"""SQLAlchemy models for catalog and data-contract entities."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, ForeignKeyConstraint, Index, Integer, String, Text, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class TipoDocumento(Base):
    __tablename__ = "tipo_documento"
    __table_args__ = (
        UniqueConstraint("integrazione_id", "codice", name="uq_tipo_documento_integrazione_codice"),
        Index("uq_tipo_documento_legacy_codice", "codice", unique=True, postgresql_where=text("integrazione_id IS NULL")),
        ForeignKeyConstraint(
            ["integrazione_id", "codice_contesto"],
            ["integrazione.id", "integrazione.codice_contesto"],
            name="fk_tipo_integrazione_contesto",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    codice: Mapped[str] = mapped_column(String(64), nullable=False)
    nome: Mapped[str] = mapped_column(String(255), nullable=False)
    stato: Mapped[str] = mapped_column(String(32), nullable=False, default="BOZZA")
    spec_owner: Mapped[str] = mapped_column(String(128), nullable=False)
    codice_contesto: Mapped[str] = mapped_column(String(64), nullable=False)
    integrazione_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    modelli: Mapped[list[ModelloDocumento]] = relationship(back_populates="tipo_documento")


class ModelloDocumento(Base):
    __tablename__ = "modello_documento"
    __table_args__ = (
        UniqueConstraint("tipo_documento_id", "codice", name="uq_modello_documento_tipo_codice"),
        # L'indice serve due letture: l'uguaglianza esatta su cui poggia
        # l'unicita' della versione pubblicata (011 FR-004) e il contenimento
        # `dimensioni @> '{"lingua": "IT"}'` che ha sostituito i filtri per
        # colonna di `lista_modelli`.
        Index("ix_modello_documento_dimensioni", "dimensioni", postgresql_using="gin"),
        # Due edizioni derivate dalla stessa origine non possono avere le stesse
        # dimensioni. E' la forma generalizzata dell'indice che 0019 teneva su
        # `(derivato_da_modello_id, lingua)`: protegge dalle creazioni simultanee,
        # dove il controllo applicativo da solo non basta (002 FR-018).
        Index(
            "uq_modello_derivato_padre_lingua",
            "derivato_da_modello_id", "dimensioni",
            unique=True,
            postgresql_where=text("stato <> 'ELIMINATO'"),
        ),
        # Lo slot di categorizzazione e la variante identificano un modello
        # (002 FR-019). Senza questo indice due creazioni simultanee sulla
        # stessa categorizzazione otterrebbero entrambe `STANDARD`, e alla
        # pubblicazione la seconda archivierebbe la prima in silenzio.
        Index(
            "uq_modello_slot_variante",
            "tipo_documento_id", "percorso_categorizzazione", "dimensioni", "variante",
            unique=True,
            postgresql_where=text("stato <> 'ELIMINATO'"),
        ),
        # La nota e' l'etichetta che distingue le varianti per chi legge: due
        # uguali sullo stesso slot non sarebbero distinguibili in interfaccia.
        Index(
            "uq_modello_slot_nota",
            "tipo_documento_id", "percorso_categorizzazione", "dimensioni", "nota",
            unique=True,
            postgresql_where=text("stato <> 'ELIMINATO' AND nota IS NOT NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tipo_documento_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tipo_documento.id", ondelete="CASCADE"), nullable=False
    )
    codice_categoria: Mapped[str] = mapped_column(String(128), nullable=False)
    codice_tipologia: Mapped[str | None] = mapped_column(String(128), nullable=True)
    percorso_categorizzazione: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    public_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, unique=True)
    codice: Mapped[str] = mapped_column(String(128), nullable=False)
    nome: Mapped[str] = mapped_column(String(255), nullable=False)
    variante: Mapped[str] = mapped_column(String(64), nullable=False, default="STANDARD")
    # Il testo con cui il gestore dice in cosa la variante differisce. `nome`
    # resta generato e non modificabile: i due campi non si sostituiscono.
    nota: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # 011 DEC-011-PERSISTENZA-DIMENSIONI: la categorizzazione non e' piu' due
    # colonne dedicate ma un documento per nome di dimensione. Una chiave
    # assente significa dimensione non valorizzata, ed e' l'unico modo per
    # esprimerlo (FR-006): nessun valore `null` dentro il documento, cosi' non
    # c'e' ambiguita' fra "non valorizzata" e "valorizzata a nulla".
    # `variante` resta una colonna propria: la decide l'admin, mentre le
    # dimensioni le dichiara l'integrazione (FR-012), e i due assi non si
    # fondono.
    dimensioni: Mapped[dict[str, str]] = mapped_column(JSONB, nullable=False, default=dict)
    derivato_da_modello_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("modello_documento.id", ondelete="SET NULL"), nullable=True
    )
    stato: Mapped[str] = mapped_column(String(32), nullable=False, default="BOZZA")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    tipo_documento: Mapped[TipoDocumento] = relationship(back_populates="modelli")
    versioni: Mapped[list[ModelloDocumentoVersione]] = relationship(back_populates="modello")
    modello_origine: Mapped[ModelloDocumento | None] = relationship(
        remote_side=[id], foreign_keys=[derivato_da_modello_id], back_populates="edizioni_derivate"
    )
    edizioni_derivate: Mapped[list[ModelloDocumento]] = relationship(
        foreign_keys=[derivato_da_modello_id], back_populates="modello_origine"
    )


class ModelloDocumentoVersione(Base):
    __tablename__ = "modello_versione"
    __table_args__ = (
        UniqueConstraint("modello_documento_id", "versione", name="uq_modello_versione_documento_versione"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    public_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, unique=True)
    modello_documento_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("modello_documento.id", ondelete="CASCADE"), nullable=False
    )
    versione: Mapped[int] = mapped_column(Integer, nullable=False)
    stato: Mapped[str] = mapped_column(String(32), nullable=False, default="BOZZA")
    formato_documentale: Mapped[str] = mapped_column(String(64), nullable=False, default="GEMODO_DOCUMENT_V1")
    struttura_documentale: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    data_inizio_validita: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    data_fine_validita: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    pubblicato_il: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    pubblicato_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # 010 FR-014: il ramo **com'era** quando la versione e' nata. Immutabile:
    # descrive il passato, quindi nessun ciclo di verifica lo riscrive.
    # Nullo sulle versioni anteriori alla migration 0022, che non hanno una
    # firma e non possono averne una inventata (vedi la sua docstring).
    firma_algoritmo: Mapped[str | None] = mapped_column(String(32), nullable=True)
    firma_contratto: Mapped[str | None] = mapped_column(String(64), nullable=True)
    contratto_firmato: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    modello: Mapped[ModelloDocumento] = relationship(back_populates="versioni")
    campi: Mapped[list[ModelloCampoRichiesto]] = relationship(back_populates="versione_modello")
    esito_compatibilita: Mapped["EsitoCompatibilitaVersione | None"] = relationship(
        back_populates="versione", uselist=False, cascade="all, delete-orphan",
    )
    # Ordinate per `ordine`: la sequenza e' parte del documento, non un
    # dettaglio di presentazione, quindi non puo' dipendere da come il
    # database restituisce le righe (003 T001).
    sezioni: Mapped[list["SezioneModello"]] = relationship(
        back_populates="versione",
        order_by="SezioneModello.ordine",
        cascade="all, delete-orphan",
    )


class SezioneModello(Base):
    """Una sezione del documento composto, propria della versione (003 T001).

    La tabella esiste dalla migration `0001` e finora non aveva un mapping:
    nessuna migration di struttura serve qui. Le sezioni **appartengono alla
    versione**, non al modello: si modificano solo finche' la versione e'
    in `BOZZA`, e una versione nuova ne riceve una copia, come gia' accade
    per i campi. Non hanno un versionamento proprio - decisione 2026-06-19.

    `contenuto` serializza una lista di `BloccoDocumento` (003 T002). I
    Pydantic non sono ridefiniti qui: vivono in `app/documentale/schemas.py`
    e sono gli stessi che descrivono il modello documentale controllato.
    """

    __tablename__ = "sezione_modello"
    __table_args__ = (
        UniqueConstraint("modello_versione_id", "codice", name="uq_sezione_modello_versione_codice"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    modello_versione_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("modello_versione.id", ondelete="CASCADE"), nullable=False
    )
    codice: Mapped[str] = mapped_column(String(128), nullable=False)
    ordine: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    contenuto: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    versione: Mapped[ModelloDocumentoVersione] = relationship(back_populates="sezioni")


class EsitoCompatibilitaVersione(Base):
    """Ultimo confronto fra la versione e il ramo live (010 FR-014/FR-015).

    Sta fuori da `modello_versione` perche' e' l'unico dato che il runner
    riscrive: tenerlo li' avrebbe aggiornato una versione pubblicata a ogni
    ciclo. L'esito e' distinto dallo stato di pubblicazione - una versione
    `PUBBLICATO` puo' essere `DA_AGGIORNARE` senza smettere di essere
    pubblicata - e un errore esterno resta `NON_VERIFICABILE`, mai allineato.
    """

    __tablename__ = "esito_compatibilita_versione"
    __table_args__ = (
        UniqueConstraint("modello_versione_id", name="uq_esito_compatibilita_versione"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    modello_versione_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("modello_versione.id", ondelete="CASCADE"), nullable=False
    )
    esito: Mapped[str] = mapped_column(String(32), nullable=False)
    verificato_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    differenze: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    firma_osservata: Mapped[str | None] = mapped_column(String(64), nullable=True)

    versione: Mapped[ModelloDocumentoVersione] = relationship(back_populates="esito_compatibilita")


class PolicyDimensione(Base):
    """Dichiara se una dimensione della categorizzazione ammette un valore generico.

    Una riga per `(tipo_documento_id, nome_dimensione)`: la policy vale ovunque
    quel nome ricompaia nell'albero di quel tipo documento, mai per singola
    foglia. Esplicitamente scollegata da `DefinizioneStruttura` (010), che e'
    solo l'esempio presentazionale per il team dell'integrazione e non deve mai
    determinare il comportamento a runtime - vedi DEC-002-POLICY.
    """

    __tablename__ = "policy_dimensione"
    __table_args__ = (
        UniqueConstraint("tipo_documento_id", "nome_dimensione", name="uq_policy_dimensione_tipo_nome"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tipo_documento_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tipo_documento.id", ondelete="CASCADE"), nullable=False
    )
    nome_dimensione: Mapped[str] = mapped_column(String(64), nullable=False)
    consente_valore_generico: Mapped[bool] = mapped_column(Boolean, nullable=False)
    # 011 DEC-011-DEFAULT-DIMENSIONE: il valore che il form preseleziona.
    # NULL significa "nessuna preselezione", ed e' anche il modo di dire "per
    # questa dimensione il default e' il generico". Non e' vincolato ai valori
    # dell'albero live: un valore che sparisce va segnalato, non cancellato
    # (stesso principio di FR-009).
    valore_default: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_by: Mapped[str | None] = mapped_column(String(255), nullable=True)


class ModelloCampoRichiesto(Base):
    __tablename__ = "campo_modello"
    __table_args__ = (
        # NULLS NOT DISTINCT: 0.7.0 ammette il campo senza lingua, e in PostgreSQL
        # due NULL non si equivalgono - senza questo, due campi con lo stesso
        # codice e lingua assente convivrebbero sulla stessa versione.
        UniqueConstraint(
            "modello_versione_id", "codice", "lingua",
            name="uq_campo_modello_versione_codice_lingua",
            postgresql_nulls_not_distinct=True,
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    modello_versione_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("modello_versione.id", ondelete="CASCADE"), nullable=False
    )
    codice: Mapped[str] = mapped_column(String(128), nullable=False)
    etichetta: Mapped[str] = mapped_column(String(255), nullable=False)
    descrizione: Mapped[str | None] = mapped_column(Text, nullable=True)
    tipo_dato: Mapped[str] = mapped_column(String(32), nullable=False)
    obbligatorio: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Assente quando la foglia discovery dichiara le lingue per se' (0.7.0):
    # il contratto del campo vale allora per tutte, e non ne ha una propria.
    lingua: Mapped[str | None] = mapped_column(String(8), nullable=True)
    ordine: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    formato: Mapped[str | None] = mapped_column(String(64), nullable=True)
    valore_default: Mapped[str | None] = mapped_column(Text, nullable=True)
    opzioni: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    validazione: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    versione_modello: Mapped[ModelloDocumentoVersione] = relationship(back_populates="campi")


class AuditEventoModello(Base):
    """Evento audit per creazione/transizione di stato di modelli e versioni (002)."""

    __tablename__ = "audit_evento_modello"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tipo_evento: Mapped[str] = mapped_column(String(64), nullable=False)
    soggetto_id: Mapped[str] = mapped_column(String(255), nullable=False)
    client_id: Mapped[str] = mapped_column(String(255), nullable=False)
    ruoli: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    modello_documento_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("modello_documento.id", ondelete="CASCADE"), nullable=False
    )
    modello_versione_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("modello_versione.id", ondelete="SET NULL"), nullable=True
    )
    payload_minimo: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
