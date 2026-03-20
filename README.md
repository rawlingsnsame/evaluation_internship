# Internship Evaluation System — Algorithm Design Report
**Schools:** NAHPI · COLTECH | **AI Engine:** OPENROUTER_API | **Language:** Python

---

## 1. The Problem

Universities require companies to evaluate interns using school-specific forms. Each school has different criteria and scoring rules. The supervisor fills in one free-text remark and provides basic attendance and task data.

The challenge is that numbers alone are incomplete. A student who finishes all tasks but needs constant supervision should not score the same as one who works independently. That distinction only exists in the written remark — not in the figures.

---

## 2. Inputs

| Input | Type | Purpose |
|---|---|---|
| Tasks completed / total | Numeric | Measures work output |
| Days present / total days | Numeric | Measures discipline and commitment |
| Supervisor remark | Free text | Primary scoring signal — captures attitude, quality, behaviour |
| School (NAHPI or COLTECH) | Selection | Determines rubric and output format |
| Intern details | Contextual | Used for report header only, not for scoring |

---

## 3. Algorithm

The algorithm runs in three stages.

### Stage 1 — Normalisation
Both numeric inputs are converted to rates between 0 and 1 so they are comparable regardless of internship length or task count.

```
task_rate      = tasks_completed / total_tasks
attendance_rate = days_present / total_days
```

### Stage 2 — Remark Analysis (LLM)
The remark and numeric rates are sent to LLM, which scores the intern on 7 behavioural dimensions (0.0 to 1.0 each):

- **Work Quality** — thoroughness and accuracy of work produced
- **Technical Skill** — competence with tools and technology
- **Communication** — clarity, listening, interpersonal effectiveness
- **Initiative** — proactiveness and self-starting behaviour
- **Discipline** — punctuality and rule-following
- **Team Integration** — teamwork and respect for colleagues
- **Independence** — ability to work without supervision

The remark is the primary signal. Numeric rates are supporting context only.

> *Example: "Completed tasks but needed constant reminders" → initiative: 0.28, independence: 0.25, work_quality: 0.70*

### Stage 3 — Weighted Score Fusion
Each rubric criterion is scored by blending the three signals using criterion-specific weights:

```
score = (task_rate × w1) + (attendance_rate × w2) + (AI_dimension_based_on_remark × w3)
```

Weights reflect what each criterion actually measures. Communication is 100% AI-driven (tasks and attendance say nothing about it). Discipline draws heavily from attendance. Commitment uses all three signals equally.

**NAHPI:** the 0–1 fused value maps to a Likert level 1–5 (Poor → Outstanding), then scales to the category's max points. Total out of 100.

**COLTECH:** the 0–1 fused value is multiplied directly by the criterion's max points. Total out of 30.

---

## 4. Output

A structured evaluation report formatted to the selected school's rubric, containing:
- Intern and supervisor details
- AI-generated summary (2 sentences)
- Scored criteria (Likert levels for NAHPI, raw points for COLTECH)
- Per-criterion observations (COLTECH only)
- AI dimension scores for transparency
- Supervisor's original remark
## 5. Why AI — Comparison

### Remark Analysis

| Approach | Why considered | Decision |
|---|---|---|
| **AI API** | Understands nuance and context. Returns per-dimension scores, not just a single sentiment label. Can separate "hardworking but lacks independence" into high work_quality and low independence simultaneously. | ✅ Chosen |
| VADER (rule-based) | Fast, no internet needed. Returns only one compound score (−1 to +1). Cannot split a remark into separate dimension scores. | ❌ Not used |
| RoBERTa / DistilBERT (local) | More accurate than VADER, runs offline. Still limited to POSITIVE / NEGATIVE with a confidence score — no per-dimension breakdown. | ⚠️ Offline fallback |
| Manual scoring by supervisor | Accurate but shifts the entire burden back to the supervisor, which the system is designed to reduce. | ❌ Not used |

### Score Computation

| Approach | Why considered | Decision |
|---|---|---|
| **Weighted linear fusion** | Simple, transparent, and tunable per criterion. Easy to explain to supervisors and academics. | ✅ Chosen |
| Trained ML model (regression) | Could learn optimal weights from data. Requires a labelled historical dataset that does not yet exist. | ❌ Not used |
| Equal weights | Simpler but ignores that some inputs are irrelevant to certain criteria (e.g. attendance has no bearing on communication). | ❌ Not used |
| Threshold rules | Easy for simple cases, brittle for mixed signals. A student with 95% attendance but a remark noting "frequently disruptive" should not score top on discipline. | ❌ Not used |
