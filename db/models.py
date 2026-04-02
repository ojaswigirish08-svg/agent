import uuid
from datetime import datetime
from sqlalchemy import String, Float, Boolean, Integer, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from db.connection import Base


class Candidate(Base):
    __tablename__ = "candidates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    resume_url: Mapped[str] = mapped_column(String(500), nullable=True)
    resume_text: Mapped[str] = mapped_column(Text, nullable=True)
    domain: Mapped[str] = mapped_column(String(100), nullable=True)
    experience_level: Mapped[str] = mapped_column(String(100), nullable=True)
    years_experience: Mapped[int] = mapped_column(Integer, nullable=True)
    tech_stack: Mapped[dict] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    sessions: Mapped[list["Session"]] = relationship("Session", back_populates="candidate")


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("candidates.id"), nullable=False)
    domain: Mapped[str] = mapped_column(String(100), nullable=False)
    experience_level: Mapped[str] = mapped_column(String(100), nullable=False)
    mode: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="active")
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    ended_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    candidate: Mapped["Candidate"] = relationship("Candidate", back_populates="sessions")
    turns: Mapped[list["InterviewTurn"]] = relationship("InterviewTurn", back_populates="session")
    signals: Mapped[list["AntiCheatSignal"]] = relationship("AntiCheatSignal", back_populates="session")
    reports: Mapped[list["Report"]] = relationship("Report", back_populates="session")


class InterviewTurn(Base):
    __tablename__ = "interview_turns"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sessions.id"), nullable=False)
    turn_number: Mapped[int] = mapped_column(Integer, nullable=False)
    phase: Mapped[str] = mapped_column(String(50), nullable=False)
    candidate_text: Mapped[str] = mapped_column(Text, nullable=True)
    agent_text: Mapped[str] = mapped_column(Text, nullable=True)
    topic: Mapped[str] = mapped_column(String(100), nullable=True)
    question_type: Mapped[str] = mapped_column(String(100), nullable=True)
    technical_accuracy: Mapped[float] = mapped_column(Float, nullable=True)
    confidence_level: Mapped[float] = mapped_column(Float, nullable=True)
    quadrant: Mapped[str] = mapped_column(String(100), nullable=True)
    intellectual_honesty: Mapped[float] = mapped_column(Float, nullable=True)
    suspicious_flag: Mapped[bool] = mapped_column(Boolean, default=False)
    difficulty_level: Mapped[int] = mapped_column(Integer, nullable=True)
    hint_given: Mapped[bool] = mapped_column(Boolean, default=False)
    recovery_score: Mapped[float] = mapped_column(Float, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    session: Mapped["Session"] = relationship("Session", back_populates="turns")


class AntiCheatSignal(Base):
    __tablename__ = "anticheat_signals"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sessions.id"), nullable=False)
    signal_type: Mapped[str] = mapped_column(String(100), nullable=False)
    weight: Mapped[float] = mapped_column(Float, nullable=False)
    context: Mapped[dict] = mapped_column(JSONB, nullable=True)
    flagged: Mapped[bool] = mapped_column(Boolean, default=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    session: Mapped["Session"] = relationship("Session", back_populates="signals")


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sessions.id"), nullable=False)
    report_type: Mapped[str] = mapped_column(String(50), nullable=False)
    technical_score: Mapped[float] = mapped_column(Float, nullable=True)
    behavioral_score: Mapped[float] = mapped_column(Float, nullable=True)
    integrity_score: Mapped[float] = mapped_column(Float, nullable=True)
    overall_score: Mapped[float] = mapped_column(Float, nullable=True)
    grade: Mapped[str] = mapped_column(String(10), nullable=True)
    recommendation: Mapped[str] = mapped_column(String(100), nullable=True)
    content: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    session: Mapped["Session"] = relationship("Session", back_populates="reports")