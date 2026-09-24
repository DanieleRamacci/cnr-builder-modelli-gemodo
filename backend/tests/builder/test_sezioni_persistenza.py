"""Persistenza delle sezioni di una versione modello (003 T001-T005).

Su PostgreSQL reale: la tabella `sezione_modello` esiste dalla migration
`0001` e finora non aveva un mapping, quindi questi test sono la prima cosa
che la esercita davvero.
"""

from __future__ import annotations

import uuid

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session

from app.builder import repository as builder_repository
from app.catalog.models import ModelloDocumento, ModelloDocumentoVersione, SezioneModello, TipoDocumento
from app.documentale.schemas import BloccoDocumento, PosizionamentoBlocco, TipoBloccoDocumento
from tests.support.postgres import postgres_database_url  # noqa: F401  (fixture)
from tests.builder.test_builder_flow_api import db_engine  # noqa: F401  (fixture)


def blocco(identificativo: str, *, ordine: int = 0, placeholder: list[str] | None = None) -> dict:
    return BloccoDocumento(
        id=identificativo,
        tipo=TipoBloccoDocumento.PARAGRAFO,
        contenuto=f"testo di {identificativo}",
        posizionamento=PosizionamentoBlocco.BODY,
        ordine=ordine,
        placeholder_usati=placeholder or [],
    ).model_dump(mode="json")


@pytest.fixture()
def versione(db_engine):
    """Una versione in bozza, con il suo tipo documento e modello."""
    suffisso = uuid.uuid4().hex[:12]
    with Session(db_engine) as db:
        tipo = TipoDocumento(
            id=uuid.uuid4(), codice=f"SEZIONI_{suffisso}", nome="Tipo sezioni",
            stato="ATTIVA", spec_owner="specs/003-sezioni-placeholder-versionamento",
            codice_contesto="sezioni",
        )
        modello = ModelloDocumento(
            id=uuid.uuid4(), tipo_documento_id=tipo.id, codice_categoria="CAT",
            codice_tipologia="TIP", percorso_categorizzazione=["TIP", "CAT"],
            codice=f"sezioni-{suffisso}", nome="Modello sezioni", variante="STANDARD",
            stato="ATTIVA", dimensioni={},
        )
        riga = ModelloDocumentoVersione(
            id=uuid.uuid4(), modello_documento_id=modello.id, versione=1,
            stato="BOZZA", formato_documentale="GEMODO_DOCUMENT_V1",
            struttura_documentale={},
        )
        db.add_all([tipo, modello, riga])
        db.commit()
        ids = (tipo.id, modello.id, riga.id)
    yield ids
    with Session(db_engine) as db:
        db.execute(sa.delete(ModelloDocumento).where(ModelloDocumento.id == ids[1]))
        db.execute(sa.delete(TipoDocumento).where(TipoDocumento.id == ids[0]))
        db.commit()


@pytest.mark.integration
def test_le_sezioni_si_leggono_sempre_nell_ordine_dichiarato(db_engine, versione):
    """La sequenza e' parte del documento, non dipende da come il DB restituisce le righe."""
    _, _, versione_id = versione
    with Session(db_engine) as db:
        # Inserite di proposito in ordine sparso.
        for codice, ordine in (("chiusura", 30), ("premessa", 10), ("corpo", 20)):
            db.add(SezioneModello(
                id=uuid.uuid4(), modello_versione_id=versione_id,
                codice=codice, ordine=ordine, contenuto=[blocco(codice)],
            ))
        db.commit()

    with Session(db_engine) as db:
        riga = db.get(ModelloDocumentoVersione, versione_id)
        assert [s.codice for s in riga.sezioni] == ["premessa", "corpo", "chiusura"]


@pytest.mark.integration
def test_due_sezioni_non_possono_avere_lo_stesso_codice_sulla_stessa_versione(db_engine, versione):
    _, _, versione_id = versione
    with Session(db_engine) as db:
        db.add(SezioneModello(
            id=uuid.uuid4(), modello_versione_id=versione_id,
            codice="premessa", ordine=10, contenuto=[],
        ))
        db.commit()

    with pytest.raises(sa.exc.IntegrityError):
        with Session(db_engine) as db:
            db.add(SezioneModello(
                id=uuid.uuid4(), modello_versione_id=versione_id,
                codice="premessa", ordine=20, contenuto=[],
            ))
            db.commit()


