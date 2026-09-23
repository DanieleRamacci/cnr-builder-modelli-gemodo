"""Builder domain service: model/version creation and publication workflow.

FR-002/FR-003/FR-014/FR-015 (specs/002-builder-modelli, riallineate 2026-09-15,
DEC-001-CONTESTO-SOSTITUISCE-UFFICIO): la struttura disponibile (tipologie,
profili, campi) si legge sempre dalla porta di discovery, mai direttamente
dalle tabelle catalogo; ogni scrittura e' autorizzata per il singolo contesto
del tipo documento target, mai sulla lista di permessi del principal gia'
appiattita su tutti i contesti del token.
"""

from __future__ import annotations

import uuid
import re
import unicodedata
from datetime import datetime, timezone

from fastapi import Depends
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.builder import repository as builder_repository
from app.builder.audit import registra_evento
from app.builder.schemas import CampoVersioneRequest, CreaEdizioneDerivataRequest, CreaModelloRequest, FiltriModelli
from app.catalog import repository as catalog_repository
from app.catalog.models import ModelloCampoRichiesto, ModelloDocumento, ModelloDocumentoVersione, TipoDocumento
from app.configurazione import repository as configurazione_repository
from app.common.errors import BuilderDomainError, DomainError, ErrorCode
from app.common.security import PrincipalGEMODO, verify_scrittura_su_contesto, contesti_con_permesso, ROLE_GEMODO_MODELLI_GESTORE
from app.db.session import get_db
from app.discovery.configuration import discovery_per_tipo
from app.discovery.port import PortaDiscovery
from app.discovery.schemas import CatalogoDiscovery

TRANSIZIONI_VALIDE: dict[str, set[str]] = {
    "BOZZA": {"IN_REVISIONE"},
    "IN_REVISIONE": {"BOZZA", "APPROVATO"},
    "APPROVATO": {"PUBBLICATO"},
    "PUBBLICATO": {"ARCHIVIATO", "SOSPESO"},
    "SOSPESO": {"ARCHIVIATO"},
    "ARCHIVIATO": set(),
}


# 011 T054: il nome della dimensione del livello e' uniformato a quello della
# colonna che ha sostituito e del campo di contratto.
NOME_LIVELLO = "livello_professionale"

# Le due chiavi storiche dell'albero discovery e la dimensione che ne deriva.
# Sono un dettaglio del *formato* della risposta, non un elenco di dimensioni
# governate: ogni altra chiave con una lista diventa una dimensione senza che
# nessuno debba aggiungerla qui.
_CHIAVI_DIMENSIONE_STORICHE = {"lingue_possibili": "lingua", "livelli_possibili": NOME_LIVELLO}


def _dimensioni_dichiarate(nodo) -> dict[str, tuple[str, ...]]:
    """Dimensioni e valori ammessi che una foglia dichiara.

    Legge le due chiavi storiche piu' qualunque altra chiave che porti una lista
    non vuota, perche' `NodoDiscovery` ha `extra="allow"`. E' lo stesso criterio
    di `IntegrazioniService._dimensioni_catalogo`, che era gia' generico: qui
    serve anche il valore, non solo il nome.
    """
    dichiarate: dict[str, tuple[str, ...]] = {}
    for chiave, nome in _CHIAVI_DIMENSIONE_STORICHE.items():
        valori = getattr(nodo, chiave, None)
        if valori:
            dichiarate[nome] = tuple(valori)
    for nome, valori in (nodo.model_extra or {}).items():
        if isinstance(valori, (list, tuple)) and valori and all(isinstance(v, str) for v in valori):
            dichiarate[nome] = tuple(valori)
    return dichiarate


def _dimensioni_dichiarate_ovunque(catalogo) -> set[str]:
    """Nomi di dimensione visti su almeno una foglia dell'albero."""
    nomi: set[str] = set()
    stack = list(catalogo.nodi)
    while stack:
        nodo = stack.pop()
        stack.extend(nodo.figli or ())
        if nodo.campi is not None:
            nomi.update(_dimensioni_dichiarate(nodo))
    return nomi


def _slug(value: str) -> str:
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", ascii_value.lower()).strip("-") or "modello"


