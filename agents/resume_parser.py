import json
from providers.llm.base import BaseLLMProvider


class ResumeParser:

    def __init__(self, llm: BaseLLMProvider):
        self.llm = llm

    async def parse(self, resume_text: str) -> dict:
        system_prompt = """You are an expert VLSI hiring specialist.
Analyze the resume and extract the candidate profile.

Return ONLY valid JSON with this exact structure:
{
    "domain": "analog_layout" or "physical_design" or "design_verification",
    "experience_level": "fresh_graduate" or "trained_fresher" or "experienced_junior" or "experienced_senior",
    "years_experience": number,
    "tech_stack": ["tool1", "tool2"],
    "resume_summary": "2-3 sentence summary of candidate background"
}

Domain definitions:
- analog_layout: works on transistor level layout, custom layout, analog circuits
- physical_design: works on floorplanning, placement, routing, timing closure
- design_verification: works on testbenches, UVM, assertions, coverage

Experience level definitions:
- fresh_graduate: 0 years, just completed degree
- trained_fresher: 0-1 years, has training or internship
- experienced_junior: 1-3 years industry experience
- experienced_senior: 3+ years industry experience

If domain is unclear default to physical_design.
If experience is unclear default to trained_fresher."""

        messages = [
            {
                "role": "user",
                "content": f"Parse this VLSI resume:\n\n{resume_text}"
            }
        ]

        try:
            result = await self.llm.generate_json(messages, system_prompt)
            return self._validate(result)
        except Exception as e:
            return self._default_profile()

    def _validate(self, result: dict) -> dict:
        valid_domains = ["analog_layout", "physical_design", "design_verification"]
        valid_levels = ["fresh_graduate", "trained_fresher", "experienced_junior", "experienced_senior"]

        if result.get("domain") not in valid_domains:
            result["domain"] = "physical_design"
        if result.get("experience_level") not in valid_levels:
            result["experience_level"] = "trained_fresher"
        if not isinstance(result.get("years_experience"), (int, float)):
            result["years_experience"] = 0
        if not isinstance(result.get("tech_stack"), list):
            result["tech_stack"] = []
        if not result.get("resume_summary"):
            result["resume_summary"] = "VLSI candidate profile"

        return result

    def _default_profile(self) -> dict:
        return {
            "domain": "physical_design",
            "experience_level": "trained_fresher",
            "years_experience": 0,
            "tech_stack": [],
            "resume_summary": "VLSI candidate"
        }