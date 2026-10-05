"""Il registro attivita' letto in un solo elenco (013 FR-011).

Ogni fonte resta dov'e': le generazioni nel loro registro, gli eventi di
modelli, configurazione e integrazioni nelle loro tabelle di audit, le
validazioni e gli accessi negati in `evento_attivita`. Qui si uniscono, in
ordine di tempo, con le stesse colonne. Gli eventi senza `username` (scritti
prima della 013) lo prendono da un'altra riga dello stesso soggetto, se c'e'.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

CATEGORIE = ("GENERAZIONE", "VALIDAZIONE", "ACCESSO", "MODELLO", "CONFIGURAZIONE", "INTEGRAZIONE")

_UNIONE = """
WITH eventi AS (
    SELECT d.created_at AS quando, 'GENERAZIONE' AS categoria, 'GENERAZIONE' AS azione,
           d.stato AS esito, d.creato_da AS soggetto, d.username, d.client_id,
           t.codice_contesto AS contesto, 'documento' AS oggetto_tipo, d.riferimento AS oggetto_id,
           m.nome AS oggetto_nome,
           jsonb_strip_nulls(jsonb_build_object(
               'sistema_richiedente', d.sistema_richiedente,
               'external_context_id', d.external_context_id,
               'modello', m.codice, 'versione', v.versione, 'modello_versione_id', v.public_id,
               'hash_dati', d.hash_dati, 'hash_file', d.hash_file,
               'dimensione_byte', d.dimensione_byte, 'errore', d.errore_messaggio
           )) AS dettaglio
    FROM documento_generato d
    JOIN modello_versione v ON v.id = d.modello_versione_id
    JOIN modello_documento m ON m.id = v.modello_documento_id
    JOIN tipo_documento t ON t.id = m.tipo_documento_id
    UNION ALL
    SELECT a.created_at, 'MODELLO', a.tipo_evento, 'OK', a.soggetto_id, a.username, a.client_id,
           t.codice_contesto, 'modello', a.modello_documento_id::text, m.nome, a.payload_minimo
    FROM audit_evento_modello a
    LEFT JOIN modello_documento m ON m.id = a.modello_documento_id
    LEFT JOIN tipo_documento t ON t.id = m.tipo_documento_id
    UNION ALL
    SELECT c.created_at, 'CONFIGURAZIONE', c.tipo_evento, 'OK', c.soggetto_id, c.username, c.client_id,
           t.codice_contesto, 'tipo_documento', c.tipo_documento_id::text, t.nome, c.payload_minimo
    FROM audit_evento_configurazione c
    LEFT JOIN tipo_documento t ON t.id = c.tipo_documento_id
    UNION ALL
    SELECT i.created_at, 'INTEGRAZIONE', i.tipo_evento, 'OK', i.soggetto_id, i.username, i.client_id,
           g.codice_contesto, 'integrazione', i.integrazione_id::text, g.nome, i.payload_minimo
    FROM audit_evento_integrazione i
    LEFT JOIN integrazione g ON g.id = i.integrazione_id
    UNION ALL
    SELECT e.created_at, e.categoria, e.azione, e.esito, e.soggetto, e.username, e.client_id,
           e.contesto, e.oggetto_tipo, e.oggetto_id, NULL, e.dettaglio
    FROM evento_attivita e
),
nomi AS (
    SELECT soggetto, max(username) AS username
    FROM eventi WHERE soggetto IS NOT NULL AND username IS NOT NULL
    GROUP BY soggetto
)
SELECT e.quando, e.categoria, e.azione, e.esito, e.soggetto,
       coalesce(e.username, n.username) AS username, e.client_id, e.contesto,
       e.oggetto_tipo, e.oggetto_id, e.oggetto_nome, e.dettaglio
FROM eventi e
LEFT JOIN nomi n ON n.soggetto = e.soggetto
WHERE (CAST(:da AS timestamptz) IS NULL OR e.quando >= CAST(:da AS timestamptz))
  AND (CAST(:a AS timestamptz) IS NULL OR e.quando < CAST(:a AS timestamptz))
  AND (CAST(:categoria AS text) IS NULL OR e.categoria = CAST(:categoria AS text))
  AND (CAST(:esito AS text) IS NULL OR e.esito = CAST(:esito AS text))
  AND (CAST(:utente AS text) IS NULL
       OR coalesce(e.username, n.username, '') ILIKE CAST(:utente AS text)
       OR coalesce(e.soggetto, '') ILIKE CAST(:utente AS text)
       OR coalesce(e.client_id, '') ILIKE CAST(:utente AS text))
  AND (CAST(:testo AS text) IS NULL
       OR coalesce(e.oggetto_nome, '') ILIKE CAST(:testo AS text)
       OR coalesce(e.oggetto_id, '') ILIKE CAST(:testo AS text)
       OR e.azione ILIKE CAST(:testo AS text)
       OR e.dettaglio::text ILIKE CAST(:testo AS text))
ORDER BY e.quando DESC
LIMIT :limite OFFSET :salto
"""


@dataclass(frozen=True)
class FiltroAttivita:
    da: datetime | None = None
    a: datetime | None = None
    categoria: str | None = None
    esito: str | None = None
    utente: str | None = None
    testo: str | None = None


def _simile(valore: str | None) -> str | None:
    """Cerca il testo dentro il campo, con i caratteri jolly di LIKE trattati come testo."""
    if not valore or not valore.strip():
        return None
    pulito = valore.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{pulito}%"


def elenco(db: Session, filtro: FiltroAttivita, *, limite: int, salto: int) -> list[dict[str, Any]]:
    righe = db.execute(text(_UNIONE), {
        "da": filtro.da, "a": filtro.a, "categoria": filtro.categoria or None, "esito": filtro.esito or None,
        "utente": _simile(filtro.utente), "testo": _simile(filtro.testo),
        "limite": limite, "salto": salto,
    }).mappings()
    return [dict(riga) for riga in righe]
