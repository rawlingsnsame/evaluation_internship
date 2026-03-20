# Internship Performance Evaluation System

An AI-powered backend that evaluates internship students based on their tasks completed, attendance, average mark, and supervisor remarks. Supports two school evaluation frameworks: **COLTECH** and **NAHPI**.

---

## How It Works

Input data is validated locally, then a school-specific prompt is sent to an LLM via [OpenRouter](https://openrouter.ai). The model scores the student against the school's criteria and returns structured reasoning. Personal and supervisor details never leave your machine — they are merged into the final report locally after the AI call.

```
Input Data → Validate → Build Prompt → AI Scoring → Validate Response → JSON Report
```

---

## Supported Schools

**COLTECH** — scores 4 criteria totalling /30:
| Criterion | Max |
|---|---|
| Participation at Work | 12 |
| Discipline | 6 |
| Ability to Integrate | 7 |
| General Behavior | 5 |

Each criterion has a dedicated supervisor comment plus one overall remark.

**NAHPI** — scores 20 sub-criteria across 5 sections totalling /100:

| Section | Label | Max |
|---|---|---|
| A | Quality of Work | 20 |
| B | Job Knowledge / Technical Skills | 20 |
| C | Communication & Interpersonal Skills | 20 |
| D | Initiative and Leadership | 20 |
| E | Personal Development and Learning | 20 |

Items scored 1–5 (Poor → Outstanding). One overall supervisor remark.

---

## Setup

**Requirements:** Python 3.10+

```bash
pip install openai python-dotenv
```

Create a `.env` file:
```
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_API_KEY=your_key_here
```

---

## Usage

Edit the input data at the bottom of `evaluator.py`:

```python
personal    = {"name": "Jean Dupont", "id": "ST001"}
performance = {"tasks_done": 4, "tasks_total": 5, "days_present": 45, "total_days": 50, "average_mark": 78}
remarks     = {
    "comments": {
        "participation":    "Hardworking and proactive.",
        "discipline":       "Generally punctual.",
        "integration":      "Works independently and shows creativity.",
        "general_behavior": "Professional with all staff.",
    },
    "supervisor_remark": "A strong intern with good growth potential.",
}
```

Then run:
```bash
python evaluator.py
```

Output is a JSON report printed to the console.

---

## Models

Three models are tried in order — first success wins:

| Priority | Model | Role | Cost |
|---|---|---|---|
| 1 | `google/gemini-2.5-flash-lite` | Primary | ~$0.10/$0.40 per 1M tokens |
| 2 | `meta-llama/llama-4-scout:free` | Free fallback | Free |
| 3 | `mistralai/mistral-small-3.1-24b-instruct:free` | Free last resort | Free |

Configure retries and timeout via `EvaluatorConfig`:
```python
evaluator = InternshipEvaluator(EvaluatorConfig(max_retries=3, retry_delay=5, timeout=90))
```

---

## Architecture

| Class | Responsibility |
|---|---|
| `InputValidator` | Validates all inputs before the AI is called |
| `PromptBuilder` | Builds school-specific prompts with few-shot examples |
| `AIClient` | Handles API calls, per-model retries, and model fallback |
| `ResponseValidator` | Validates structure and score ranges of the AI response |
| `ReportAssembler` | Merges AI output with personal data into the final report |
| `InternshipEvaluator` | Thin orchestrator — calls each component in sequence |

---

## Project Structure

```
├# Internship Performance Evaluation System

An AI-powered backend that evaluates internship students based on their tasks completed, attendance, average mark, and supervisor remarks. Supports two school evaluation frameworks: **COLTECH** and **NAHPI**.

---

## How It Works

Input data is validated locally, then a school-specific prompt is sent to an LLM via [OpenRouter](https://openrouter.ai). The model scores the student against the school's criteria and returns structured reasoning. Personal and supervisor details never leave your machine — they are merged into the final report locally after the AI call.

```
Input Data → Validate → Build Prompt → AI Scoring → Validate Response → JSON Report
```

---

## Supported Schools

**COLTECH** — scores 4 criteria totalling /30:
| Criterion | Max |
|---|---|
| Participation at Work | 12 |
| Discipline | 6 |
| Ability to Integrate | 7 |
| General Behavior | 5 |

Each criterion has a dedicated supervisor comment plus one overall remark.

**NAHPI** — scores 20 sub-criteria across 5 sections totalling /100:

| Section | Label | Max |
|---|---|---|
| A | Quality of Work | 20 |
| B | Job Knowledge / Technical Skills | 20 |
| C | Communication & Interpersonal Skills | 20 |
| D | Initiative and Leadership | 20 |
| E | Personal Development and Learning | 20 |

Items scored 1–5 (Poor → Outstanding). One overall supervisor remark.

---

## Setup

**Requirements:** Python 3.10+

```bash
pip install openai python-dotenv
```

Create a `.env` file:
```
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_API_KEY=your_key_here
```

---

## Usage

Edit the input data at the bottom of `evaluator.py`:

```python
personal    = {"name": "Jean Dupont", "id": "ST001"}
performance = {"tasks_done": 4, "tasks_total": 5, "days_present": 45, "total_days": 50, "average_mark": 78}
remarks     = {
    "comments": {
        "participation":    "Hardworking and proactive.",
        "discipline":       "Generally punctual.",
        "integration":      "Works independently and shows creativity.",
        "general_behavior": "Professional with all staff.",
    },
    "supervisor_remark": "A strong intern with good growth potential.",
}
```

Then run:
```bash
python evaluator.py
```

Output is a JSON report printed to the console.

---

## Models

Three models are tried in order — first success wins:

| Priority | Model | Role | Cost |
|---|---|---|---|
| 1 | `google/gemini-2.5-flash-lite` | Primary | ~$0.10/$0.40 per 1M tokens |
| 2 | `meta-llama/llama-4-scout:free` | Free fallback | Free |
| 3 | `mistralai/mistral-small-3.1-24b-instruct:free` | Free last resort | Free |

Configure retries and timeout via `EvaluatorConfig`:
```python
evaluator = InternshipEvaluator(EvaluatorConfig(max_retries=3, retry_delay=5, timeout=90))
```

---

## Architecture

| Class | Responsibility |
|---|---|
| `InputValidator` | Validates all inputs before the AI is called |
| `PromptBuilder` | Builds school-specific prompts with few-shot examples |
| `AIClient` | Handles API calls, per-model retries, and model fallback |
| `ResponseValidator` | Validates structure and score ranges of the AI response |
| `ReportAssembler` | Merges AI output with personal data into the final report |
| `InternshipEvaluator` | Thin orchestrator — calls each component in sequence |

---

## Project Structure

```
src/                          
│  ├─ assembler.py
│  ├─ criterions.py
│  ├─ validators.py
│  ├─ prompt_builder.py
├─ main.py                    # entrypoint
├── .env               # API credentials (never commit this)
└── README.md
```