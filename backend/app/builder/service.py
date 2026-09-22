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
from app.builder.schemas import CampoVersioneRequest, CreaEdizioneDerivataRequest, CreaModelloRequest
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


def _slug(value: str) -> str:
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", ascii_value.lower()).strip("-") or "modello"


def _identita_modello(
    *,
    tipo: str,
    nodi,
    lingua: str | None,
    livello: str | None,
    modello_id: uuid.UUID,
) -> tuple[str, str]:
    # Una dimensione assente compare nel nome come "tutte/tutti": e' ammessa solo
    # quando la policy dichiara che la dimensione consente un valore generico.
    scope = livello or "tutti"
    lingua_slug = lingua or "tutte"
    suffix = modello_id.hex
    prefix = _slug("-".join([tipo, *(n.codice for n in nodi), scope, lingua_slug]))
    codice = f"{prefix[:128 - len(suffix) - 1]}-{suffix}"
    language_name = (
        "Tutte le lingue" if lingua is None else ("Italiano" if lingua == "IT" else "Inglese")
    )
    scope_name = f"Livello {livello}" if livello else "Tutti i livelli"
    name_suffix = f" - {scope_name} - {language_name} - {datetime.now(timezone.utc):%Y-%m-%d}"
    descriptions = " - ".join(n.descrizione for n in nodi)
    return codice, f"{descriptions[:255 - len(name_suffix)]}{name_suffix}"


