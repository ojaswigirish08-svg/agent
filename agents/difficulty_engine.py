from orchestrator.state import InterviewState


class DifficultyEngine:

    def __init__(self, config: dict):
        self.config = config
        self.max_level = config["interview"]["difficulty_levels"]
        self.min_level = 1

    def evaluate(self, state: InterviewState) -> dict:
        current = state.difficulty_level
        changed = False
        reason = "unchanged"

        if state.consecutive_strong >= 3:
            new_level = min(current + 1, self.max_level)
            if new_level != current:
                state.difficulty_level = new_level
                state.consecutive_strong = 0
                changed = True
                reason = "escalated"

        elif state.consecutive_weak >= 3:
            new_level = max(current - 1, self.min_level)
            if new_level != current:
                state.difficulty_level = new_level
                state.consecutive_weak = 0
                changed = True
                reason = "dropped"

        return {
            "new_level": state.difficulty_level,
            "changed": changed,
            "reason": reason,
            "previous_level": current
        }

    def get_difficulty_label(self, level: int) -> str:
        labels = {
            1: "foundational",
            2: "basic",
            3: "intermediate",
            4: "advanced",
            5: "expert"
        }
        return labels.get(level, "intermediate")