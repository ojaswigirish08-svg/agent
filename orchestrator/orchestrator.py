import asyncio
from providers.llm.base import BaseLLMProvider
from providers.stt.base import BaseSTTProvider
from providers.tts.base import BaseTTSProvider
from orchestrator.state import InterviewState
from orchestrator.session_manager import SessionManager
from agents.resume_parser import ResumeParser
from agents.warmup_agent import WarmupAgent
from agents.interview_conductor import InterviewConductor
from agents.evaluator_agent import EvaluatorAgent
from agents.topic_navigator import TopicNavigator
from agents.difficulty_engine import DifficultyEngine
from agents.behavior_monitor import BehaviorMonitor
from agents.anti_cheat_agent import AntiCheatAgent
from agents.report_builder import ReportBuilder


class Orchestrator:

    def __init__(
        self,
        llm: BaseLLMProvider,
        stt: BaseSTTProvider,
        tts: BaseTTSProvider,
        config: dict
    ):
        self.llm = llm
        self.stt = stt
        self.tts = tts
        self.config = config

        self.session_manager = SessionManager(config)
        self.resume_parser = ResumeParser(llm)
        self.warmup_agent = WarmupAgent(llm, config)
        self.conductor = InterviewConductor(llm, config)
        self.evaluator = EvaluatorAgent(llm)
        self.topic_navigator = TopicNavigator(config)
        self.difficulty_engine = DifficultyEngine(config)
        self.behavior_monitor = BehaviorMonitor()
        self.anti_cheat = AntiCheatAgent(config)
        self.report_builder = ReportBuilder(llm, config)

    async def create_session(
        self,
        resume_text: str,
        candidate_id: str,
        mode: str = "mock"
    ) -> InterviewState:
        profile = await self.resume_parser.parse(resume_text)
        state = self.session_manager.create_session(
            candidate_id=candidate_id,
            domain=profile["domain"],
            experience_level=profile["experience_level"],
            years_experience=profile["years_experience"],
            tech_stack=profile["tech_stack"],
            resume_summary=profile["resume_summary"],
            mode=mode
        )
        return state

    async def get_opening(self, state: InterviewState) -> tuple:
        opening_text = await self.warmup_agent.get_opening(state)
        state.conversation_history.append({
            "role": "assistant",
            "content": opening_text
        })
        audio = await self.tts.synthesize(opening_text)
        return opening_text, audio

    async def process_turn(
        self,
        candidate_text: str,
        state: InterviewState
    ) -> dict:

        state.turn_number += 1

        if state.phase == "warmup":
            return await self._handle_warmup_turn(candidate_text, state)
        else:
            return await self._handle_interview_turn(candidate_text, state)

    async def _handle_warmup_turn(
        self,
        candidate_text: str,
        state: InterviewState
    ) -> dict:
        state.conversation_history.append({
            "role": "user",
            "content": candidate_text
        })

        result = await self.warmup_agent.respond(candidate_text, state)
        response_text = result["response"]

        state.conversation_history.append({
            "role": "assistant",
            "content": response_text
        })

        audio = await self.tts.synthesize(response_text)

        return {
            "response_text": response_text,
            "audio": audio,
            "interview_ended": False,
            "phase": state.phase
        }

    async def _handle_interview_turn(
        self,
        candidate_text: str,
        state: InterviewState
    ) -> dict:

        last_question = state.conversation_history[-1]["content"] if state.conversation_history else ""

        eval_task = self.evaluator.evaluate(candidate_text, last_question, state)
        behavior_result = self.behavior_monitor.analyze(candidate_text, state)
        evaluation = await eval_task

        self.difficulty_engine.evaluate(state)
        topic_instruction = self.topic_navigator.get_next_instruction(state)

        state.current_topic = topic_instruction["topic"]
        state.current_question_type = topic_instruction["question_type"]

        if topic_instruction["question_type"] not in ["personal_anchor", "contradiction", "numerical_probe"]:
            self.topic_navigator.mark_topic_covered(topic_instruction["topic"], state)

        state.conversation_history.append({
            "role": "user",
            "content": candidate_text
        })

        conductor_result = await self.conductor.respond(
            candidate_text=candidate_text,
            topic_instruction=topic_instruction,
            state=state,
            evaluation={
                "technical_accuracy": evaluation.technical_accuracy,
                "hint_suggested": evaluation.hint_given,
                "follow_up_needed": evaluation.technical_accuracy < 0.6
            }
        )

        response_text = conductor_result["response"]
        interview_ended = conductor_result["interview_ended"]

        state.conversation_history.append({
            "role": "assistant",
            "content": response_text
        })

        state.questions_asked += 1

        audio = await self.tts.synthesize(response_text)

        reports = None
        if interview_ended:
            state.interview_ended = True
            reports = await self.report_builder.build(state)
            state.evaluation_complete = True

        return {
            "response_text": response_text,
            "audio": audio,
            "interview_ended": interview_ended,
            "phase": state.phase,
            "reports": reports,
            "evaluation": {
                "quadrant": evaluation.quadrant,
                "technical_accuracy": evaluation.technical_accuracy
            }
        }

    def process_anticheat_signal(
        self,
        signal_type: str,
        signal_data: dict,
        state: InterviewState
    ) -> dict:
        return self.anti_cheat.process_signal(signal_type, signal_data, state)

    def get_session(self, session_id: str) -> InterviewState:
        return self.session_manager.get_session(session_id)