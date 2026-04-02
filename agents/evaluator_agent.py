from providers.llm.base import BaseLLMProvider
from orchestrator.state import InterviewState, AnswerRecord
from datetime import datetime


class EvaluatorAgent:

    def __init__(self, llm: BaseLLMProvider):
        self.llm = llm

    async def evaluate(
        self,
        candidate_text: str,
        agent_question: str,
        state: InterviewState
    ) -> AnswerRecord:

        if not candidate_text or not candidate_text.strip():
            return self._empty_record(state)

        scores = await self._score_answer(candidate_text, agent_question, state)
        confidence = self._measure_confidence(candidate_text, state)
        quadrant = self._classify_quadrant(scores["technical_accuracy"], confidence)
        honesty = self._score_honesty(candidate_text, scores)
        self._update_trajectory(scores["technical_accuracy"], state)
        self._update_consecutive(scores["technical_accuracy"], state)

        record = AnswerRecord(
            turn_number=state.turn_number,
            phase=state.phase,
            candidate_text=candidate_text,
            agent_text=agent_question,
            topic=state.current_topic,
            question_type=state.current_question_type,
            technical_accuracy=scores["technical_accuracy"],
            confidence_level=confidence,
            quadrant=quadrant,
            intellectual_honesty=honesty,
            suspicious_flag=scores.get("suspicious", False),
            difficulty_level=state.difficulty_level,
            hint_given=state.last_hint_turn == state.turn_number,
            recovery_score=scores.get("recovery_score", 0.0),
            timestamp=datetime.utcnow()
        )

        state.answers.append(record)
        return record

    async def _score_answer(
        self,
        candidate_text: str,
        agent_question: str,
        state: InterviewState
    ) -> dict:

        system_prompt = f"""You are evaluating a VLSI interview answer.

Domain: {state.domain.replace("_", " ")}
Experience level: {state.experience_level.replace("_", " ")}
Topic: {state.current_topic}
Question type: {state.current_question_type}
Difficulty level: {state.difficulty_level} of 5

Evaluate the candidate's answer and return ONLY valid JSON:
{{
    "technical_accuracy": 0.0 to 1.0,
    "topic_covered": "topic name or null",
    "follow_up_needed": true or false,
    "hint_suggested": true or false,
    "suspicious": true or false,
    "recovery_score": 0.0 to 1.0,
    "quality": "strong" or "average" or "weak" or "no_answer"
}}

Scoring guide:
- technical_accuracy: 0.9+ = excellent, 0.7-0.9 = good, 0.5-0.7 = partial, below 0.5 = weak
- suspicious: true if answer is unusually perfect with no hesitation or personal details
- hint_suggested: true if candidate clearly knows the concept but is struggling to articulate
- recovery_score: only relevant if a hint was given in previous turn"""

        messages = [
            {
                "role": "user",
                "content": f"Question: {agent_question}\n\nCandidate answer: {candidate_text}"
            }
        ]

        try:
            result = await self.llm.generate_json(messages, system_prompt)
            return result
        except Exception:
            return {
                "technical_accuracy": 0.5,
                "topic_covered": state.current_topic,
                "follow_up_needed": False,
                "hint_suggested": False,
                "suspicious": False,
                "recovery_score": 0.0,
                "quality": "average"
            }

    def _measure_confidence(self, text: str, state: InterviewState) -> float:
        if not text:
            return 0.0

        words = text.split()
        word_count = len(words)

        fillers = ["um", "uh", "like", "basically", "you know", "so", "actually"]
        filler_count = sum(1 for w in words if w.lower().strip(".,") in fillers)
        filler_ratio = filler_count / max(word_count, 1)

        hedges = ["i think", "maybe", "perhaps", "i'm not sure", "i believe", "probably"]
        hedge_count = sum(1 for h in hedges if h in text.lower())
        hedge_ratio = hedge_count / max(word_count / 10, 1)

        confidence = 1.0 - (filler_ratio * 0.4) - (hedge_ratio * 0.3)

        baseline = state.baseline_metrics.get("filler_frequency", 0.1)
        if filler_ratio < baseline * 0.3 and word_count > 50:
            confidence = min(confidence + 0.2, 1.0)

        return max(0.0, min(1.0, confidence))

    def _classify_quadrant(
        self,
        technical_accuracy: float,
        confidence: float
    ) -> str:
        accurate = technical_accuracy >= 0.6
        confident = confidence >= 0.6

        if accurate and confident:
            return "genuine_expert"
        elif accurate and not confident:
            return "genuine_nervous"
        elif not accurate and confident:
            return "dangerous_fake"
        else:
            return "honestly_underprepared"

    def _score_honesty(self, text: str, scores: dict) -> float:
        text_lower = text.lower()
        admits_ignorance = any(phrase in text_lower for phrase in [
            "i don't know", "i'm not sure", "i haven't worked on",
            "i haven't encountered", "i'm not familiar", "i don't have experience"
        ])

        if admits_ignorance:
            accuracy = scores.get("technical_accuracy", 0.0)
            if accuracy > 0.5:
                return 1.0
            else:
                return 0.8
        else:
            accuracy = scores.get("technical_accuracy", 0.5)
            confidence_penalty = 0.2 if scores.get("suspicious", False) else 0.0
            return max(0.0, accuracy - confidence_penalty)

    def _update_trajectory(self, accuracy: float, state: InterviewState):
        total = len(state.answers)
        target = state.target_questions

        if total < target // 3:
            state.trajectory_early = (
                (state.trajectory_early * max(total - 1, 0) + accuracy) /
                max(total, 1)
            )
        elif total < (target * 2) // 3:
            mid_count = total - target // 3
            state.trajectory_mid = (
                (state.trajectory_mid * max(mid_count - 1, 0) + accuracy) /
                max(mid_count, 1)
            )
        else:
            late_count = total - (target * 2) // 3
            state.trajectory_late = (
                (state.trajectory_late * max(late_count - 1, 0) + accuracy) /
                max(late_count, 1)
            )

    def _update_consecutive(self, accuracy: float, state: InterviewState):
        if accuracy >= 0.7:
            state.consecutive_strong += 1
            state.consecutive_weak = 0
        elif accuracy <= 0.4:
            state.consecutive_weak += 1
            state.consecutive_strong = 0
        else:
            state.consecutive_strong = 0
            state.consecutive_weak = 0

    def _empty_record(self, state: InterviewState) -> AnswerRecord:
        return AnswerRecord(
            turn_number=state.turn_number,
            phase=state.phase,
            candidate_text="",
            agent_text="",
            topic=state.current_topic,
            question_type=state.current_question_type,
            technical_accuracy=0.0,
            confidence_level=0.0,
            quadrant="honestly_underprepared",
            intellectual_honesty=0.5,
            suspicious_flag=False,
            difficulty_level=state.difficulty_level,
            hint_given=False,
            recovery_score=0.0
        )