@pytest.mark.integration
def test_le_sezioni_muoiono_con_la_versione(db_engine, versione):
    """`ON DELETE CASCADE`: una sezione non sopravvive alla versione che la contiene."""
    _, modello_id, versione_id = versione
    with Session(db_engine) as db:
        db.add(SezioneModello(
            id=uuid.uuid4(), modello_versione_id=versione_id,
            codice="premessa", ordine=10, contenuto=[blocco("b1")],
        ))
        db.commit()

    with Session(db_engine) as db:
        db.execute(sa.delete(ModelloDocumento).where(ModelloDocumento.id == modello_id))
        db.commit()

    with Session(db_engine) as db:
        rimaste = db.scalar(sa.select(sa.func.count()).select_from(SezioneModello)
                            .where(SezioneModello.modello_versione_id == versione_id))
        assert rimaste == 0


@pytest.mark.integration
def test_la_composizione_concatena_le_sezioni_e_rinumera_i_blocchi(db_engine, versione):
    """003 T003: le sezioni sono il modo in cui il documento e' conservato, questa e' la forma in cui si legge."""
    _, _, versione_id = versione
    with Session(db_engine) as db:
        db.add(SezioneModello(
            id=uuid.uuid4(), modello_versione_id=versione_id, codice="premessa", ordine=10,
            contenuto=[blocco("intro", ordine=0, placeholder=["codice_bando"]),
                       blocco("sottotitolo", ordine=1)],
        ))
        db.add(SezioneModello(
            id=uuid.uuid4(), modello_versione_id=versione_id, codice="corpo", ordine=20,
            # Riparte da zero: concatenando, senza rinumerazione, si
            # sovrapporrebbe ai blocchi della sezione precedente.
            contenuto=[blocco("dettaglio", ordine=0, placeholder=["codice_bando", "numero_posti"])],
        ))
        db.commit()

    with Session(db_engine) as db:
        riga = db.get(ModelloDocumentoVersione, versione_id)
        documento = builder_repository.composizione_documentale(riga)

    assert [b.id for b in documento.blocchi] == ["intro", "sottotitolo", "dettaglio"]
    assert [b.ordine for b in documento.blocchi] == [0, 1, 2], "ordine progressivo globale"
    assert documento.placeholder_usati == ["codice_bando", "numero_posti"], "unione senza duplicati"
    assert documento.formato == "GEMODO_DOCUMENT_V1"
    assert documento.contiene_html_libero is False


@pytest.mark.integration
def test_una_versione_nuova_eredita_le_sezioni_senza_condividerle(db_engine, versione):
    """003 T004: come per i campi. La copia e' profonda, altrimenti modificare
    la bozza cambierebbe anche il documento gia' pubblicato."""
    _, modello_id, versione_id = versione
    with Session(db_engine) as db:
        db.add(SezioneModello(
            id=uuid.uuid4(), modello_versione_id=versione_id, codice="premessa", ordine=10,
            contenuto=[blocco("intro")],
        ))
        db.commit()

    with Session(db_engine) as db:
        precedente = db.get(ModelloDocumentoVersione, versione_id)
        nuova = builder_repository.crea_versione(
            db, modello_documento_id=modello_id, campi=[],
            sezioni=builder_repository.clona_sezioni(precedente),
        )
        db.commit()
        nuova_id = nuova.id

    with Session(db_engine) as db:
        copia = db.get(ModelloDocumentoVersione, nuova_id)
        assert [s.codice for s in copia.sezioni] == ["premessa"]
        assert copia.sezioni[0].id != versione_id
        # Modificare la copia non tocca l'originale.
        copia.sezioni[0].contenuto = [blocco("riscritto")]
        db.commit()

    with Session(db_engine) as db:
        originale = db.get(ModelloDocumentoVersione, versione_id)
        assert originale.sezioni[0].contenuto[0]["id"] == "intro"