def _identita_modello(
    *,
    tipo: str,
    nodi,
    dimensioni: dict[str, str],
    modello_id: uuid.UUID,
) -> tuple[str, str]:
    """Codice e nome generati, distinti per ogni combinazione di dimensioni (011 FR-003).

    I valori entrano **in ordine alfabetico di nome dimensione**, non nell'ordine
    in cui l'integrazione li elenca: quell'ordine non e' garantito stabile dal
    contratto di discovery, quindi due creazioni identiche potrebbero altrimenti
    produrre codici diversi.

    I nomi umani di lingua e livello - "Italiano", "Livello VI", "Tutti i
    livelli" - sono spariti: esistevano solo per quelle due dimensioni, e per
    `area_geografica` non ci sarebbe stato nulla di simile. Tenerli avrebbe
    significato che due dimensioni hanno nomi belli e tutte le altre no, che e'
    il privilegio che 011 toglie.
    """
    valori = [dimensioni[nome] for nome in sorted(dimensioni)]
    suffix = modello_id.hex
    prefix = _slug("-".join([tipo, *(n.codice for n in nodi), *valori]))
    codice = f"{prefix[:128 - len(suffix) - 1]}-{suffix}"
    # Una dimensione non valorizzata semplicemente non compare nel nome:
    # l'assenza e' l'informazione (FR-006), e non serve renderla con "tutti".
    etichetta_dimensioni = " - ".join(valori)
    parti_suffix = [p for p in (etichetta_dimensioni, f"{datetime.now(timezone.utc):%Y-%m-%d}") if p]
    name_suffix = " - " + " - ".join(parti_suffix)
    descriptions = " - ".join(n.descrizione for n in nodi)
    return codice, f"{descriptions[:255 - len(name_suffix)]}{name_suffix}"


