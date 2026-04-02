from providers.llm.base import BaseLLMProvider
from orchestrator.state import InterviewState
from agents.difficulty_engine import DifficultyEngine


class InterviewConductor:

    def __init__(self, llm: BaseLLMProvider, config: dict):
        self.llm = llm
        self.config = config
        self.difficulty_engine = DifficultyEngine(config)

    async def respond(
        self,
        candidate_text: str,
        topic_instruction: dict,
        state: InterviewState,
        evaluation: dict = None
    ) -> dict:

        system_prompt = self._build_system_prompt(state, topic_instruction, evaluation)
        messages = self._build_messages(state, candidate_text)
        response_text = await self.llm.generate(messages, system_prompt)
        response_text = self._clean_response(response_text)
        interview_ended = self._check_interview_end(state, response_text)

        return {
            "response": response_text,
            "interview_ended": interview_ended
        }

    def _build_system_prompt(
        self,
        state: InterviewState,
        topic_instruction: dict,
        evaluation: dict = None
    ) -> str:

        difficulty_label = self.difficulty_engine.get_difficulty_label(
            state.difficulty_level
        )
        domain_label = state.domain.replace("_", " ")
        level_label = state.experience_level.replace("_", " ")

        questions_left = state.target_questions - state.questions_asked
        is_last_question = questions_left <= 1

        prompt = f"""You are a professional VLSI interviewer conducting a mock interview.

CANDIDATE PROFILE:
- Domain: {domain_label}
- Experience level: {level_label}
- Tech stack: {", ".join(state.tech_stack) if state.tech_stack else "not specified"}

INTERVIEW STATE:
- Current difficulty: {difficulty_label} (level {state.difficulty_level}/5)
- Questions asked: {state.questions_asked} of {state.target_questions}
- Current topic: {state.current_topic or "opening"}
- Question type: {topic_instruction.get("question_type", "definition")}

WHAT TO DO THIS TURN:
"""
        question_type = topic_instruction.get("question_type", "definition")

        if question_type == "personal_anchor":
            anchor = topic_instruction.get("anchor_question", "")
            prompt += f"""Ask this personal experience question naturally:
"{anchor}"
Do not change the question. Ask it conversationally."""

        elif question_type == "contradiction":
            target = topic_instruction.get("contradiction_target", "")
            prompt += f"""Ask about {topic_instruction["topic"]} in a way that revisits 
the concept of {target} from a different angle.
Do not reference the previous question."""

        elif question_type == "numerical_probe":
            prompt += f"""Ask the candidate for approximate real numbers from their 
personal experience related to {state.current_topic}.
Example: "Roughly what numbers have you worked with for this in your experience?"
Do not accept "it depends" � push for approximate values."""

        elif question_type == "scenario":
            prompt += f"""Ask a practical scenario question about {topic_instruction["topic"]}.
The candidate just gave a definition answer � now test if they can apply it.
Start with "Now if you encountered this in your actual design..." """

        else:
            prompt += f"""Ask a {difficulty_label} level question about {topic_instruction["topic"]}.
Start with a definition or concept question if not yet covered."""

        if evaluation:
            accuracy = evaluation.get("technical_accuracy", 0.5)
            hint_suggested = evaluation.get("hint_suggested", False)
            follow_up = evaluation.get("follow_up_needed", False)

            if hint_suggested and accuracy < 0.4:
                prompt += f"""

The candidate is struggling. Give a small hint before asking the next question.
Acknowledge their attempt warmly then provide a gentle nudge."""

            elif follow_up and accuracy < 0.7:
                prompt += f"""

The candidate gave a partial answer. Ask one follow-up to probe deeper before moving on."""

            elif accuracy >= 0.8:
                prompt += f"""

The candidate answered well. Acknowledge briefly then move to next topic."""

        if is_last_question:
            prompt += f"""

This is the LAST question. After the candidate answers, close the interview warmly.
Say something like "That brings us to the end of our session today. 
Thank you for your time � your detailed report will be ready shortly." """

        prompt += """

RULES:
- Ask ONE question only per turn
- Keep responses under 4 sentences before the question
- Be conversational and natural � not robotic
- Never mention scores, evaluation, or cheating detection
- Never repeat a question already asked
- If candidate says I don't know � acknowledge honestly and either give hint or move on"""

        return prompt

    def _build_messages(
        self,
        state: InterviewState,
        candidate_text: str
    ) -> list:
        messages = state.conversation_history.copy()
        if candidate_text:
            messages.append({
                "role": "user",
                "content": candidate_text
            })
        return messages

    def _clean_response(self, response: str) -> str:
        response = response.strip()
        for tag in ["<response>", "</response>", "<evaluation>", "</evaluation>"]:
            response = response.replace(tag, "")
        return response.strip()

    def _check_interview_end(
        self,
        state: InterviewState,
        response_text: str
    ) -> bool:
        if state.questions_asked >= state.target_questions:
            return True

        closing_phrases = [
            "brings us to the end",
            "that concludes",
            "thank you for your time",
            "your report will be ready",
            "end of our session",
            "interview is complete"
        ]
        response_lower = response_text.lower()
        return any(phrase in response_lower for phrase in closing_phrases)