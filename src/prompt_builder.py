import json
import textwrap

from src.criterions import SCHOOL_CRITERIONS

class PromptBuilder:
    """Builds school-specific evaluation prompts with few-shot examples."""

    _COLTECH_EXAMPLE = json.dumps({
        "summary": "The intern performed well overall, completing all tasks with high quality and maintaining excellent attendance.",
        "criteria": {
            "participation":    {"score": 10.5, "reasoning": "Completed all 5 tasks with an 85% average mark, showing consistent effort."},
            "discipline":       {"score": 5.5,  "reasoning": "Present 48/50 days; supervisor noted strong punctuality."},
            "integration":      {"score": 6.0,  "reasoning": "Demonstrated independent thinking and creative problem-solving per supervisor."},
            "general_behavior": {"score": 4.5,  "reasoning": "Supervisor highlighted excellent rapport with staff at all levels."},
        }
    }, indent=2)

    _NAHPI_EXAMPLE = json.dumps({
        "summary": "A capable intern who delivered quality work and communicated well, with room to grow in initiative.",
        "items": {
            "1": {"score": 4, "reasoning": "Completed 4/5 tasks competently with an average mark of 78%."},
            "2": {"score": 3, "reasoning": "Standards were mostly respected with minor deviations noted."},
            "3": {"score": 4, "reasoning": "Deadlines were met consistently throughout the internship."},
            "4": {"score": 4, "reasoning": "Organised and engaged throughout all assigned work."},
            "5": {"score": 4, "reasoning": "Demonstrated solid technical skills relevant to assigned tasks."},
            "6": {"score": 3, "reasoning": "Used tools adequately but required occasional guidance."},
            "7": {"score": 4, "reasoning": "Proficient with required computer technology."},
            "8": {"score": 4, "reasoning": "Respected safety and operating procedures throughout."},
            "9": {"score": 4, "reasoning": "Communicated clearly in written and verbal interactions."},
            "10": {"score": 4, "reasoning": "Listened attentively and acted on feedback promptly."},
            "11": {"score": 4, "reasoning": "Collaborated effectively within the team."},
            "12": {"score": 5, "reasoning": "Consistently showed respect and professionalism to all colleagues."},
            "13": {"score": 4, "reasoning": "Attended all required sessions and showed dedication."},
            "14": {"score": 3, "reasoning": "Showed motivation but rarely took initiative without prompting."},
            "15": {"score": 3, "reasoning": "Analytical thinking was adequate for the tasks assigned."},
            "16": {"score": 3, "reasoning": "Solutions were functional but rarely went beyond the obvious."},
            "17": {"score": 4, "reasoning": "Adapted quickly to process changes during the internship."},
            "18": {"score": 4, "reasoning": "Actively sought to learn new tools and techniques."},
            "19": {"score": 5, "reasoning": "Received and acted on feedback constructively every time."},
            "20": {"score": 3, "reasoning": "Showed interest in growth but did not actively pursue extra opportunities."},
        }
    }, indent=2)

    def build(self, school: str, performance: dict, remarks: dict) -> str:
        stats = self._stats(performance)
        if school == "COLTECH":
            return self._coltech(stats, remarks)
        return self._nahpi(stats, remarks)

    @staticmethod
    def _stats(p: dict) -> str:
        t_pct = p["tasks_done"] / p["tasks_total"] * 100
        a_pct = p["days_present"] / p["total_days"] * 100
        return (
            f"- Tasks     : {p['tasks_done']}/{p['tasks_total']} ({t_pct:.1f}%)\n"
            f"- Attendance: {p['days_present']}/{p['total_days']} ({a_pct:.1f}%)\n"
            f"- Avg Mark  : {p['average_mark']}%"
        )

    def _coltech(self, stats: str, remarks: dict) -> str:
        criteria_text = "\n".join(
            f"  {cid} (max {m}): {desc}"
            for cid, m, desc in SCHOOL_CRITERIONS["COLTECH"]["definitions"]
        )
        observations = "\n".join(
            f"  - {k}: {v}" for k, v in remarks["comments"].items()
        )
        return textwrap.dedent(f"""
            You are an expert academic evaluator for the COLTECH internship programme.

            ## PERFORMANCE DATA
            {stats}
            - Overall Remark: {remarks['supervisor_remark']}

            ## SUPERVISOR OBSERVATIONS (one per criterion)
            {observations}

            ## CRITERIA
            {criteria_text}

            ## EXAMPLE OUTPUT (follow this structure exactly)
            {self._COLTECH_EXAMPLE}

            ## INSTRUCTIONS
            - Score each criterion from 0 to its max (1 decimal place).
            - Cross-reference all observations holistically — one comment may inform another criterion.
            - Write 1–2 sentences of reasoning per criterion.
            - Write a 2–3 sentence summary.
            - Respond ONLY with a JSON object matching the example structure above.
        """).strip()

    def _nahpi(self, stats: str, remarks: dict) -> str:
        sections_text = ""
        for section in SCHOOL_CRITERIONS["NAHPI"]["sections"]:
            sections_text += f"\nSection {section['letter']} — {section['label']}:\n"
            sections_text += "\n".join(
                f"  {iid}: {desc}" for iid, desc in section["items"]
            )
        return textwrap.dedent(f"""
            You are an expert academic evaluator for the NAHPI internship programme.

            ## PERFORMANCE DATA
            {stats}
            - Supervisor Remark: {remarks['supervisor_remark']}

            ## SCORING SCALE (integers only)
            1=Poor | 2=Underdeveloped | 3=Average | 4=Good | 5=Outstanding

            ## SUB-CRITERIA (A1–E20)
            {sections_text}

            ## EXAMPLE OUTPUT (follow this structure exactly)
            {self._NAHPI_EXAMPLE}

            ## INSTRUCTIONS
            - Score every item A1–E20 as an integer 1–5.
            - Use the supervisor remark for tone and specifics; use tasks/attendance/mark as anchors.
            - Write 1 sentence of reasoning per item.
            - Write a 4–5 sentence summary.
            - Respond ONLY with a JSON object matching the example structure above.
        """).strip()