class BuilderService:
    def __init__(self, db: Session, discovery: PortaDiscovery | None = None) -> None:
        self.db = db
        self.discovery = discovery

    def contesti(self, principal: PrincipalGEMODO) -> list[str]:
        return sorted(contesti_con_permesso(principal, ROLE_GEMODO_MODELLI_GESTORE,
                                           dict(principal.ruoli_contesto)))

    def lista(
        self,
        principal: PrincipalGEMODO,
        codice_contesto: str,
        *,
        offset: int,
        limit: int,
        filtri: FiltriModelli | None = None,
    ):
        verify_scrittura_su_contesto(principal, codice_contesto)
        return builder_repository.lista_modelli(
            self.db, codice_contesto, offset=offset, limit=limit,
            **(filtri.model_dump(exclude_none=True) if filtri is not None else {}),
        )

    def voci_filtro(self, principal: PrincipalGEMODO, codice_contesto: str) -> dict[str, list[str]]:
        verify_scrittura_su_contesto(principal, codice_contesto)
        return builder_repository.voci_filtro(self.db, codice_contesto)

    # Comportamento storico, usato solo come ripiego quando un tipo documento non
    # ha ancora una policy registrata: e' lo stesso che la migration 0018 scrive
    # per i tipi esistenti, quindi nulla cambia di nascosto. Una dimensione che
    # non compare qui resta richiesta, e la lettura delle policy la segnala.
    POLICY_DI_RIPIEGO = {"lingua": False, NOME_LIVELLO: True}

    @classmethod
    def _verifica_dimensione(cls, nome, valore, ammessi, policy):
        """Un valore assente e' ammesso solo se la policy consente il generico."""
        if valore is None:
            if policy.get(nome, cls.POLICY_DI_RIPIEGO.get(nome, False)):
                return
            raise BuilderDomainError(
                "DIMENSIONE_RICHIEDE_VALORE",
                f"La dimensione '{nome}' richiede un valore esplicito per questo tipo documento",
                status_code=400,
            )
        if valore not in (ammessi or ()):
            raise BuilderDomainError(
                ErrorCode.CONTESTO_NON_VALIDO,
                f"Valore '{valore}' non disponibile per la dimensione '{nome}' nella categorizzazione scelta",
                status_code=400,
            )

    @classmethod
    def _verifica_dimensioni(cls, dimensioni: dict[str, str], dichiarate: dict[str, tuple[str, ...]], policy) -> None:
        """Enforcement su **tutte** le dimensioni dichiarate, non su due nomi (011 FR-002).

        Prima questo metodo veniva invocato esattamente due volte, con "lingua" e
        "livello" scritti a mano: una policy registrata su qualunque altra
        dimensione veniva salvata e poi ignorata, dando all'admin la falsa
        impressione di aver configurato qualcosa. Ora il ciclo copre tutte le
        dimensioni che la foglia dichiara.

        Il ciclo e' sulle dimensioni **dichiarate dalla foglia**, non sull'unione
        con le policy registrate. La policy vive sul tipo documento, ma l'albero
        puo' dichiarare dimensioni diverse su foglie diverse: pretendere un
        valore per una dimensione che questa foglia non ha renderebbe la
        creazione impossibile, perche' fornirlo violerebbe FR-006 e non fornirlo
        violerebbe la policy. Una policy non applicabile a questa foglia
        semplicemente non si applica.
        """
        for nome in sorted(dichiarate):
            cls._verifica_dimensione(nome, dimensioni.get(nome), dichiarate.get(nome), policy)
        # FR-006: nessun valore implicito, ma nemmeno valori inventati. Una
        # chiave che la foglia non dichiara non puo' essere registrata, altrimenti
        # il modello direbbe qualcosa che l'integrazione non ha mai dichiarato.
        for nome in sorted(set(dimensioni) - set(dichiarate)):
            raise BuilderDomainError(
                "DIMENSIONE_NON_DICHIARATA",
                f"La dimensione '{nome}' non e' dichiarata per la categorizzazione scelta",
                status_code=400,
            )

    def policy_dimensioni(self, principal: PrincipalGEMODO, codice_tipo_documento: str):
        tipo = self._resolve_tipo_documento(codice_tipo_documento)
        verify_scrittura_su_contesto(principal, tipo.codice_contesto)
        registrate = builder_repository.policy_dimensioni(self.db, tipo.id)
        nomi = {p.nome_dimensione for p in registrate}
        non_configurate = sorted(self._dimensioni_live(codice_tipo_documento, tipo) - nomi)
        conteggi = {
            nome: builder_repository.conta_modelli_pubblicati_con_dimensione(
                self.db, tipo.id, nome
            )
            for nome in nomi | set(non_configurate)
        }
        return tipo, registrate, non_configurate, conteggi

    def _dimensioni_live(self, codice_tipo_documento: str, tipo) -> set[str]:
        """Le dimensioni che l'albero live dichiara, qualunque siano (011 FR-005).

        Sostituisce un `return {"lingua", "livello"}` scritto a mano, che era il
        motivo per cui una dimensione nuova non veniva nemmeno segnalata come
        priva di policy. L'albero e' gia' letto in modo generico: `NodoDiscovery`
        ha `extra="allow"`, quindi qualunque chiave con una lista di valori
        arriva fin qui senza che nessuno l'abbia prevista.
        """
        catalogo = self._catalogo(codice_tipo_documento, aggiornato=False, tipo=tipo)
        return set(_dimensioni_dichiarate_ovunque(catalogo))

    def imposta_policy_dimensione(self, principal: PrincipalGEMODO, codice_tipo_documento: str, request):
        """Registra la policy di una dimensione. Nessuna dimensione e' esclusa.

        Prima esisteva `DIMENSIONI_SENZA_GENERICO = {"lingua"}`, che rifiutava con
        `GENERICO_NON_SUPPORTATO` il tentativo di dichiarare la lingua generica:
        serviva perche' la colonna era NOT NULL e il contratto la esponeva
        obbligatoria, quindi accettare e poi salvare 'IT' sarebbe stata una bugia
        silenziosa. Con 011 la colonna non esiste piu' e il contratto ammette il
        null, quindi il divieto non ha piu' una ragione tecnica - ed era, alla
        lettera, un nome di dimensione scritto nel codice.

        La protezione non sparisce, cambia natura: la schermata mostra la
        conseguenza calcolata dai dati prima di salvare. Il rischio residuo e'
        dichiarato in DEC-011-POLICY-LINGUA-ALL-ADMIN - portare la lingua del
        bando a generico riaprirebbe l'ambiguita' che DEC-001-LINGUA-IT-EN aveva
        chiuso - ma e' ora una scelta deliberata dell'admin, non un'impossibilita'
        strutturale.
        """
        tipo = self._resolve_tipo_documento(codice_tipo_documento)
        verify_scrittura_su_contesto(principal, tipo.codice_contesto)
        policy, creata = builder_repository.salva_policy_dimensione(
            self.db, tipo_documento_id=tipo.id, nome_dimensione=request.nome_dimensione,
            consente_valore_generico=request.consente_valore_generico,
            valore_default=request.valore_default, soggetto=principal.subject,
        )
        self.db.commit()
        return policy, creata

    def dettaglio(self, principal: PrincipalGEMODO, modello_id: uuid.UUID) -> ModelloDocumento:
        modello = builder_repository.modello_con_campi(self.db, modello_id)
        if modello is None:
            raise DomainError("RISORSA_NON_TROVATA", "Risorsa non disponibile", status_code=404)
        verify_scrittura_su_contesto(principal, modello.tipo_documento.codice_contesto)
        return modello

    def dimensioni_non_disponibili(self, modello: ModelloDocumento) -> list[str]:
        """Segnala dimensioni storiche non piu' dichiarate dalla foglia live."""
        catalogo = self._catalogo(
            modello.tipo_documento.codice,
            aggiornato=True,
            tipo=modello.tipo_documento,
        )
        foglia = catalogo.indice_percorsi().get(tuple(modello.percorso_categorizzazione))
        dichiarate = set(_dimensioni_dichiarate(foglia)) if foglia is not None else set()
        return sorted(set(modello.dimensioni) - dichiarate)

    def _catalogo(self, codice: str, *, aggiornato: bool = False, tipo: TipoDocumento | None = None) -> CatalogoDiscovery:
        tipo = tipo if tipo is not None else self._resolve_tipo_documento(codice)
        porta = self.discovery if self.discovery is not None else discovery_per_tipo(self.db, tipo)
        return porta.catalogo_discovery(codice, forza_aggiornamento=aggiornato)

    def struttura_disponibile(self, principal: PrincipalGEMODO, codice_tipo_documento: str) -> CatalogoDiscovery:
        tipo = self._resolve_tipo_documento(codice_tipo_documento)
        verify_scrittura_su_contesto(principal, tipo.codice_contesto)
        return self._catalogo(codice_tipo_documento)

    def _tipo_per_integrazione(self, source, codice: str) -> TipoDocumento:
        """FR-024: al piu' un tipo non inattivo per (codice_contesto, codice).

        Riusa quello dell'integrazione, associa una configurazione amministrativa
        non ancora assegnata, rifiuta quella di un'altra integrazione.
        """
        esistenti = list(self.db.scalars(select(TipoDocumento).where(
            TipoDocumento.codice_contesto == source.codice_contesto,
            TipoDocumento.codice == codice,
            TipoDocumento.stato != "INATTIVA",
        ).with_for_update()))
        proprio = next((t for t in esistenti if t.integrazione_id == source.id), None)
        if proprio is not None:
            return proprio
        libero = next((t for t in esistenti if t.integrazione_id is None), None)
        if libero is not None:
            libero.integrazione_id = source.id
            self.db.flush()
            return libero
        if esistenti:
            raise DomainError(
                "TIPO_DOCUMENTO_ALTRA_INTEGRAZIONE",
                "Tipo documento gia' associato a un'altra integrazione dello stesso contesto",
                status_code=409,
            )
        # Persist only the document type identity, never the external tree.
        self.db.execute(insert(TipoDocumento).values(
            id=uuid.uuid4(), codice=codice, nome=codice, codice_contesto=source.codice_contesto,
            integrazione_id=source.id, stato="ATTIVA", spec_owner="specs/002-builder-modelli",
        ).on_conflict_do_nothing(constraint="uq_tipo_documento_integrazione_codice"))
        tipo = self.db.scalar(select(TipoDocumento).where(
            TipoDocumento.integrazione_id == source.id, TipoDocumento.codice == codice,
        ))
        # Un tipo nuovo nasce con le policy esplicite, come i tipi gia' esistenti
        # dopo la migration 0018: l'admin le rivede, non deve inventarle da zero.
        for nome, generico in self.POLICY_DI_RIPIEGO.items():
            builder_repository.salva_policy_dimensione(
                self.db, tipo_documento_id=tipo.id, nome_dimensione=nome,
                consente_valore_generico=generico,
                valore_default="IT" if nome == "lingua" else None,
                soggetto=None,
            )
        return tipo

    def crea_modello(self, principal: PrincipalGEMODO, request: CreaModelloRequest) -> ModelloDocumento:
        if request.integrazione_id is None:
            tipo = self._resolve_tipo_documento(request.codice_tipo_documento)
        else:
            source = configurazione_repository.integrazione(self.db, request.integrazione_id)
            if source is None:
                raise DomainError("RISORSA_NON_TROVATA", "Risorsa non disponibile", status_code=404)
            verify_scrittura_su_contesto(principal, source.codice_contesto)
            tipo = self._tipo_per_integrazione(source, request.codice_tipo_documento)
        verify_scrittura_su_contesto(principal, tipo.codice_contesto)

        indice = self._catalogo(request.codice_tipo_documento, aggiornato=True, tipo=tipo).indice_percorsi()

        def riferimenti(percorso: tuple[str, ...]) -> tuple[str, str | None]:
            nodi = [indice[percorso[:i]] for i in range(1, len(percorso) + 1)]
            categoria = next((n.codice for n in reversed(nodi) if n.tipo_livello == "profilo"), percorso[-1])
            tipologia = next((n.codice for n in nodi if n.tipo_livello == "tipologia"), None)
            return categoria, tipologia

        if request.percorso_categorizzazione is not None:
            percorso = tuple(request.percorso_categorizzazione)
            foglia = indice.get(percorso)
            if foglia is None or foglia.campi is None:
                raise BuilderDomainError(ErrorCode.CONTESTO_NON_VALIDO, "Percorso non disponibile o non foglia", status_code=404)
            categoria, tipologia = riferimenti(percorso)
            if ((request.codice_categoria is not None and request.codice_categoria != categoria)
                or (request.codice_tipologia is not None and request.codice_tipologia != tipologia)):
                raise BuilderDomainError(ErrorCode.CONTESTO_NON_VALIDO, "Codici incoerenti con il percorso scelto", status_code=400)
        else:
            candidati = [p for p, n in indice.items() if n.campi is not None
                         and riferimenti(p)[0] == request.codice_categoria
                         and (request.codice_tipologia is None or riferimenti(p)[1] == request.codice_tipologia)]
            if len(candidati) != 1:
                raise BuilderDomainError(
                    ErrorCode.CONTESTO_NON_VALIDO,
                    "Selezione ambigua: indicare il percorso completo" if candidati else "Categoria/tipologia non disponibile",
                    status_code=400 if candidati else 404,
                )
            percorso = candidati[0]
            categoria, tipologia = riferimenti(percorso)

        foglia = indice[percorso]
        # DEC-002-POLICY: cosa rende due modelli distinti non e' piu' scritto qui,
        # ma dichiarato per nome di dimensione sul tipo documento.
        policy = {p.nome_dimensione: p.consente_valore_generico
                  for p in builder_repository.policy_dimensioni(self.db, tipo.id)}
        dimensioni = request.dimensioni_effettive()
        self._verifica_dimensioni(dimensioni, _dimensioni_dichiarate(foglia), policy)
        nodi = [indice[percorso[:i]] for i in range(1, len(percorso) + 1)]
        modello_id = uuid.uuid4()
        codice, nome = _identita_modello(
            tipo=request.codice_tipo_documento,
            nodi=nodi,
            dimensioni=dimensioni,
            modello_id=modello_id,
        )

        modello = builder_repository.crea_modello(
            self.db,
            modello_id=modello_id,
            codice=codice,
            nome=nome,
            tipo_documento_id=tipo.id,
            codice_categoria=categoria,
            codice_tipologia=tipologia,
            percorso_categorizzazione=list(percorso),
            variante="STANDARD",
            dimensioni=dimensioni,
        )
        registra_evento(
            self.db,
            tipo_evento="MODELLO_CREATO",
            principal=principal,
            modello_documento_id=modello.id,
            modello_versione_id=None,
            # Le dimensioni entrano nell'audit: erano ricavabili dalle due
            # colonne, che non esistono piu'. Senza, l'evento perderebbe la
            # categorizzazione del modello creato (Constitution V).
            payload_minimo={
                "codice": modello.codice,
                "codice_tipo_documento": request.codice_tipo_documento,
                "dimensioni": dimensioni,
            },
        )
        self.db.commit()
        return modello

    def crea_edizione_derivata(
        self,
        principal: PrincipalGEMODO,
        modello_id: uuid.UUID,
        request: CreaEdizioneDerivataRequest,
    ) -> ModelloDocumento:
        origine = builder_repository.get_modello(self.db, modello_id)
        if origine is None:
            raise BuilderDomainError(ErrorCode.MODELLO_NON_TROVATO, "Modello non trovato", status_code=404)
        verify_scrittura_su_contesto(principal, origine.tipo_documento.codice_contesto)
        self.db.execute(select(TipoDocumento.id).where(
            TipoDocumento.id == origine.tipo_documento_id,
        ).with_for_update())
        self.db.refresh(origine)
        nome_dimensione, valore = request.dimensione_derivata()
        if origine.dimensioni.get(nome_dimensione) is None:
            raise BuilderDomainError(
                ErrorCode.CONTESTO_NON_VALIDO,
                f"Il modello di origine non valorizza la dimensione '{nome_dimensione}': "
                "non c'e' un valore da cui derivare",
                status_code=400,
            )
        if valore == origine.dimensioni.get(nome_dimensione):
            raise BuilderDomainError(
                ErrorCode.CONTESTO_NON_VALIDO,
                f"Il valore derivato di '{nome_dimensione}' deve essere diverso da quello del modello origine",
                status_code=400,
            )
        if builder_repository.get_edizione_derivata(self.db, origine.id, nome_dimensione, valore) is not None:
            raise BuilderDomainError(
                "EDIZIONE_DERIVATA_DUPLICATA",
                f"Esiste gia' un'edizione derivata con '{nome_dimensione}' = '{valore}'",
                status_code=409,
            )

        indice = self._catalogo(
            origine.tipo_documento.codice, aggiornato=True, tipo=origine.tipo_documento,
        ).indice_percorsi()
        percorso = tuple(origine.percorso_categorizzazione)
        foglia = indice.get(percorso)
        if foglia is None or foglia.campi is None:
            raise BuilderDomainError(
                ErrorCode.CONTESTO_NON_VALIDO,
                "Il ramo del modello non e' piu' disponibile",
                status_code=404,
            )
        dichiarate = _dimensioni_dichiarate(foglia)
        # 011 FR-014: si deriva solo su una dimensione **obbligatoria**, perche'
        # e' li' che il modello di origine ha certamente il valore di partenza.
        # Dove la dimensione ammette il generico un modello puo' non valorizzarla,
        # e "derivane un'altra versione" non significherebbe nulla.
        policy = {p.nome_dimensione: p.consente_valore_generico
                  for p in builder_repository.policy_dimensioni(self.db, origine.tipo_documento_id)}
        if policy.get(nome_dimensione, self.POLICY_DI_RIPIEGO.get(nome_dimensione, False)):
            raise BuilderDomainError(
                ErrorCode.CONTESTO_NON_VALIDO,
                f"La dimensione '{nome_dimensione}' ammette un valore generico per questo tipo documento: "
                "non e' una dimensione su cui derivare edizioni",
                status_code=400,
            )
        if valore not in (dichiarate.get(nome_dimensione) or ()):
            raise BuilderDomainError(
                ErrorCode.CONTESTO_NON_VALIDO,
                f"Valore '{valore}' non disponibile per la dimensione '{nome_dimensione}' "
                "nella categorizzazione scelta",
                status_code=400,
            )
        sorgente = builder_repository.get_ultima_versione_con_campi(self.db, origine.id)
        if sorgente is None:
            raise BuilderDomainError(
                ErrorCode.MODELLO_VERSIONE_NON_TROVATO,
                "Il modello origine non ha versioni da clonare",
                status_code=409,
            )

        nodi = [indice[percorso[:i]] for i in range(1, len(percorso) + 1)]
        derivato_id = uuid.uuid4()
        # L'edizione derivata conserva tutte le dimensioni dell'origine e cambia
        # solo quella su cui si deriva.
        dimensioni_derivate = {**origine.dimensioni, nome_dimensione: valore}
        codice, nome = _identita_modello(
            tipo=origine.tipo_documento.codice,
            nodi=nodi,
            dimensioni=dimensioni_derivate,
            modello_id=derivato_id,
        )
        derivato = builder_repository.crea_modello(
            self.db,
            modello_id=derivato_id,
            codice=codice,
            nome=nome,
            tipo_documento_id=origine.tipo_documento_id,
            codice_categoria=origine.codice_categoria,
            codice_tipologia=origine.codice_tipologia,
            percorso_categorizzazione=list(origine.percorso_categorizzazione),
            variante=origine.variante,
            dimensioni=dimensioni_derivate,
            derivato_da_modello_id=origine.id,
        )
        versione = builder_repository.crea_versione(
            self.db,
            modello_documento_id=derivato.id,
            campi=builder_repository.clona_campi(sorgente),
            formato_documentale=sorgente.formato_documentale,
            struttura_documentale=sorgente.struttura_documentale,
        )
        registra_evento(
            self.db,
            tipo_evento="MODELLO_DERIVATO_CREATO",
            principal=principal,
            modello_documento_id=derivato.id,
            modello_versione_id=versione.id,
            payload_minimo={
                "modello_origine_id": str(origine.id),
                "dimensione": nome_dimensione,
                "valore": valore,
            },
        )
        try:
            self.db.commit()
        except IntegrityError as exc:
            # Due richieste simultanee per la stessa terna (origine, dimensione, valore):
            # l'indice parziale di 0019 le separa, il controllo applicativo sopra
            # non basta. Conflitto funzionale, mai un 500 (002 FR-018).
            self.db.rollback()
            if getattr(exc.orig, "sqlstate", None) == "23505":
                raise BuilderDomainError(
                    "EDIZIONE_DERIVATA_DUPLICATA",
                    f"Esiste gia' un'edizione derivata con '{nome_dimensione}' = '{valore}'",
                    status_code=409,
                ) from exc
            raise
        self.db.refresh(derivato)
        return derivato

    def crea_versione(
        self, principal: PrincipalGEMODO, modello_id: uuid.UUID, campi_richiesti: list[CampoVersioneRequest]
    ) -> ModelloDocumentoVersione:
        modello = builder_repository.get_modello(self.db, modello_id)
        if modello is None:
            raise BuilderDomainError(ErrorCode.MODELLO_NON_TROVATO, "Modello non trovato", status_code=404)
        verify_scrittura_su_contesto(principal, modello.tipo_documento.codice_contesto)

        self.db.execute(select(TipoDocumento.id).where(TipoDocumento.id == modello.tipo_documento_id).with_for_update())
        self.db.refresh(modello)
        if modello.stato == "ELIMINATO":
            raise BuilderDomainError(ErrorCode.MODELLO_NON_TROVATO, "Modello non trovato", status_code=404)
        foglia = self._catalogo(modello.tipo_documento.codice, aggiornato=True, tipo=modello.tipo_documento).indice_percorsi().get(
            tuple(modello.percorso_categorizzazione)
        )
        if foglia is None or foglia.campi is None:
            raise BuilderDomainError(ErrorCode.CONTESTO_NON_VALIDO, "Il ramo del modello non e' piu' disponibile", status_code=404)
        chiavi = [(campo.codice, campo.lingua) for campo in campi_richiesti]
        if len(set(chiavi)) != len(chiavi):
            raise BuilderDomainError(ErrorCode.CAMPO_NON_AMMESSO, "Campi duplicati nella versione", status_code=400)
        disponibili = {
            (campo.codice, campo.lingua): campo
            for campo in foglia.campi
        }
        campi_modello: list[ModelloCampoRichiesto] = []
        for richiesto in campi_richiesti:
            chiave = (richiesto.codice, richiesto.lingua)
            sorgente = disponibili.get(chiave)
            if sorgente is None:
                raise BuilderDomainError(
                    ErrorCode.CAMPO_NON_AMMESSO,
                    f"Campo '{richiesto.codice}' ({richiesto.lingua}) non presente nel ramo discovery selezionato",
                    status_code=404,
                )
            campi_modello.append(
                ModelloCampoRichiesto(
                    id=uuid.uuid4(),
                    codice=sorgente.codice,
                    etichetta=sorgente.etichetta,
                    tipo_dato=sorgente.tipo,
                    descrizione=sorgente.descrizione,
                    obbligatorio=sorgente.obbligatorio,
                    lingua=sorgente.lingua,
                    ordine=sorgente.ordine,
                    validazione=sorgente.validazione,
                )
            )

        versione = builder_repository.crea_versione(
            self.db, modello_documento_id=modello.id, campi=campi_modello
        )
        registra_evento(
            self.db,
            tipo_evento="VERSIONE_CREATA",
            principal=principal,
            modello_documento_id=modello.id,
            modello_versione_id=versione.id,
            payload_minimo={"numero_versione": versione.versione, "campi": [c.codice for c in campi_modello]},
        )
        self.db.commit()
        return versione

    def transizione(self, principal: PrincipalGEMODO, versione_id: uuid.UUID, nuovo_stato: str, *, modello_id: uuid.UUID | None = None) -> ModelloDocumentoVersione:
        versione = builder_repository.get_versione(self.db, versione_id)
        if versione is None or (modello_id is not None and versione.modello_documento_id != modello_id):
            raise BuilderDomainError(ErrorCode.MODELLO_VERSIONE_NON_TROVATO, "Versione non trovata", status_code=404)
        modello = builder_repository.get_modello(self.db, versione.modello_documento_id)
        if modello is None:
            raise BuilderDomainError(ErrorCode.MODELLO_NON_TROVATO, "Modello non trovato", status_code=404)
        verify_scrittura_su_contesto(principal, modello.tipo_documento.codice_contesto)

        # Serialize state changes, including replacement publication, per document type.
        self.db.execute(select(TipoDocumento.id).where(
            TipoDocumento.id == modello.tipo_documento_id,
        ).with_for_update())
        self.db.refresh(versione)
        self.db.refresh(modello)
        if modello.stato == "ELIMINATO":
            raise BuilderDomainError(ErrorCode.MODELLO_NON_TROVATO, "Modello non trovato", status_code=404)

        ammessi = TRANSIZIONI_VALIDE.get(versione.stato, set())
        if nuovo_stato not in ammessi:
            raise BuilderDomainError(
                ErrorCode.TRANSIZIONE_STATO_NON_VALIDA,
                f"Transizione da {versione.stato} a {nuovo_stato} non valida",
                status_code=409,
            )

        if nuovo_stato == "PUBBLICATO":
            precedente = builder_repository.get_versione_pubblicata_corrente(
                self.db,
                tipo_documento_id=modello.tipo_documento_id,
                percorso_categorizzazione=modello.percorso_categorizzazione,
                variante=modello.variante,
                dimensioni=modello.dimensioni,
                escludi_versione_id=versione.id,
            )
            if precedente is not None:
                builder_repository.transizione_stato(self.db, precedente, nuovo_stato="ARCHIVIATO")
                registra_evento(
                    self.db,
                    tipo_evento="VERSIONE_ARCHIVIATA",
                    principal=principal,
                    modello_documento_id=modello.id,
                    modello_versione_id=precedente.id,
                    payload_minimo={"motivo": "sostituita da nuova versione corrente"},
                )

        builder_repository.transizione_stato(self.db, versione, nuovo_stato=nuovo_stato)
        registra_evento(
            self.db,
            tipo_evento=f"VERSIONE_{nuovo_stato}",
            principal=principal,
            modello_documento_id=modello.id,
            modello_versione_id=versione.id,
            payload_minimo={"stato": nuovo_stato},
        )
        self.db.commit()
        return versione

    def elimina(self, principal: PrincipalGEMODO, modello_id: uuid.UUID) -> None:
        modello = builder_repository.get_modello(self.db, modello_id)
        if modello is None:
            raise BuilderDomainError(ErrorCode.MODELLO_NON_TROVATO, "Modello non trovato", status_code=404)
        verify_scrittura_su_contesto(principal, modello.tipo_documento.codice_contesto)
        self.db.execute(select(TipoDocumento.id).where(TipoDocumento.id == modello.tipo_documento_id).with_for_update())
        self.db.refresh(modello)
        if modello.stato == "ELIMINATO":
            raise BuilderDomainError(ErrorCode.MODELLO_NON_TROVATO, "Modello non trovato", status_code=404)
        modello.stato = "ELIMINATO"
        for versione in modello.versioni:
            self.db.refresh(versione)
            if versione.stato == "PUBBLICATO":
                builder_repository.transizione_stato(self.db, versione, nuovo_stato="ARCHIVIATO")
        registra_evento(self.db, tipo_evento="MODELLO_ELIMINATO", principal=principal,
                       modello_documento_id=modello.id, modello_versione_id=None,
                       payload_minimo={"codice": modello.codice})
        self.db.commit()

    def _resolve_tipo_documento(self, codice_tipo_documento: str):
        tipo = catalog_repository.get_tipo_documento_by_codice(self.db, codice_tipo_documento)
        if tipo is None:
            raise BuilderDomainError(ErrorCode.CONTESTO_NON_VALIDO, "Tipo documento non trovato", status_code=404)
        return tipo


def get_builder_service(db: Session = Depends(get_db)) -> BuilderService:
    return BuilderService(db)
