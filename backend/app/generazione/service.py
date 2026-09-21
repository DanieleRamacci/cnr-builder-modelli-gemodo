"""Real document generation, superseding the retired simulated placeholder (004, MVP FR-019/020 slice)."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends
from sqlalchemy.orm import Session

from app.catalog import repository as catalog_repository
from app.common.security import PrincipalGEMODO
from app.db.session import get_db
from app.generazione.renderer import render_pdf
from app.generazione.schemas import EsitoGenerazione
from app.storage import archivio
from app.storage.models import DocumentoGenerato
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
        validazione = self.validazione.validate_payload(request, principal)  # 404/409 se versione assente/non pubblicata/fuori contesto
        version = catalog_repository.get_model_version_by_public_id(self.db, request.modello_versione_id)
        hash_richiesta = hash_dati(request.dati)
        esistente = self.storage.esistente_per_chiave(
            sistema_richiedente=request.sistema_richiedente, external_context_id=request.external_context_id,
            modello_versione_id=version.id, hash_richiesta=hash_richiesta,
        )
        if esistente is not None:
            return self._risposta_idempotente(esistente, validazione, request)
        if not validazione.valido:
            return RisultatoGenerazione(
                self._risposta(
                    stato="DATI_NON_VALIDI",
                    messaggio="Documento non generato: i dati ricevuti non sono coerenti con il contratto del modello.",
                    request=request, validazione=validazione, riferimento=None,
                ),
                contenuto=None, nome_file=None,
            )

        titolo = f"{version.modello.tipo_documento.nome} - {version.modello.nome}"
        campi = catalog_repository.list_required_fields(self.db, version.id)
        righe = [(campo.etichetta, request.dati[campo.codice]) for campo in campi if campo.codice in request.dati]
        nome_file = f"{version.modello.codice}-v{version.versione}-{request.external_context_id}.pdf"

        try:
            contenuto = render_pdf(titolo=titolo, righe=righe)
        except Exception:
            fallito = self.storage.registra_fallimento(
                sistema_richiedente=request.sistema_richiedente, external_context_id=request.external_context_id,
                modello_versione_id=version.id, hash_richiesta=hash_richiesta, nome_file=nome_file,
                errore_messaggio="Errore durante la produzione del documento", creato_da=principal.subject,
            )
            return RisultatoGenerazione(
                self._risposta(
                    stato="FALLITO", messaggio="Documento non generato: errore durante la produzione del file.",
                    request=request, validazione=validazione, riferimento=fallito.riferimento,
                ),
                contenuto=None, nome_file=None,
            )

        documento = self.storage.registra_successo(
            sistema_richiedente=request.sistema_richiedente, external_context_id=request.external_context_id,
            modello_versione_id=version.id, hash_richiesta=hash_richiesta, nome_file=nome_file,
            contenuto=contenuto, creato_da=principal.subject,
        )
        return RisultatoGenerazione(
            self._risposta(
                stato="COMPLETATO", messaggio="Documento di test generato correttamente.",
                request=request, validazione=validazione, riferimento=documento.riferimento,
            ),
            contenuto=contenuto, nome_file=nome_file,
        )

    def _risposta_idempotente(
        self, documento: DocumentoGenerato, validazione: ValidazioneResponse, request: ValidazioneRequest,
    ) -> RisultatoGenerazione:
        esito = self._risposta(
            stato=documento.stato,
            messaggio="Richiesta gia' elaborata in precedenza con gli stessi dati: risultato invariato.",
            request=request, validazione=validazione, riferimento=documento.riferimento,
        )
        if documento.stato != "COMPLETATO":
            return RisultatoGenerazione(esito, contenuto=None, nome_file=None)
        return RisultatoGenerazione(
            esito, contenuto=archivio.leggi(documento.percorso_file), nome_file=documento.nome_file,
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
