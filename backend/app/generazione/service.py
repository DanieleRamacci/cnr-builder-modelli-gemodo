"""Generazione dei documenti (004) con il registro delle generazioni al posto dell'archivio (013)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from functools import partial

from fastapi import Depends
from sqlalchemy.orm import Session

from app.catalog import repository as catalog_repository
from app.common.security import PrincipalGEMODO
from app.db.session import get_db
from app.builder import repository as builder_repository
from app.generazione.renderer import (
    PlaceholderSenzaValore,
    render_documento,
    render_pdf,
    sostituisci_placeholder,
)
from app.generazione.schemas import EsitoGenerazione
from app.storage.service import StorageDocumentiService, get_storage_documenti_service, hash_dati
from app.validation.schemas import ValidazioneRequest, ValidazioneResponse
from app.validation.service import PayloadValidationService, get_payload_validation_service


@dataclass(frozen=True)
class RisultatoGenerazione:
    """Esito piu' il contenuto del file quando disponibile subito (stato COMPLETATO)."""

    esito: EsitoGenerazione
    contenuto: bytes | None
    nome_file: str | None


class GenerazioneDocumentiService:
    def __init__(self, db: Session, validazione: PayloadValidationService, storage: StorageDocumentiService):
        self.db = db
        self.validazione = validazione
        self.storage = storage

    def genera(self, request: ValidazioneRequest, principal: PrincipalGEMODO) -> RisultatoGenerazione:
        """Genera e consegna; ogni chiamata lascia una riga nel registro (013).

        La stessa chiave si ripete quante volte serve, anche con dati diversi:
        GEBAN rigenera il bando a ogni correzione. GEMODO non conserva il PDF,
        ne registra l'impronta; e lo consegna solo a registrazione avvenuta.
        """
        validazione = self.validazione.validate_payload(request, principal)  # 404/409 se versione assente/non pubblicata/fuori contesto
        version = catalog_repository.get_model_version_by_public_id(self.db, request.modello_versione_id)
        nome_file = f"{version.modello.codice}-v{version.versione}-{request.external_context_id}.pdf"
        riferimento = uuid.uuid4().hex
        registra = partial(
            self.storage.registra, sistema_richiedente=request.sistema_richiedente,
            external_context_id=request.external_context_id, modello_versione_id=version.id,
            hash_richiesta=hash_dati(request.dati), nome_file=nome_file, principal=principal,
            riferimento=riferimento,
        )
        if not validazione.valido:
            campi = sorted({errore.campo or errore.codice for errore in validazione.errori})
            riga = registra(stato="DATI_NON_VALIDI", errore_messaggio="Dati non validi: " + ", ".join(campi))
            return RisultatoGenerazione(
                self._risposta(
                    stato="DATI_NON_VALIDI",
                    messaggio="Documento non generato: i dati ricevuti non sono coerenti con il contratto del modello.",
                    request=request, validazione=validazione, riferimento=riga.riferimento,
                ),
                contenuto=None, nome_file=None,
            )

        titolo = f"{version.modello.tipo_documento.nome} - {version.modello.nome}"
        campi = catalog_repository.list_required_fields(self.db, version.id)

        # 003 T018/T019: se la versione ha sezioni, il documento e' quello
        # composto. Un modello senza sezioni - ogni modello creato prima della
        # `003` - resta l'elenco etichetta/valore, quindi nulla di gia'
        # pubblicato cambia forma da sotto.
        documentale = builder_repository.composizione_documentale(version)
        try:
            if documentale.blocchi:
                blocchi = sostituisci_placeholder(documentale.blocchi, request.dati)
                contenuto = render_documento(
                    titolo=titolo, blocchi=blocchi,
                    inizi_sezione=builder_repository.inizi_sezione(version),
                    cornice=builder_repository.cornice_del_tipo(version),
                    logo=builder_repository.logo_del_tipo(version),
                    riferimento_documentale=riferimento,
                )
            else:
                righe = [
                    (campo.etichetta, request.dati[campo.codice])
                    for campo in campi if campo.codice in request.dati
                ]
                contenuto = render_pdf(
                    titolo=titolo, righe=righe, cornice=builder_repository.cornice_del_tipo(version),
                    logo=builder_repository.logo_del_tipo(version), riferimento_documentale=riferimento,
                )
        except PlaceholderSenzaValore as mancanti:
            # Un segnaposto senza valore non e' un errore di produzione del
            # file: e' il documento che non si puo' comporre con questi dati.
            messaggio = "Documento non generato: mancano i valori per " + ", ".join(mancanti.mancanti)
            riga = registra(stato="DATI_NON_VALIDI", errore_messaggio=messaggio)
            return RisultatoGenerazione(
                self._risposta(
                    stato="DATI_NON_VALIDI", messaggio=messaggio,
                    request=request, validazione=validazione, riferimento=riga.riferimento,
                ),
                contenuto=None, nome_file=None,
            )
        except Exception:
            riga = registra(stato="FALLITO", errore_messaggio="Errore durante la produzione del documento")
            return RisultatoGenerazione(
                self._risposta(
                    stato="FALLITO", messaggio="Documento non generato: errore durante la produzione del file.",
                    request=request, validazione=validazione, riferimento=riga.riferimento,
                ),
                contenuto=None, nome_file=None,
            )

        riga = registra(stato="COMPLETATO", contenuto=contenuto)
        return RisultatoGenerazione(
            self._risposta(
                stato="COMPLETATO", messaggio="Documento di test generato correttamente.",
                request=request, validazione=validazione, riferimento=riga.riferimento,
            ),
            contenuto=contenuto, nome_file=nome_file,
        )

    @staticmethod
    def _risposta(
        *, stato: str, messaggio: str, request: ValidazioneRequest, validazione: ValidazioneResponse, riferimento: str | None,
    ) -> EsitoGenerazione:
        return EsitoGenerazione(
            stato=stato, messaggio=messaggio, modello_versione_id=request.modello_versione_id,
            external_context_id=request.external_context_id, riferimento_documentale=riferimento, validazione=validazione,
        )


def get_generazione_documenti_service(
    db: Session = Depends(get_db),
    validazione: PayloadValidationService = Depends(get_payload_validation_service),
    storage: StorageDocumentiService = Depends(get_storage_documenti_service),
) -> GenerazioneDocumentiService:
    return GenerazioneDocumentiService(db, validazione, storage)
