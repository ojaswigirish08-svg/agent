from providers.llm.base import BaseLLMProvider
from orchestrator.state import InterviewState


class WarmupAgent:

    def __init__(self, llm: BaseLLMProvider, config: dict):
        self.llm = llm
        self.config = config
        self.warmup_questions_target = config["interview"]["warmup_questions"]

    async def get_opening(self, state: InterviewState) -> str:
        domain_label = state.domain.replace("_", " ").title()
        level_label = state.experience_level.replace("_", " ").title()

        return (
            f"Hello, and welcome to your mock interview. "
            f"I'm your AI interviewer today. "
            f"This session is tailored for {domain_label} at the {level_label} level "
            f"and will take approximately {state.duration_minutes} minutes. "
            f"Before we begin the actual interview, let's have a quick conversation "
            f"to get you comfortable. Tell me � what have you been working on "
            f"recently, or what brought you to VLSI?"
        )

    async def respond(
        self,
        candidate_text: str,
        state: InterviewState
    ) -> dict:

        self._update_baseline(candidate_text, state)
        state.warmup_turns += 1

        is_complete = state.warmup_turns >= self.warmup_questions_target

        if is_complete:
            response_text = (
                "That's great, thank you for sharing that. "
                "I have a good sense of your background now. "
                "Let's begin the actual interview. "
                "I'll ask you a series of technical questions � "
                "take your time with each answer, and feel free to "
                "think out loud. Ready? Let's start."
            )
            state.warmup_complete = True
            state.phase = "interview"
        else:
            system_prompt = self._build_warmup_prompt(state)
            messages = state.conversation_history.copy()
            messages.append({"role": "user", "content": candidate_text})
            response_text = await self.llm.generate(messages, system_prompt)
            response_text = response_text.strip()

        return {
            "response": response_text,
            "warmup_complete": is_complete
        }

    def _update_baseline(self, text: str, state: InterviewState):
        if not text:
            return

        words = text.split()
        word_count = len(words)

        fillers = ["um", "uh", "like", "basically", "you know", "so", "actually"]
        filler_count = sum(1 for w in words if w.lower().strip(".,") in fillers)
        filler_freq = filler_count / max(word_count, 1)

        if not state.baseline_metrics:
            state.baseline_metrics = {
                "avg_word_count": word_count,
                "filler_frequency": filler_freq,
                "sample_count": 1
            }
        else:
            n = state.baseline_metrics["sample_count"]
            state.baseline_metrics["avg_word_count"] = (
                (state.baseline_metrics["avg_word_count"] * n + word_count) / (n + 1)
            )
            state.baseline_metrics["filler_frequency"] = (
                (state.baseline_metrics["filler_frequency"] * n + filler_freq) / (n + 1)
            )
            state.baseline_metrics["sample_count"] = n + 1

    def _build_warmup_prompt(self, state: InterviewState) -> str:
        return f"""You are a warm and professional VLSI interviewer conducting a brief warmup conversation.

Your goal is to make the candidate comfortable before the real interview begins.
Ask ONE casual follow-up question about their background or experience.
Keep it conversational, friendly, and brief.
Do NOT ask technical questions yet.
Do NOT evaluate anything they say.

Candidate domain: {state.domain.replace("_", " ")}
Candidate level: {state.experience_level.replace("_", " ")}
Warmup turn: {state.warmup_turns} of {self.warmup_questions_target}"""