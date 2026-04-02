from orchestrator.state import InterviewState


class BehaviorMonitor:

    def __init__(self):
        self.filler_words = [
            "um", "uh", "like", "basically", "you know",
            "so", "actually", "right", "okay", "well"
        ]
        self.self_corrections = [
            "wait", "actually", "let me rethink",
            "i mean", "sorry", "let me rephrase"
        ]

    def analyze(self, text: str, state: InterviewState) -> dict:
        if not text or not state.baseline_metrics:
            return self._empty_analysis()

        words = text.split()
        word_count = len(words)

        filler_count = sum(
            1 for w in words
            if w.lower().strip(".,?!") in self.filler_words
        )
        filler_freq = filler_count / max(word_count, 1)

        correction_count = sum(
            1 for c in self.self_corrections
            if c in text.lower()
        )
        correction_freq = correction_count / max(word_count / 10, 1)

        sentences = [s.strip() for s in text.replace("!", ".").replace("?", ".").split(".") if s.strip()]
        avg_sentence_length = sum(len(s.split()) for s in sentences) / max(len(sentences), 1)

        deviation_score = self._calculate_deviation(
            filler_freq, word_count, state
        )

        suspicion_delta = self._calculate_suspicion(
            filler_freq, word_count, deviation_score, state
        )

        if suspicion_delta > 0.3:
            state.deviation_flags.append({
                "turn": state.turn_number,
                "topic": state.current_topic,
                "filler_freq": filler_freq,
                "word_count": word_count,
                "deviation": deviation_score,
                "suspicion_delta": suspicion_delta
            })
            state.suspicion_score += suspicion_delta
            if state.current_topic:
                current = state.topic_suspicion.get(state.current_topic, 0.0)
                state.topic_suspicion[state.current_topic] = current + suspicion_delta

        return {
            "filler_count": filler_count,
            "filler_frequency": filler_freq,
            "correction_count": correction_count,
            "word_count": word_count,
            "avg_sentence_length": avg_sentence_length,
            "deviation_score": deviation_score,
            "suspicion_delta": suspicion_delta
        }

    def _calculate_deviation(
        self,
        filler_freq: float,
        word_count: int,
        state: InterviewState
    ) -> float:
        baseline = state.baseline_metrics
        if not baseline:
            return 0.0

        baseline_filler = baseline.get("filler_frequency", 0.1)
        baseline_length = baseline.get("avg_word_count", 50)

        filler_deviation = abs(filler_freq - baseline_filler) / max(baseline_filler, 0.01)
        length_deviation = abs(word_count - baseline_length) / max(baseline_length, 1)

        return min(1.0, (filler_deviation * 0.6 + length_deviation * 0.4))

    def _calculate_suspicion(
        self,
        filler_freq: float,
        word_count: int,
        deviation_score: float,
        state: InterviewState
    ) -> float:
        suspicion = 0.0

        if filler_freq < 0.01 and word_count > 60:
            suspicion += 0.3

        if deviation_score > 0.7:
            suspicion += 0.2

        if word_count > state.baseline_metrics.get("avg_word_count", 50) * 2.5:
            suspicion += 0.2

        return min(1.0, suspicion)

    def _empty_analysis(self) -> dict:
        return {
            "filler_count": 0,
            "filler_frequency": 0.0,
            "correction_count": 0,
            "word_count": 0,
            "avg_sentence_length": 0.0,
            "deviation_score": 0.0,
            "suspicion_delta": 0.0
        }