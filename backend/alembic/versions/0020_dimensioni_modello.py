"""I valori di dimensione escono dalle colonne dedicate (011, DEC-011-PERSISTENZA-DIMENSIONI).

`modello_documento.lingua` e `modello_documento.livello_professionale`
diventano voci di un documento `dimensioni` per nome di dimensione. Il motivo
non e' estetico: con due colonne, un tipo documento che non ha la lingua fra le
proprie dimensioni ne riceveva comunque una - `lingua` era NOT NULL con default
'IT' - cioe' un dato falso. Con il documento, l'assenza della chiave *e'*
l'assenza della dimensione (FR-006).

Cosa questa migration NON tocca, perche' FR-007 lo richiede:

- `codice` e `nome` dei modelli: nessun ricalcolo. I modelli esistenti
  conservano il nome discorsivo prodotto dalla vecchia `_identita_modello`.
- `modello_versione`: lo stato di pubblicazione vive li' e non passa da queste
  colonne.
- il collegamento del documento generato al modello: e' per id.

ATTENZIONE - IL DOWNGRADE PERDE DATI E NE INVENTA. Ricostruisce `lingua` e
`livello_professionale` dalle chiavi corrispondenti, ma:

- un modello che valorizza dimensioni diverse da quelle due **perde quei
  valori**: non esiste una colonna dove rimetterli;
- un modello **senza** lingua - un tipo documento tipo `contratti`, che e' il
  caso per cui `011` esiste - ne riceve una inventata, `IT`, perche' la colonna
  ricreata e' NOT NULL. E' il dato falso che questa migration elimina, che
  ritorna se si torna indietro.

Entrambe sono inevitabili e vanno sapute prima: un rollback effettuato dopo aver
creato modelli con dimensioni proprie non e' a sua volta reversibile.

Revision ID: 0020
Revises: 0019
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0020"
down_revision = "0019"
branch_labels = None
depends_on = None


# Il nome della dimensione del livello si uniforma a quello della colonna e del
# contratto. Tenere `livello` nelle policy e `livello_professionale` altrove
# avrebbe cablato la traduzione fra i due in `ModelloCatalogoSchema`, cioe'
# avrebbe reintrodotto in piccolo il problema che `011` elimina.
NOME_LIVELLO_VECCHIO = "livello"
NOME_LIVELLO_NUOVO = "livello_professionale"

# L'indice unico parziale creato da 0019. Vive su una colonna che questa
# migration elimina, quindi va ricreato esplicitamente nella forma nuova.
INDICE_EDIZIONE_DERIVATA = "uq_modello_derivato_padre_lingua"


def upgrade() -> None:
    # 1. La colonna nuova. server_default '{}' serve solo a popolare le righe
    #    esistenti senza violare il NOT NULL; viene rimosso subito dopo, cosi'
    #    il default resta una responsabilita' applicativa.
    op.add_column(
        "modello_documento",
        sa.Column("dimensioni", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
    )

    # 2. Popolamento. `lingua` e' NOT NULL, quindi produce sempre la chiave.
    #    `livello_professionale` NULL **non** produce la chiave: assenza di
    #    chiave significa dimensione non valorizzata, che e' esattamente il
    #    significato odierno di quella colonna NULL sotto una policy che ammette
    #    il generico.
    op.execute(
        f"""
        UPDATE modello_documento
        SET dimensioni = jsonb_build_object('lingua', lingua)
            || CASE
                   WHEN livello_professionale IS NULL THEN '{{}}'::jsonb
                   ELSE jsonb_build_object('{NOME_LIVELLO_NUOVO}', livello_professionale)
               END
        """
    )
    op.alter_column("modello_documento", "dimensioni", server_default=None)

    # 3. L'indice che serve l'uguaglianza di FR-004 e il contenimento dei filtri.
    op.create_index(
        "ix_modello_documento_dimensioni",
        "modello_documento",
        ["dimensioni"],
        postgresql_using="gin",
    )

    # 4. Il dominio della lingua non sparisce: si sposta dove gia' viveva
    #    davvero, cioe' nel confronto con `foglia.lingue_possibili`, che e' la
    #    fonte autorevole. E' il punto in cui il database smette di esserne il
    #    custode (DEC-001-LINGUA-IT-EN, riaperta da 011).
    op.drop_constraint("ck_modello_documento_lingua", "modello_documento", type_="check")

    # 5. L'indice unico parziale di 0019 protegge le edizioni derivate dalle
    #    creazioni simultanee: e' su `(derivato_da_modello_id, lingua)`, quindi
    #    `DROP COLUMN lingua` lo eliminerebbe **di riflesso**, in silenzio. Senza
    #    sostituto, due richieste simultanee creerebbero due edizioni gemelle e
    #    il ramo IntegrityError del servizio non scatterebbe mai.
    #    Lo si sostituisce con la forma generalizzata: due edizioni derivate
    #    dalla stessa origine non possono avere le stesse dimensioni, qualunque
    #    sia la dimensione su cui si e' derivato (011 FR-013).
    op.execute(f"DROP INDEX {INDICE_EDIZIONE_DERIVATA}")

    # 6. Via le colonne dedicate.
    op.drop_column("modello_documento", "lingua")
    op.drop_column("modello_documento", "livello_professionale")

    op.execute(
        f"CREATE UNIQUE INDEX {INDICE_EDIZIONE_DERIVATA} ON modello_documento "
        "(derivato_da_modello_id, dimensioni) WHERE stato <> 'ELIMINATO'"
    )

    # 7. Il valore che il form preseleziona diventa una proprieta' dichiarata
    #    della dimensione (DEC-011-DEFAULT-DIMENSIONE), invece che l'ordine con
    #    cui l'integrazione elenca i valori - ordine che il contratto di
    #    discovery non garantisce stabile.
    op.add_column("policy_dimensione", sa.Column("valore_default", sa.String(64), nullable=True))

    # 8. L'uniformazione del nome.
    op.execute(
        f"""
        UPDATE policy_dimensione
        SET nome_dimensione = '{NOME_LIVELLO_NUOVO}'
        WHERE nome_dimensione = '{NOME_LIVELLO_VECCHIO}'
        """
    )

    # 9. I default che conservano il comportamento odierno. E' l'unico punto
    #    della migrazione in cui si scrive una preferenza invece di convertire
    #    un dato, e va fatto: senza, al primo deploy il form smetterebbe di
    #    proporre cio' che propone oggi, che e' un cambiamento che nessuno ha
    #    chiesto. `lingua -> IT` e' il valore che esce oggi; il livello resta
    #    NULL, cioe' "nessuna preselezione", che oggi corrisponde al generico.
    op.execute(
        """
        UPDATE policy_dimensione
        SET valore_default = 'IT'
        WHERE nome_dimensione = 'lingua'
        """
    )


def downgrade() -> None:
    op.execute(
        f"""
        UPDATE policy_dimensione
        SET nome_dimensione = '{NOME_LIVELLO_VECCHIO}'
        WHERE nome_dimensione = '{NOME_LIVELLO_NUOVO}'
        """
    )
    op.drop_column("policy_dimensione", "valore_default")

    # Le colonne tornano nullable per poter essere popolate, poi `lingua` torna
    # NOT NULL come era.
    op.add_column("modello_documento", sa.Column("lingua", sa.String(2), nullable=True))
    op.add_column("modello_documento", sa.Column("livello_professionale", sa.String(64), nullable=True))
    op.execute(
        f"""
        UPDATE modello_documento
        SET lingua = COALESCE(dimensioni ->> 'lingua', 'IT'),
            livello_professionale = dimensioni ->> '{NOME_LIVELLO_NUOVO}'
        """
    )
    op.alter_column("modello_documento", "lingua", nullable=False, server_default=sa.text("'IT'"))
    op.create_check_constraint(
        "ck_modello_documento_lingua",
        "modello_documento",
        "lingua IN ('IT', 'EN')",
    )
    op.execute(f"DROP INDEX {INDICE_EDIZIONE_DERIVATA}")
    op.drop_index("ix_modello_documento_dimensioni", table_name="modello_documento")
    op.drop_column("modello_documento", "dimensioni")
    # Ricreato nella forma che 0019 si aspetta di trovare: il suo downgrade fa
    # DROP INDEX su questo nome.
    op.execute(
        f"CREATE UNIQUE INDEX {INDICE_EDIZIONE_DERIVATA} ON modello_documento "
        "(derivato_da_modello_id, lingua) WHERE stato <> 'ELIMINATO'"
    )
