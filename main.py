import os
import json
from datetime import datetime, timezone
from xmlrpc import client
from openai import OpenAI
from dataclasses import dataclass
from typing import Dict, List, Any
from dotenv import load_dotenv

from criterions import SCHOOL_CRITERIONS

load_dotenv()

class InternshipEvaluator:
    def __init__(self):
        self.client = OpenAI(
                        base_url=os.getenv("OPENROUTER_BASE_URL"),
                        api_key=os.getenv("OPENROUTER_API_KEY"),
                    )
        self.models = [
           "google/gemini-2.5-flash-lite", # Close performance
           "moonshotai/kimi-k2",           # Cheaper
           "deepseek/deepseek-r1:free"     # Free backup
       ]
    
    def _get_stats(self, performance: dict) -> str:
        t_pct = (performance["tasks_done"] / performance["tasks_total"]) * 100
        a_pct = (performance["days_present"] / performance["total_days"]) * 100
        return (f"- Tasks: {performance['tasks_done']}/{performance['tasks_total']} ({t_pct:.1f}%)\n"
                f"- Attendance: {performance['days_present']}/{performance['total_days']} ({a_pct:.1f}%)\n"
                f"- Average Mark: {performance['average_mark']}%")
    
    def _generate_prompt(self, school: str, performance: dict, remarks: dict) -> str:
        stats = self._get_stats(performance)

        if school == "COLTECH":
            criteria_text = "\n".join([f"{cid} (Max {m}): {desc}" for cid, m, desc in SCHOOL_CRITERIONS["COLTECH"]["definitions"]])
            observation_text = "\n".join([f"- {k}: {v}" for k, v in remarks["comments"].items()])
            return f"""You are an expert academic evaluator for COLTECH.
                ## PERFORMANCE DATA
                {stats}
                - Overall Remark: {remarks['overall_remark']}

                ## SUPERVISOR OBSERVATIONS
                {observation_text}

                ## CRITERIA TO GRADE
                {criteria_text}

                ## INSTRUCTIONS
                1. Score each criterion (1 decimal place) based on quantitative data and observations.
                2. Provide a sentence explanation of reasoning for each.
                3. Provide a 2-3 sentence summary of student performance.
                Respond ONLY with JSON:
                {{
                "summary": "...",
                "criteria": {{ "participation": {{"score": 0.0, "reasoning": "..."}}, ... }}
                }}"""
        else:
            sections_text = ""
            for section in SCHOOL_CRITERIONS["NAHPI"]["sections"]:
                sections_text += f"\nSection {section['letter']} ({section['label']}):\n"

                sections_text += "\n".join(
                    [f"  - {item_id}: {desc}" for item_id, desc in section["items"]]
                )

            return f"""You are an expert academic evaluator for NAHPI.
                    ## PERFORMANCE DATA
                    {stats}
                    - Supervisor Remark: {remarks['overall_remark']}

                    ## SCORING SCALE (Integers 1-5)
                    1: Poor | 2: Underdeveloped | 3: Average | 4: Good | 5: Outstanding

                    ## 20 SUB-CRITERIA TO GRADE
                    {sections_text}

                    ## INSTRUCTIONS
                    1. Score all 20 items (1-20) as integers 1-5.
                    2. Provide 1 sentence of reasoning for each item.
                    3. Provide a 2-3 sentence summary.
                    Respond ONLY with JSON:
                    {{
                    "summary": "...",
                    "items": {{ "1": {{"score": 0, "reasoning": "..."}}, ... }}
                    }}"""
                    
    def _call_ai(self, prompt: str) -> Dict:
        response = self.client.chat.completions.create(
            model="deepseek/deepseek-r1:free",
            messages=[{"role": "user", "content": prompt}],
            extra_body={"models": self.models}
        )
        raw = response.choices[0].message.content.removeprefix("```json").removesuffix("```").strip()
        return json.loads(raw)
    
    def generate_report(self, school: str, performance: dict, remarks: dict) -> Dict:
        prompt = self._generate_prompt(school, performance, remarks)
        ai_data = self._call_ai(prompt)

        report = {
            "evaluation": {"summary": ai_data["summary"]}
        }

        total = 0.0
        if school == "COLTECH":
            items = []
            for cid, m, desc in SCHOOL_CRITERIONS["COLTECH"]["definitions"]:
                val = ai_data["criteria"].get(cid, {"score": 0})
                score = round(max(0.0, min(float(m), float(val["score"]))), 1)
                total += score
                items.append({"id": cid, "label": desc.split(":")[0], "score": score, "max": m, "reasoning": val.get("reasoning", "")})
            report["evaluation"]["criteria"] = items
        else:
            sections = []
            for s in SCHOOL_CRITERIONS["NAHPI"]["sections"]:
                sec_items = []
                for iid, desc in s["items"]:
                    val = ai_data["items"].get(iid, {"score": 1})
                    score = max(1, min(5, int(round(float(val["score"])))))
                    sec_items.append({"id": iid, "description": desc, "score": score, "reasoning": val.get("reasoning", "")})
                s_total = sum(i["score"] for i in sec_items)
                total += s_total
                sections.append({"label": s["label"], "score": s_total, "max": 20, "items": sec_items})
            report["evaluation"]["sections"] = sections

        report["evaluation"]["totals"] = {
            "score": total, 
            "max": SCHOOL_CRITERIONS[school]["max_total"],
            "percentage": f"{(total / SCHOOL_CRITERIONS[school]['max_total']) * 100:.1f}%"
        }
        return report

if __name__ == "__main__":
    evaluator = InternshipEvaluator()
    
    # Example for NAHPI
    personal = {"name": "Jean Dupont", "id": "ST001"}
    performance = {"tasks_done": 1, "tasks_total": 5, "days_present": 45, "total_days": 50, "average_mark": 78}
    remarks = {
    "comments": {
        "Participation": "Lacking in Hardwork and proactiveness",
        "Discipline": "Generally punctual",
        "Teamwork": "Works well with others"
    },
    "overall_remark": "No Consistent effort throughout.",
}
    final_report = evaluator.generate_report("NAHPI", performance, remarks)
    print(json.dumps(final_report, indent=2))