class BuilderService:
    def __init__(self, db: Session, discovery: PortaDiscovery | None = None) -> None:
        self.db = db
        self.discovery = discovery

    def contesti(self, principal: PrincipalGEMODO) -> list[str]:
        return sorted(contesti_con_permesso(principal, ROLE_GEMODO_MODELLI_GESTORE,
                                           dict(principal.ruoli_contesto)))

    def lista(self, principal: PrincipalGEMODO, codice_contesto: str, *, offset: int, limit: int):
        verify_scrittura_su_contesto(principal, codice_contesto)
        return builder_repository.lista_modelli(self.db, codice_contesto, offset=offset, limit=limit)

    # Comportamento storico, usato solo come ripiego quando un tipo documento non
    # ha ancora una policy registrata: e' lo stesso che la migration 0018 scrive
    # per i tipi esistenti, quindi nulla cambia di nascosto. Una dimensione che
    # non compare qui resta richiesta, e la lettura delle policy la segnala.
    POLICY_DI_RIPIEGO = {"lingua": False, "livello": True}

    @classmethod
    def _verifica_dimensione(cls, nome, valore, ammessi, policy, messaggio_valore_non_ammesso):
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
            raise BuilderDomainError(ErrorCode.CONTESTO_NON_VALIDO, messaggio_valore_non_ammesso, status_code=400)

    def policy_dimensioni(self, principal: PrincipalGEMODO, codice_tipo_documento: str):
        tipo = self._resolve_tipo_documento(codice_tipo_documento)
        verify_scrittura_su_contesto(principal, tipo.codice_contesto)
        registrate = builder_repository.policy_dimensioni(self.db, tipo.id)
        nomi = {p.nome_dimensione for p in registrate}
        return tipo, registrate, sorted(self._dimensioni_note(tipo) - nomi)

    def _dimensioni_note(self, tipo) -> set[str]:
        """Le dimensioni che il sistema sa gia' leggere dall'albero discovery.

        Quando ne verranno aggiunte altre lato integrazione andranno raccolte da
        qui, cosi' la schermata 4a le segnala invece di ignorarle.
        """
        return {"lingua", "livello"}

    # La persistenza di un valore generico esiste solo dove la colonna lo ammette.
    # `modello_documento.lingua` e' NOT NULL con vincolo IT/EN (DEC-001-LINGUA-IT-EN)
    # ed e' esposta non nullabile anche nel catalogo verso GEBAN: dichiarare qui
    # `lingua` generica e poi salvare 'IT' sarebbe una bugia silenziosa, quindi la
    # policy viene rifiutata finche' schema e contratto di `001` non cambiano.
    DIMENSIONI_SENZA_GENERICO = {"lingua"}

    def imposta_policy_dimensione(self, principal: PrincipalGEMODO, codice_tipo_documento: str, request):
        tipo = self._resolve_tipo_documento(codice_tipo_documento)
        verify_scrittura_su_contesto(principal, tipo.codice_contesto)
        if request.consente_valore_generico and request.nome_dimensione in self.DIMENSIONI_SENZA_GENERICO:
            raise BuilderDomainError(
                "GENERICO_NON_SUPPORTATO",
                f"La dimensione '{request.nome_dimensione}' non puo' ammettere un valore generico: "
                "la persistenza e il contratto del catalogo la richiedono valorizzata",
                status_code=409,
            )
        policy, creata = builder_repository.salva_policy_dimensione(
            self.db, tipo_documento_id=tipo.id, nome_dimensione=request.nome_dimensione,
            consente_valore_generico=request.consente_valore_generico, soggetto=principal.subject,
        )
        self.db.commit()
        return policy, creata

    def dettaglio(self, principal: PrincipalGEMODO, modello_id: uuid.UUID) -> ModelloDocumento:
        modello = builder_repository.modello_con_campi(self.db, modello_id)
        if modello is None:
            raise DomainError("RISORSA_NON_TROVATA", "Risorsa non disponibile", status_code=404)
        verify_scrittura_su_contesto(principal, modello.tipo_documento.codice_contesto)
        return modello

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
                consente_valore_generico=generico, soggetto=None,
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
        self._verifica_dimensione(
            "lingua", request.lingua, foglia.lingue_possibili, policy,
            "Lingua non disponibile per la categorizzazione scelta",
        )
        self._verifica_dimensione(
            "livello", request.livello_professionale, foglia.livelli_possibili, policy,
            "Livello professionale non disponibile per la categorizzazione scelta",
        )
        nodi = [indice[percorso[:i]] for i in range(1, len(percorso) + 1)]
        modello_id = uuid.uuid4()
        codice, nome = _identita_modello(
            tipo=request.codice_tipo_documento,
            nodi=nodi,
            lingua=request.lingua,
            livello=request.livello_professionale,
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
            lingua=request.lingua,
            livello_professionale=request.livello_professionale,
        )
        registra_evento(
            self.db,
            tipo_evento="MODELLO_CREATO",
            principal=principal,
            modello_documento_id=modello.id,
            modello_versione_id=None,
            payload_minimo={"codice": modello.codice, "codice_tipo_documento": request.codice_tipo_documento},
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
        if request.lingua == origine.lingua:
            raise BuilderDomainError(
                ErrorCode.CONTESTO_NON_VALIDO,
                "La lingua derivata deve essere diversa da quella del modello origine",
                status_code=400,
            )
        if builder_repository.get_edizione_derivata(self.db, origine.id, request.lingua) is not None:
            raise BuilderDomainError(
                "EDIZIONE_DERIVATA_DUPLICATA",
                "Esiste gia' un'edizione derivata nella lingua richiesta",
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
        if request.lingua not in (foglia.lingue_possibili or ()):
            raise BuilderDomainError(
                ErrorCode.CONTESTO_NON_VALIDO,
                "Lingua non disponibile per la categorizzazione scelta",
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
        codice, nome = _identita_modello(
            tipo=origine.tipo_documento.codice,
            nodi=nodi,
            lingua=request.lingua,
            livello=origine.livello_professionale,
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
            lingua=request.lingua,
            livello_professionale=origine.livello_professionale,
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
            payload_minimo={"modello_origine_id": str(origine.id), "lingua": request.lingua},
        )
        try:
            self.db.commit()
        except IntegrityError as exc:
            # Due richieste simultanee per la stessa coppia (origine, lingua):
            # l'indice parziale di 0019 le separa, il controllo applicativo sopra
            # non basta. Conflitto funzionale, mai un 500 (002 FR-018).
            self.db.rollback()
            if getattr(exc.orig, "sqlstate", None) == "23505":
                raise BuilderDomainError(
                    "EDIZIONE_DERIVATA_DUPLICATA",
                    "Esiste gia' un'edizione derivata nella lingua richiesta",
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
                lingua=modello.lingua,
                livello_professionale=modello.livello_professionale,
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
