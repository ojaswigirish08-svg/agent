from datetime import datetime
from orchestrator.state import InterviewState


SIGNAL_WEIGHTS = {
    "tab_switch": 0.3,
    "tab_switch_perfect_answer": 0.8,
    "window_blur": 0.1,
    "paste_detected": 0.5,
    "consistent_delay": 0.7,
    "zero_fillers_complex": 0.5,
    "generic_anchor_answer": 0.4,
    "sophistication_mismatch": 0.4,
}

WHITELISTED_DOMAINS = [
    "localhost:8000",
    "localhost:3000",
]


class AntiCheatAgent:

    def __init__(self, config: dict):
        self.config = config
        custom_domains = config.get("anti_cheat", {}).get("whitelisted_domains", [])
        self.whitelisted_domains = WHITELISTED_DOMAINS + custom_domains
        custom_weights = config.get("anti_cheat", {}).get("signal_weights", {})
        self.weights = {**SIGNAL_WEIGHTS, **custom_weights}

    def process_signal(
        self,
        signal_type: str,
        signal_data: dict,
        state: InterviewState
    ) -> dict:

        if self._is_whitelisted(signal_data.get("destination", "")):
            return {"flagged": False, "reason": "whitelisted"}

        weight = self.weights.get(signal_type, 0.1)

        if signal_type == "tab_switch":
            last_answer = state.answers[-1] if state.answers else None
            if last_answer and last_answer.technical_accuracy > 0.8:
                weight = self.weights.get("tab_switch_perfect_answer", 0.8)
                signal_type = "tab_switch_perfect_answer"

        signal_record = {
            "type": signal_type,
            "weight": weight,
            "context": signal_data,
            "turn": state.turn_number,
            "topic": state.current_topic,
            "timestamp": datetime.utcnow().isoformat(),
            "flagged": True
        }

        state.signals_log.append(signal_record)
        state.suspicion_score = min(1.0, state.suspicion_score + weight)

        if state.current_topic:
            current = state.topic_suspicion.get(state.current_topic, 0.0)
            state.topic_suspicion[state.current_topic] = min(
                1.0, current + weight * 0.5
            )

        return signal_record

    def get_integrity_verdict(self, state: InterviewState) -> dict:
        score = state.suspicion_score
        total_signals = len(state.signals_log)

        if score < 0.3:
            verdict = "clean"
            integrity_score = 100
        elif score < 0.6:
            verdict = "low_suspicion"
            integrity_score = int(70 - (score * 30))
        elif score < 0.85:
            verdict = "moderate_suspicion"
            integrity_score = int(50 - (score * 20))
        else:
            verdict = "high_suspicion"
            integrity_score = int(20 - (score * 10))

        integrity_score = max(0, min(100, integrity_score))

        flagged_topics = {
            topic: round(score, 2)
            for topic, score in state.topic_suspicion.items()
            if score > 0.3
        }

        return {
            "integrity_score": integrity_score,
            "verdict": verdict,
            "total_signals": total_signals,
            "suspicion_score": round(score, 2),
            "flagged_topics": flagged_topics,
            "signals": state.signals_log
        }

    def _is_whitelisted(self, destination: str) -> bool:
        if not destination:
            return False
        return any(domain in destination for domain in self.whitelisted_domains)