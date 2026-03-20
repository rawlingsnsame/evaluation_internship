import os
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List

from openai import OpenAI, APIConnectionError, APIStatusError, APITimeoutError
from dotenv import load_dotenv

from src.validators import ValidationError, AIResponseError, InputValidator, ResponseValidator
from src.prompt_builder import PromptBuilder
from src.assembler import ReportAssembler

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

@dataclass
class EvaluatorConfig:
    models: List[str] = field(default_factory=lambda: [
        "google/gemini-2.5-flash-lite",   # Primary
        "meta-llama/llama-4-scout",  # Free fallback
        "mistralai/mistral-nemo",
    ])
    max_retries: int = 2
    retry_delay: int = 2
    timeout: int = 60

class AIClient:
    """Handles API calls with retries per model"""

    def __init__(self, config: EvaluatorConfig):
        self.config = config
        self.client = OpenAI(
            base_url=os.getenv("OPENROUTER_BASE_URL"),
            api_key=os.getenv("OPENROUTER_API_KEY"),
        )

    def call(self, prompt: str) -> Dict:
        errors = {}
        for model in self.config.models:
            try:
                return self._try_model(model, prompt)
            except Exception as e:
                errors[model] = f"{type(e).__name__}: {e}"
                log.warning("Model %s failed — trying next. (%s)", model, errors[model])

        summary = "\n".join(f"  {m}: {err}" for m, err in errors.items())
        raise AIResponseError(f"All models failed:\n{summary}")

    def _try_model(self, model: str, prompt: str) -> Dict:
        last_exc = None
        for attempt in range(1, self.config.max_retries + 1):
            try:
                log.info("Model: %s | Attempt %d/%d", model, attempt, self.config.max_retries)
                response = self.client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"},
                    timeout=self.config.timeout,
                )
                return json.loads(response.choices[0].message.content)

            except APITimeoutError as e:
                last_exc = e
                log.warning("Timeout on attempt %d — %s", attempt, e)

            except APIConnectionError as e:
                last_exc = e
                log.warning("Connection error on attempt %d — %s", attempt, e)

            except APIStatusError as e:
                last_exc = e
                if e.status_code == 429 or e.status_code >= 500:
                    log.warning("Status %s on attempt %d — %s", e.status_code, attempt, e.message)
                else:
                    log.error("Non-retryable %s from %s: %s", e.status_code, model, e.message)
                    raise

            except json.JSONDecodeError as e:
                log.error("Invalid JSON from %s: %s", model, e)
                raise

            if attempt < self.config.max_retries:
                log.info("Retrying in %ds...", self.config.retry_delay)
                time.sleep(self.config.retry_delay)

        raise last_exc


class InternshipEvaluator:
    def __init__(self, config: EvaluatorConfig | None = None):
        cfg = config or EvaluatorConfig()
        self._validator  = InputValidator()
        self._prompt     = PromptBuilder()
        self._ai         = AIClient(cfg)
        self._response   = ResponseValidator()
        self._assembler  = ReportAssembler()

    def generate_report(self, school: str, personal: dict,
                        performance: dict, remarks: dict) -> Dict:
        self._validator.validate(school, personal, performance, remarks)
        prompt   = self._prompt.build(school, performance, remarks)
        ai_data  = self._ai.call(prompt)
        self._response.validate(school, ai_data)
        return self._assembler.assemble(school, personal, performance, remarks, ai_data)


if __name__ == "__main__":
    evaluator = InternshipEvaluator() 
    personal    = {"name": "Rawlings Ngenge", "id": "ST001"}
    performance = {"tasks_done": 5, "tasks_total": 5, "days_present": 45, "total_days": 50, "average_mark": 78}
    remarks     = {
        "comments": {
            "participation":    "Lacking in hardwork and proactiveness.",
            "discipline":       "Generally punctual.",
            "integration":      "Works independently but rarely shows initiative.",
            "general_behavior": "Professional conduct maintained.",
        },
        "supervisor_remark": "Very competent and has potential to grow with more initiative and engagement.",
    }

    try:
        report = evaluator.generate_report("COLTECH", personal, performance, remarks)
        print(json.dumps(report, indent=2))
    except ValidationError as e:
        log.error("Invalid input — %s", e)
    except AIResponseError as e:
        log.error("Evaluation failed — %s", e)