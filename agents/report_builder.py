from providers.llm.base import BaseLLMProvider
from orchestrator.state import InterviewState
from agents.anti_cheat_agent import AntiCheatAgent


class ReportBuilder:

    def __init__(self, llm: BaseLLMProvider, config: dict):
        self.llm = llm
        self.config = config
        self.anti_cheat = AntiCheatAgent(config)

    async def build(self, state: InterviewState) -> dict:
        technical_score = self._calculate_technical_score(state)
        behavioral_score = self._calculate_behavioral_score(state)
        integrity_report = self.anti_cheat.get_integrity_verdict(state)
        integrity_score = integrity_report["integrity_score"]
        overall_score = self._calculate_overall_score(
            technical_score, behavioral_score, integrity_score
        )
        grade = self._calculate_grade(overall_score)
        trajectory_type = self._determine_trajectory(state)
        topic_performance = self._get_topic_performance(state)
        notable_moments = self._get_notable_moments(state)

        recruiter_report = self._build_recruiter_report(
            state, technical_score, behavioral_score,
            integrity_score, overall_score, grade,
            trajectory_type, topic_performance, notable_moments,
            integrity_report
        )

        mock_report = None
        if state.mode == "mock":
            mock_report = await self._build_mock_report(
                state, technical_score, behavioral_score,
                overall_score, grade, trajectory_type,
                topic_performance
            )

        return {
            "recruiter_report": recruiter_report,
            "mock_report": mock_report,
            "integrity_report": integrity_report,
            "technical_score": technical_score,
            "behavioral_score": behavioral_score,
            "integrity_score": integrity_score,
            "overall_score": overall_score,
            "grade": grade
        }

    def _calculate_technical_score(self, state: InterviewState) -> float:
        if not state.answers:
            return 0.0
        interview_answers = [a for a in state.answers if a.phase == "interview"]
        if not interview_answers:
            return 0.0
        scores = [a.technical_accuracy for a in interview_answers]
        return round(sum(scores) / len(scores) * 100, 1)

    def _calculate_behavioral_score(self, state: InterviewState) -> float:
        if not state.answers:
            return 0.0
        interview_answers = [a for a in state.answers if a.phase == "interview"]
        if not interview_answers:
            return 0.0
        honesty_scores = [a.intellectual_honesty for a in interview_answers]
        honesty_avg = sum(honesty_scores) / len(honesty_scores)
        trajectory_bonus = 0.0
        if state.trajectory_late > state.trajectory_early + 0.15:
            trajectory_bonus = 0.1
        behavioral = (honesty_avg + trajectory_bonus)
        return round(min(1.0, behavioral) * 100, 1)

    def _calculate_overall_score(
        self,
        technical: float,
        behavioral: float,
        integrity: float
    ) -> float:
        if integrity < 40:
            technical = technical * 0.6
        score = (technical * 0.70) + (behavioral * 0.20) + (integrity * 0.10)
        return round(min(100, score), 1)

    def _calculate_grade(self, score: float) -> str:
        if score >= 85:
            return "A"
        elif score >= 75:
            return "B"
        elif score >= 60:
            return "C"
        elif score >= 45:
            return "D"
        else:
            return "F"

    def _determine_trajectory(self, state: InterviewState) -> str:
        early = state.trajectory_early
        mid = state.trajectory_mid
        late = state.trajectory_late
        if late > early + 0.15:
            return "rising"
        elif early > late + 0.15:
            return "falling"
        elif early > 0.65 and late > 0.65:
            return "flat_strong"
        elif early < 0.45 and late < 0.45:
            return "flat_weak"
        else:
            return "spiky"

    def _get_topic_performance(self, state: InterviewState) -> dict:
        topic_scores = {}
        for answer in state.answers:
            if answer.phase != "interview" or not answer.topic:
                continue
            if answer.topic not in topic_scores:
                topic_scores[answer.topic] = []
            topic_scores[answer.topic].append(answer.technical_accuracy)
        result = {}
        for topic, scores in topic_scores.items():
            avg = sum(scores) / len(scores)
            if avg >= 0.75:
                rating = "strong"
            elif avg >= 0.55:
                rating = "adequate"
            else:
                rating = "needs_work"
            result[topic] = {
                "score": round(avg * 100, 1),
                "rating": rating
            }
        return result

    def _get_notable_moments(self, state: InterviewState) -> list:
        moments = []
        for answer in state.answers:
            if answer.phase != "interview":
                continue
            if answer.intellectual_honesty >= 0.9 and answer.technical_accuracy >= 0.5:
                moments.append({
                    "type": "positive",
                    "turn": answer.turn_number,
                    "note": f"Demonstrated intellectual honesty on {answer.topic}"
                })
            if answer.quadrant == "dangerous_fake":
                moments.append({
                    "type": "flag",
                    "turn": answer.turn_number,
                    "note": f"Confident but inaccurate answer on {answer.topic}"
                })
            if answer.technical_accuracy >= 0.9:
                moments.append({
                    "type": "positive",
                    "turn": answer.turn_number,
                    "note": f"Excellent answer on {answer.topic}"
                })
        return moments[:5]

    def _build_recruiter_report(
        self, state, technical_score, behavioral_score,
        integrity_score, overall_score, grade,
        trajectory_type, topic_performance, notable_moments,
        integrity_report
    ) -> dict:
        trajectory_notes = {
            "rising": "Started cautiously but improved significantly � consider nervousness discount on early answers",
            "falling": "Strong opening that degraded � possible memorization pattern",
            "flat_strong": "Consistently strong performance throughout",
            "flat_weak": "Consistently weak � genuinely underprepared",
            "spiky": "Inconsistent performance � cross-reference with integrity signals"
        }
        if overall_score >= 80 and integrity_score >= 70:
            recommendation = "hire"
            rec_note = "Strong candidate � recommend proceeding"
        elif overall_score >= 65 and integrity_score >= 70:
            recommendation = "consider"
            rec_note = "Decent candidate � recommend second round"
        elif integrity_score < 40:
            recommendation = "hold"
            rec_note = "Integrity concerns � further verification recommended"
        else:
            recommendation = "reject"
            rec_note = "Does not meet threshold for this role"

        return {
            "candidate_id": state.candidate_id,
            "session_id": state.session_id,
            "domain": state.domain,
            "experience_level": state.experience_level,
            "scores": {
                "overall": overall_score,
                "technical": technical_score,
                "behavioral": behavioral_score,
                "integrity": integrity_score
            },
            "grade": grade,
            "recommendation": recommendation,
            "recommendation_note": rec_note,
            "trajectory": trajectory_type,
            "trajectory_note": trajectory_notes.get(trajectory_type, ""),
            "topic_performance": topic_performance,
            "notable_moments": notable_moments,
            "integrity_verdict": integrity_report["verdict"],
            "flagged_topics": integrity_report.get("flagged_topics", {})
        }

    async def _build_mock_report(
        self, state, technical_score, behavioral_score,
        overall_score, grade, trajectory_type, topic_performance
    ) -> dict:
        system_prompt = f"""You are generating a detailed mock interview report for a VLSI candidate.

Candidate: {state.domain.replace("_", " ")} � {state.experience_level.replace("_", " ")}
Overall score: {overall_score}/100
Grade: {grade}
Technical score: {technical_score}/100
Behavioral score: {behavioral_score}/100
Trajectory: {trajectory_type}
Topic performance: {topic_performance}
Resume summary: {state.resume_summary}

Generate a detailed, honest, actionable mock report.
Return ONLY valid JSON with this structure:
{{
    "overall_feedback": "2-3 sentence honest assessment",
    "readiness_statement": "specific readiness statement for their target level",
    "strengths": ["specific strength 1", "specific strength 2", "specific strength 3"],
    "areas_of_improvement": [
        {{
            "area": "topic name",
            "feedback": "specific feedback",
            "suggestion": "specific actionable suggestion",
            "timeline": "estimated timeline"
        }}
    ],
    "behavioral_feedback": "honest feedback on interview behavior",
    "recommended_resources": ["specific resource 1", "specific resource 2"],
    "roadmap": [
        {{"week": "Week 1-2", "focus": "what to do"}},
        {{"week": "Week 3-4", "focus": "what to do"}}
    ],
    "next_mock_recommendation": "specific recommendation for next mock session"
}}"""

        messages = [{"role": "user", "content": "Generate the mock interview report."}]

        try:
            return await self.llm.generate_json(messages, system_prompt)
        except Exception:
            return {
                "overall_feedback": f"You scored {overall_score}/100 with grade {grade}.",
                "readiness_statement": "Keep practicing to improve your readiness.",
                "strengths": [],
                "areas_of_improvement": [],
                "behavioral_feedback": "",
                "recommended_resources": [],
                "roadmap": [],
                "next_mock_recommendation": "Continue practicing."
            }