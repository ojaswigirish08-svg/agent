import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional


@dataclass
class AnswerRecord:
    turn_number: int
    phase: str
    candidate_text: str
    agent_text: str
    topic: str
    question_type: str
    technical_accuracy: float
    confidence_level: float
    quadrant: str
    intellectual_honesty: float
    suspicious_flag: bool
    difficulty_level: int
    hint_given: bool
    recovery_score: float
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class InterviewState:

    # Identity
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    candidate_id: str = ""
    mode: str = "mock"

    # Candidate Profile
    domain: str = ""
    experience_level: str = ""
    years_experience: int = 0
    tech_stack: List[str] = field(default_factory=list)
    resume_summary: str = ""

    # Phase Management
    phase: str = "warmup"
    turn_number: int = 0
    questions_asked: int = 0
    time_started: datetime = field(default_factory=datetime.utcnow)
    interview_ended: bool = False

    # Behavioral Baseline
    baseline_metrics: Dict = field(default_factory=dict)
    warmup_complete: bool = False
    warmup_turns: int = 0

    # Topic State
    covered_topics: List[str] = field(default_factory=list)
    current_topic: str = ""
    current_question_type: str = "definition"
    difficulty_level: int = 1
    consecutive_strong: int = 0
    consecutive_weak: int = 0
    contradiction_pairs: Dict = field(default_factory=dict)
    anchors_injected: int = 0
    last_anchor_turn: int = 0
    numerical_probes_done: int = 0
    last_hint_turn: int = -1

    # Performance State
    answers: List[AnswerRecord] = field(default_factory=list)
    trajectory_early: float = 0.0
    trajectory_mid: float = 0.0
    trajectory_late: float = 0.0
    trajectory_type: str = ""

    # Behavioral State
    deviation_flags: List[Dict] = field(default_factory=list)
    suspicion_score: float = 0.0
    topic_suspicion: Dict = field(default_factory=dict)

    # Anti-Cheat Signals
    signals_log: List[Dict] = field(default_factory=list)

    # Conversation History
    conversation_history: List[Dict] = field(default_factory=list)

    # Final
    evaluation_complete: bool = False
    reports_generated: bool = False

    # Target counts from config
    target_questions: int = 10
    duration_minutes: int = 25