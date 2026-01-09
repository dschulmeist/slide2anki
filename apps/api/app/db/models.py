"""Database models for the slide2anki API."""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, JSON, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all models."""

    pass


class Deck(Base):
    """A collection of flashcards generated from a PDF."""

    __tablename__ = "decks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="created")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    uploads: Mapped[list["Upload"]] = relationship(
        back_populates="deck", cascade="all, delete-orphan"
    )
    slides: Mapped[list["Slide"]] = relationship(
        back_populates="deck", cascade="all, delete-orphan"
    )
    jobs: Mapped[list["Job"]] = relationship(
        back_populates="deck", cascade="all, delete-orphan"
    )
    cards: Mapped[list["CardDraft"]] = relationship(
        back_populates="deck", cascade="all, delete-orphan"
    )
    exports: Mapped[list["Export"]] = relationship(
        back_populates="deck", cascade="all, delete-orphan"
    )


class Upload(Base):
    """A PDF upload associated with a deck."""

    __tablename__ = "uploads"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    deck_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("decks.id"), nullable=False
    )
    pdf_object_key: Mapped[str] = mapped_column(String(512), nullable=False)
    page_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    deck: Mapped["Deck"] = relationship(back_populates="uploads")
    jobs: Mapped[list["Job"]] = relationship(
        back_populates="upload", cascade="all, delete-orphan"
    )


class Slide(Base):
    """A rendered slide image from a PDF."""

    __tablename__ = "slides"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    deck_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("decks.id"), nullable=False
    )
    page_index: Mapped[int] = mapped_column(Integer, nullable=False)
    image_object_key: Mapped[str] = mapped_column(String(512), nullable=False)

    # Relationships
    deck: Mapped["Deck"] = relationship(back_populates="slides")
    claims: Mapped[list["Claim"]] = relationship(
        back_populates="slide", cascade="all, delete-orphan"
    )


class Job(Base):
    """A processing job for a deck."""

    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    deck_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("decks.id"), nullable=False
    )
    upload_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("uploads.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(50), default="pending")
    progress: Mapped[int] = mapped_column(Integer, default=0)
    current_step: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    logs_object_key: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    deck: Mapped["Deck"] = relationship(back_populates="jobs")
    upload: Mapped["Upload"] = relationship(back_populates="jobs")


class Claim(Base):
    """An extracted claim from a slide."""

    __tablename__ = "claims"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    slide_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("slides.id"), nullable=False
    )
    kind: Mapped[str] = mapped_column(String(50), nullable=False)
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    evidence_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Relationships
    slide: Mapped["Slide"] = relationship(back_populates="claims")


class CardDraft(Base):
    """A generated flashcard draft."""

    __tablename__ = "card_drafts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    deck_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("decks.id"), nullable=False
    )
    front: Mapped[str] = mapped_column(Text, nullable=False)
    back: Mapped[str] = mapped_column(Text, nullable=False)
    tags: Mapped[Optional[list]] = mapped_column(JSON, default=list)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    flags_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    evidence_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="pending")

    # Relationships
    deck: Mapped["Deck"] = relationship(back_populates="cards")


class Export(Base):
    """An exported deck file."""

    __tablename__ = "exports"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    deck_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("decks.id"), nullable=False
    )
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    object_key: Mapped[str] = mapped_column(String(512), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    deck: Mapped["Deck"] = relationship(back_populates="exports")
