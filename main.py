import os
import json
import logging
import textwrap
import time
from typing import Dict

from openai import OpenAI, APIConnectionError, APIStatusError, APITimeoutError
from dotenv import load_dotenv

from criterions import SCHOOL_CRITERIONS

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

class AIResponseError(Exception):
    """Raised when all models are exhausted or return unusable responses."""

class InternshipEvaluator:
    def __init__(self):
        self.client = OpenAI(
            base_url=os.getenv("OPENROUTER_BASE_URL"),
            api_key=os.getenv("OPENROUTER_API_KEY"),
        )
        # Models tried in order — first success wins
        self.models = [
            "google/gemini-2.5-flash-lite",  # Primary
            "moonshotai/kimi-k2",            # Fallback
            "deepseek/deepseek-r1:free",     # Last resort
        ]
        self.max_retries = 2      # retries per model (for transient errors)
        self.retry_delay = 2      # seconds to wait between retries

    def _get_stats(self, performance: dict) -> str:
        t_pct = (performance["tasks_done"] / performance["tasks_total"]) * 100
        a_pct = (performance["days_present"] / performance["total_days"]) * 100
        return (
            f"- Tasks: {performance['tasks_done']}/{performance['tasks_total']} ({t_pct:.1f}%)\n"
            f"- Attendance: {performance['days_present']}/{performance['total_days']} ({a_pct:.1f}%)\n"
            f"- Average Mark: {performance['average_mark']}%"
        )

    def _generate_prompt(self, school: str, performance: dict, remarks: dict) -> str:
        stats = self._get_stats(performance)

        if school == "COLTECH":
            criteria_text = "\n".join(
                f"{cid} (Max {m}): {desc}"
                for cid, m, desc in SCHOOL_CRITERIONS["COLTECH"]["definitions"]
            )
            observation_text = "\n".join(
                f"- {k}: {v}" for k, v in remarks["comments"].items()
            )
            return textwrap.dedent(f"""
                You are an expert academic evaluator for COLTECH.

                ## PERFORMANCE DATA
                {stats}
                - Overall Remark: {remarks['overall_remark']}

                ## SUPERVISOR OBSERVATIONS
                {observation_text}

                ## CRITERIA TO GRADE
                {criteria_text}

                ## INSTRUCTIONS
                1. Score each criterion (1 decimal place) based on quantitative data and observations.
                2. Provide a sentence of reasoning for each.
                3. Provide a 2-3 sentence summary of student performance.
                Respond ONLY with JSON:
                {{
                  "summary": "...",
                  "criteria": {{ "participation": {{"score": 0.0, "reasoning": "..."}}, ... }}
                }}
            """).strip()

        else:
            sections_text = ""
            for section in SCHOOL_CRITERIONS["NAHPI"]["sections"]:
                sections_text += f"\nSection {section['letter']} ({section['label']}):\n"
                sections_text += "\n".join(
                    f"  - {item_id}: {desc}" for item_id, desc in section["items"]
                )
            return textwrap.dedent(f"""
                You are an expert academic evaluator for NAHPI.

                ## PERFORMANCE DATA
                {stats}
                - Supervisor Remark: {remarks['supervisor_remark']}

                ## SCORING SCALE (Integers 1-5)
                1: Poor | 2: Underdeveloped | 3: Average | 4: Good | 5: Outstanding

                ## 20 SUB-CRITERIA TO GRADE
                {sections_text}

                ## INSTRUCTIONS
                1. Score all 20 items (A1-E20) as integers 1-5.
                2. Provide 1 sentence of reasoning for each item.
                3. Provide a 2-3 sentence summary.
                Respond ONLY with JSON:
                {{
                  "summary": "...",
                  "items": {{ "A1": {{"score": 0, "reasoning": "..."}}, ... }}
                }}
            """).strip()

    def _try_model(self, model: str, prompt: str) -> Dict:
        """
        Call one model with retries for transient errors.
        Raises the last exception if all retries fail.
        """
        last_exc = None

        for attempt in range(1, self.max_retries + 1):
            try:
                log.info("Model: %s | Attempt %d/%d", model, attempt, self.max_retries)
                response = self.client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    timeout=60,
                )
                raw = (
                    response.choices[0].message.content
                    .removeprefix("```json")
                    .removesuffix("```")
                    .strip()
                )
                return json.loads(raw)  # success — return immediately

            except APITimeoutError as e:
                last_exc = e
                log.warning("Timeout on attempt %d — %s", attempt, e)

            except APIConnectionError as e:
                last_exc = e
                log.warning("Connection error on attempt %d — %s", attempt, e)

            except APIStatusError as e:
                last_exc = e
                # 429 rate-limit and 5xx are transient; 4xx (except 429) are not
                if e.status_code == 429 or e.status_code >= 500:
                    log.warning("Status %s on attempt %d — %s", e.status_code, attempt, e.message)
                else:
                    # 4xx client errors won't improve with a retry — fail immediately
                    log.error("Non-retryable status %s from %s: %s", e.status_code, model, e.message)
                    raise

            except json.JSONDecodeError as e:
                # Bad JSON from the model — retrying usually won't help
                log.error("Invalid JSON from %s: %s", model, e)
                raise

            # Wait before retrying (skip wait on last attempt)
            if attempt < self.max_retries:
                log.info("Retrying in %ds...", self.retry_delay)
                time.sleep(self.retry_delay)

        raise last_exc  # all retries exhausted

    def _call_ai(self, prompt: str) -> Dict:
        """
        Try each model in order. Move to the next model on any failure.
        Raises AIResponseError only when every model has been exhausted.
        """
        errors = {}

        for model in self.models:
            try:
                return self._try_model(model, prompt)
            except Exception as e:
                errors[model] = f"{type(e).__name__}: {e}"
                log.warning("Model %s failed — trying next. (%s)", model, errors[model])

        # All models failed — compile a clear summary
        error_summary = "\n".join(f"  {m}: {err}" for m, err in errors.items())
        raise AIResponseError(
            f"All models failed to produce a response:\n{error_summary}"
        )

    def generate_report(self, school: str, personal: dict, performance: dict, remarks: dict) -> Dict:
        prompt   = self._generate_prompt(school, performance, remarks)
        ai_data  = self._call_ai(prompt)   # raises AIResponseError if everything fails

        report = {"intern": personal, "evaluation": {"summary": ai_data["summary"]}}
        total  = 0.0

        if school == "COLTECH":
            items = []
            for cid, m, desc in SCHOOL_CRITERIONS["COLTECH"]["definitions"]:
                val   = ai_data["criteria"].get(cid, {"score": 0})
                score = round(max(0.0, min(float(m), float(val["score"]))), 1)
                total += score
                items.append({"id": cid, "label": desc.split(":")[0], "score": score,
                               "max": m, "reasoning": val.get("reasoning", "")})
            report["evaluation"]["criteria"] = items
        else:
            sections = []
            for s in SCHOOL_CRITERIONS["NAHPI"]["sections"]:
                sec_items = []
                for iid, desc in s["items"]:
                    val   = ai_data["items"].get(iid, {"score": 1})
                    score = max(1, min(5, int(round(float(val["score"])))))
                    sec_items.append({"id": iid, "description": desc, "score": score,
                                      "reasoning": val.get("reasoning", "")})
                s_total = sum(i["score"] for i in sec_items)
                total  += s_total
                sections.append({"label": s["label"], "score": s_total, "max": 20, "items": sec_items})
            report["evaluation"]["sections"] = sections

        report["evaluation"]["totals"] = {
            "score": total,
            "max": SCHOOL_CRITERIONS[school]["max_total"],
            "percentage": f"{(total / SCHOOL_CRITERIONS[school]['max_total']) * 100:.1f}%",
        }
        return report


if __name__ == "__main__":
    evaluator = InternshipEvaluator()

    personal    = {"name": "Jean Dupont", "id": "ST001"}
    performance = {"tasks_done": 1, "tasks_total": 5, "days_present": 45, "total_days": 50, "average_mark": 78}
    remarks     = {
        "comments": {
            "participation":    "Lacking in hardwork and proactiveness.",
            "discipline":       "Generally punctual.",
            "integration":      "Works independently but rarely shows initiative.",
            "general_behavior": "Professional conduct maintained.",
        },
        "overall_remark": "No consistent effort throughout.",
    }

    try:
        report = evaluator.generate_report("COLTECH", personal, performance, remarks)
        print(json.dumps(report, indent=2))
    except AIResponseError as e:
        log.error("Evaluation failed — %s", e)