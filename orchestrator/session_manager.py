import yaml
import os
from typing import Dict, Optional
from orchestrator.state import InterviewState


class SessionManager:

    def __init__(self, config: dict):
        self.config = config
        self.active_sessions: Dict[str, InterviewState] = {}

    def create_session(
        self,
        candidate_id: str,
        domain: str,
        experience_level: str,
        years_experience: int,
        tech_stack: list,
        resume_summary: str,
        mode: str = "mock"
    ) -> InterviewState:

        duration_map = self.config["interview"]["duration"]
        questions_map = self.config["interview"]["questions"]

        duration = duration_map.get(experience_level, 30)
        target_questions = questions_map.get(experience_level, 12)
        difficulty_start = self._get_starting_difficulty(experience_level)

        state = InterviewState(
            candidate_id=candidate_id,
            mode=mode,
            domain=domain,
            experience_level=experience_level,
            years_experience=years_experience,
            tech_stack=tech_stack,
            resume_summary=resume_summary,
            duration_minutes=duration,
            target_questions=target_questions,
            difficulty_level=difficulty_start
        )

        self.active_sessions[state.session_id] = state
        return state

    def get_session(self, session_id: str) -> Optional[InterviewState]:
        return self.active_sessions.get(session_id)

    def end_session(self, session_id: str):
        if session_id in self.active_sessions:
            self.active_sessions[session_id].interview_ended = True

    def remove_session(self, session_id: str):
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]

    def _get_starting_difficulty(self, experience_level: str) -> int:
        level_map = {
            "fresh_graduate": 1,
            "trained_fresher": 2,
            "experienced_junior": 3,
            "experienced_senior": 4
        }
        return level_map.get(experience_level, 2)