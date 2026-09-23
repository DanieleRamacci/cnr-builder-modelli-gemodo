"""Fixture SQL allo schema 0019 per verificare la migration 0020."""

from __future__ import annotations

from dataclasses import dataclass
import uuid

import sqlalchemy as sa
from sqlalchemy.engine import Connection


@dataclass(frozen=True)
class StatoMigrazioneDimensioni:
    tipo_id: uuid.UUID
    modello_id: uuid.UUID
    versione_id: uuid.UUID
    documento_id: uuid.UUID
    codice: str
    nome: str


def crea_stato_migrazione_dimensioni(connection: Connection) -> StatoMigrazioneDimensioni:
    """Crea modello pubblicato con livello NULL e documento generato collegato."""
    suffisso = uuid.uuid4().hex[:12]
    stato = StatoMigrazioneDimensioni(
        tipo_id=uuid.uuid4(),
        modello_id=uuid.uuid4(),
        versione_id=uuid.uuid4(),
        documento_id=uuid.uuid4(),
        codice=f"migrazione-dimensioni-{suffisso}",
        nome=f"Modello migrazione dimensioni {suffisso}",
    )
    connection.execute(sa.text("""
        INSERT INTO tipo_documento
            (id, codice, nome, stato, spec_owner, codice_contesto)
        VALUES
            (:id, :codice, :nome, 'ATTIVA', 'specs/011-dimensioni-generiche-modello', 'migrazione')
    """), {"id": stato.tipo_id, "codice": f"MIGRAZIONE_{suffisso}", "nome": stato.nome})
    connection.execute(sa.text("""
        INSERT INTO modello_documento
            (id, tipo_documento_id, codice_categoria, codice_tipologia,
             percorso_categorizzazione, codice, nome, variante, stato,
             lingua, livello_professionale)
        VALUES
            (:id, :tipo_id, 'PROFILO_TEST', 'TIPOLOGIA_TEST',
             '["TIPOLOGIA_TEST", "PROFILO_TEST"]'::jsonb, :codice, :nome,
             'STANDARD', 'ATTIVA', 'IT', NULL)
    """), {
        "id": stato.modello_id,
        "tipo_id": stato.tipo_id,
        "codice": stato.codice,
        "nome": stato.nome,
    })
    connection.execute(sa.text("""
        INSERT INTO modello_versione
            (id, modello_documento_id, versione, stato, formato_documentale,
             struttura_documentale, pubblicato_il, pubblicato_at)
        VALUES
            (:id, :modello_id, 1, 'PUBBLICATO', 'GEMODO_DOCUMENT_V1',
             '{}'::jsonb, now(), now())
    """), {"id": stato.versione_id, "modello_id": stato.modello_id})
    connection.execute(sa.text("""
        INSERT INTO documento_generato
            (id, riferimento, sistema_richiedente, external_context_id,
             modello_versione_id, tipo_output, stato, hash_dati, nome_file,
             hash_file, percorso_file, dimensione_byte, creato_da)
        VALUES
            (:id, :riferimento, 'TEST_MIGRAZIONE', :external_context_id,
             :versione_id, 'PDF', 'COMPLETATO', :hash_dati, 'test.pdf',
             :hash_file, '/tmp/test-migrazione.pdf', 128, 'pytest')
    """), {
        "id": stato.documento_id,
        "riferimento": f"MIG-{suffisso}",
        "external_context_id": suffisso,
        "versione_id": stato.versione_id,
        "hash_dati": "a" * 64,
        "hash_file": "b" * 64,
    })
    return stato

