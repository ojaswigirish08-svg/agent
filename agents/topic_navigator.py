import random
from orchestrator.state import InterviewState


DOMAIN_PILLARS = {
    "analog_layout": [
        "basic_layout_concepts", "matching_techniques", "parasitic_awareness",
        "latch_up_esd", "guard_rings", "drc_lvs_basics",
        "symmetry_best_practices", "device_understanding",
        "shielding_routing", "technology_awareness"
    ],
    "physical_design": [
        "floorplanning", "power_planning", "placement",
        "clock_tree_synthesis", "routing", "timing_closure",
        "drc_lvs_signoff", "static_timing_analysis", "tool_knowledge"
    ],
    "design_verification": [
        "verification_methodologies", "testbench_architecture",
        "functional_coverage", "assertions_sva", "simulation_vs_formal",
        "debugging_skills", "protocol_knowledge", "regression_signoff"
    ]
}

CONTRADICTION_PAIRS = {
    "physical_design": [
        ("floorplanning", "power_planning"),
        ("clock_tree_synthesis", "timing_closure"),
        ("placement", "routing"),
    ],
    "analog_layout": [
        ("matching_techniques", "symmetry_best_practices"),
        ("latch_up_esd", "guard_rings"),
        ("parasitic_awareness", "shielding_routing"),
    ],
    "design_verification": [
        ("functional_coverage", "assertions_sva"),
        ("verification_methodologies", "testbench_architecture"),
        ("simulation_vs_formal", "debugging_skills"),
    ]
}

PERSONAL_ANCHOR_QUESTIONS = {
    "physical_design": [
        "Tell me about a specific timing violation you personally encountered and how you resolved it.",
        "Describe a time your floorplan had to be completely redone � what caused it?",
        "What was the most challenging DRC issue you personally dealt with?",
        "Tell me about a last-minute ECO you had to handle before tapeout.",
    ],
    "analog_layout": [
        "Tell me about a matching issue you personally encountered in a layout.",
        "Describe a latch-up problem you dealt with � how was it caught?",
        "What was the most difficult parasitic extraction result you had to handle?",
        "Tell me about a DRC violation you introduced � how was it found?",
    ],
    "design_verification": [
        "Tell me about a bug you personally found through functional coverage.",
        "Describe a simulation vs formal verification conflict you encountered.",
        "What was the most complex assertion you personally wrote?",
        "Tell me about a regression failure that took the longest to debug.",
    ]
}


class TopicNavigator:

    def __init__(self, config: dict):
        self.config = config

    def get_next_instruction(self, state: InterviewState) -> dict:
        pillars = DOMAIN_PILLARS.get(state.domain, [])
        uncovered = [p for p in pillars if p not in state.covered_topics]

        # Check contradiction trap
        contradiction = self._check_contradiction(state)
        if contradiction:
            return {
                "topic": contradiction["topic"],
                "question_type": "contradiction",
                "contradiction_target": contradiction["target"],
                "anchor_question": None,
                "numerical_probe": False
            }

        # Check personal anchor injection
        if self._should_inject_anchor(state):
            anchor = self._get_anchor_question(state)
            return {
                "topic": state.current_topic,
                "question_type": "personal_anchor",
                "contradiction_target": None,
                "anchor_question": anchor,
                "numerical_probe": False
            }

        # Check numerical probe
        if self._should_probe_numerical(state):
            return {
                "topic": state.current_topic,
                "question_type": "numerical_probe",
                "contradiction_target": None,
                "anchor_question": None,
                "numerical_probe": True
            }

        # Pick next topic
        if uncovered:
            next_topic = uncovered[0]
        elif pillars:
            next_topic = random.choice(pillars)
        else:
            next_topic = state.current_topic

        # Register contradiction pair if applicable
        self._register_contradiction_pair(next_topic, state)

        return {
            "topic": next_topic,
            "question_type": "definition",
            "contradiction_target": None,
            "anchor_question": None,
            "numerical_probe": False
        }

    def mark_topic_covered(self, topic: str, state: InterviewState):
        if topic and topic not in state.covered_topics:
            state.covered_topics.append(topic)

    def _check_contradiction(self, state: InterviewState) -> dict:
        if state.turn_number < 8:
            return None
        pairs = CONTRADICTION_PAIRS.get(state.domain, [])
        for topic_a, topic_b in pairs:
            key = f"{topic_a}_{topic_b}"
            pair_data = state.contradiction_pairs.get(key, {})
            if (pair_data.get("first_asked") and
                    not pair_data.get("second_asked") and
                    state.turn_number - pair_data["first_turn"] >= 6):
                state.contradiction_pairs[key]["second_asked"] = True
                return {"topic": topic_b, "target": topic_a}
        return None

    def _register_contradiction_pair(self, topic: str, state: InterviewState):
        pairs = CONTRADICTION_PAIRS.get(state.domain, [])
        for topic_a, topic_b in pairs:
            if topic == topic_a:
                key = f"{topic_a}_{topic_b}"
                if key not in state.contradiction_pairs:
                    state.contradiction_pairs[key] = {
                        "first_asked": True,
                        "first_turn": state.turn_number,
                        "second_asked": False
                    }

    def _should_inject_anchor(self, state: InterviewState) -> bool:
        if state.anchors_injected >= 3:
            return False
        if state.turn_number - state.last_anchor_turn < 4:
            return False
        if state.turn_number < 3:
            return False
        return state.turn_number % 4 == 0

    def _get_anchor_question(self, state: InterviewState) -> str:
        questions = PERSONAL_ANCHOR_QUESTIONS.get(state.domain, [])
        if not questions:
            return "Tell me about a specific challenge you personally faced in your work."
        used = state.anchors_injected % len(questions)
        state.anchors_injected += 1
        state.last_anchor_turn = state.turn_number
        return questions[used]

    def _should_probe_numerical(self, state: InterviewState) -> bool:
        if state.numerical_probes_done >= 3:
            return False
        if state.turn_number < 4:
            return False
        return state.turn_number % 5 == 0