import os
import json
from datetime import datetime
from dotenv import load_dotenv
from google import genai

# Load variables from .env file
load_dotenv()

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
# Client picks up GEMINI_API_KEY from environment automatically
client = genai.Client(api_key=GEMINI_API_KEY)

# COLTECH: one overall remark + one comment per criterion
COLTECH_REMARKS = {
    "overall_remark": "A dedicated and hardworking intern who showed great commitment throughout.",
    "comments": {
        "participation":    "Always arrived prepared, contributed meaningfully, and delivered quality work.",
        "discipline":       "Rarely late and maintained consistent regularity across the internship.",
        "integration":      "Asked insightful questions, worked independently, and showed creativity.",
        "general_behavior": "Respectful and professional with all staff members at every level.",
    }
}

# NAHPI: single overall remark
NAHPI_REMARKS = {
    "supervisor_remark": 
    "The intern shows great initiative and technical aptitude. "
    "Communication with the team was excellent and deadlines were mostly respected. "
    "Needs to improve time management and documentation habits.",
}

def build_coltech_prompt(p: dict, r: dict) -> str:
    task_pct = p["tasks_done"] / p["tasks_total"] * 100
    att_pct  = p["days_present"] / p["total_days"] * 100
    comments = "\n".join(
        f'  - {cid}: "{text}"' for cid, text in r["comments"].items()
    )
    return f"""You are an expert academic evaluator for the COLTECH internship framework.

## Performance Data
- Tasks: {p["tasks_done"]}/{p["tasks_total"]} ({task_pct:.1f}%)
- Attendance: {p["days_present"]}/{p["total_days"]} days ({att_pct:.1f}%)
- Average Mark: {p["average_mark"]}%
- Overall Remark: "{r["overall_remark"]}"

## Per-Criterion Supervisor Comments
{comments}

## Criteria (Total: /30)
- participation    (max 12): Assiduous, hardworking, quality of work output
- discipline       (max  6): Punctuality, regularity, adherence to rules
- integration      (max  7): Independence, curiosity, logical thinking, creativity
- general_behavior (max  5): Rapport with staff, hierarchy, maturity

## Instructions
Cross-reference all comments holistically — a comment on one criterion may inform another.
Use tasks, attendance, and average mark as quantitative anchors.
Allocate a fair score (0 to max, 1 decimal) and write 2–3 sentence reasoning per criterion.
Write a 4–6 sentence overall summary.

Respond ONLY with valid JSON, no markdown, no extra text:
{{
  "summary": "...",
  "criteria": {{
    "participation":    {{"score": 0.0, "max": 12, "reasoning": "..."}},
    "discipline":       {{"score": 0.0, "max":  6, "reasoning": "..."}},
    "integration":      {{"score": 0.0, "max":  7, "reasoning": "..."}},
    "general_behavior": {{"score": 0.0, "max":  5, "reasoning": "..."}}
  }}
}}"""


def build_nahpi_prompt(p: dict, r: dict) -> str:
    task_pct = p["tasks_done"] / p["tasks_total"] * 100
    att_pct  = p["days_present"] / p["total_days"] * 100
    template = {
        k: {"score": 0, "reasoning": "..."}
        for k in ["A1","A2","A3","A4","B5","B6","B7","B8",
                  "C9","C10","C11","C12","D13","D14","D15","D16",
                  "E17","E18","E19","E20"]
    }
    return f"""You are an expert academic evaluator for the NAHPI internship framework.

## Performance Data
- Tasks: {p["tasks_done"]}/{p["tasks_total"]} ({task_pct:.1f}%)
- Attendance: {p["days_present"]}/{p["total_days"]} days ({att_pct:.1f}%)
- Average Mark: {p["average_mark"]}%
- Supervisor Remark: "{r["supervisor_remark"]}"

## Scoring Scale (integers only)
1=Poor | 2=Underdeveloped | 3=Average | 4=Good | 5=Outstanding

## 20 Sub-Criteria
A: Quality of Work (/20)
  A1: Competency in performing assigned tasks
  A2: Respect of established standards
  A3: Respect of time allowed (deadline)
  A4: Respect of organization and engagement

B: Job Knowledge / Technical Skills (/20)
  B5: Demonstration of skills required to perform assigned tasks
  B6: Ability to use tools, materials, and equipment effectively
  B7: Ability to use computer-related technology effectively
  B8: Respect of established standards and operating procedure (ethics & safety)

C: Communication & Interpersonal Skills (/20)
  C9:  Ability to communicate effectively
  C10: Ability to listen and understand others
  C11: Ability to work in a team to perform tasks effectively
  C12: Demonstration of mutual respect towards colleagues

D: Initiative and Leadership (/20)
  D13: Demonstration of commitment on the job
  D14: Initiative and Motivation
  D15: Ability to think analytically
  D16: Ability to generate creative solutions to problems

E: Personal Development and Learning (/20)
  E17: Ability to adapt to changing dynamics in the work environment
  E18: Disposition to learn new skills and knowledge
  E19: Ability to receive feedback
  E20: Endeavor to pursue opportunities for professional growth

## Instructions
Analyze the remark for tone, specific praise, and concerns.
Attendance anchors D13 and E17. Tasks + average mark anchor Sections A and B.
Write 1–2 sentence reasoning per item. Write a 4–6 sentence overall summary.

Respond ONLY with valid JSON, no markdown, no extra text:
{{
  "summary": "...",
  "items": {json.dumps(template, indent=2)}
}}"""


def call_gemini(prompt: str) -> dict:
    response = client.models.generate_content(
        model="gemini-2.5-flash", contents=prompt
    )
    raw = response.text.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    return json.loads(raw)


def assemble_coltech(personal: dict, perf: dict, remarks: dict, gemini: dict) -> dict:
    criteria_out = []
    total = 0.0
    for cid, max_score in [("participation",12),("discipline",6),("integration",7),("general_behavior",5)]:
        e = gemini["criteria"][cid]
        score = round(max(0.0, min(float(max_score), float(e["score"]))), 1)
        total += score
        criteria_out.append({
            "criterion": cid, "score": score, "max": max_score,
            "percentage": f"{score/max_score*100:.1f}%",
            "supervisor_comment": remarks["comments"][cid],
            "reasoning": e["reasoning"],
        })
    return {
        "metadata": {"school": "COLTECH", "generated_at": datetime.utcnow().isoformat()+"Z",
                     "disclaimer": "Scores are AI-inferred. Human review recommended."},
        "intern": personal,
        "input_data": {**perf,
            "task_completion": f"{perf['tasks_done']}/{perf['tasks_total']}",
            "attendance_rate": f"{perf['days_present']/perf['total_days']*100:.1f}%",
            "overall_remark": remarks["overall_remark"]},
        "evaluation": {
            "summary": gemini["summary"],
            "criteria": criteria_out,
            "totals": {"total_score": round(total,1), "total_max": 30,
                       "overall_percentage": f"{total/30*100:.1f}%"},
        },
    }


def assemble_nahpi(personal: dict, perf: dict, remarks: dict, gemini: dict) -> dict:
    sections_def = [
        ("A","Quality of Work",20,["A1","A2","A3","A4"]),
        ("B","Job Knowledge / Technical Skills",20,["B5","B6","B7","B8"]),
        ("C","Communication & Interpersonal Skills",20,["C9","C10","C11","C12"]),
        ("D","Initiative and Leadership Qualities",20,["D13","D14","D15","D16"]),
        ("E","Personal Development and Learning",20,["E17","E18","E19","E20"]),
    ]
    sections_out = []
    grand_total = 0
    for sec, label, sec_max, ids in sections_def:
        items_out = []
        for iid in ids:
            e = gemini["items"][iid]
            score = max(1, min(5, int(round(float(e["score"])))))
            items_out.append({"id": iid, "score": score, "max": 5, "reasoning": e["reasoning"]})
        sec_score = sum(i["score"] for i in items_out)
        grand_total += sec_score
        sections_out.append({"section": sec, "label": label,
                              "section_score": sec_score, "section_max": sec_max,
                              "section_percentage": f"{sec_score/sec_max*100:.1f}%",
                              "items": items_out})
    return {
        "metadata": {"school": "NAHPI", "generated_at": datetime.utcnow().isoformat()+"Z",
                     "disclaimer": "Scores are AI-inferred. Human review recommended."},
        "intern": personal,
        "input_data": {**perf,
            "task_completion": f"{perf['tasks_done']}/{perf['tasks_total']}",
            "attendance_rate": f"{perf['days_present']/perf['total_days']*100:.1f}%",
            "supervisor_remark": remarks["supervisor_remark"]},
        "evaluation": {
            "summary": gemini["summary"],
            "sections": sections_out,
            "totals": {"total_score": grand_total, "total_max": 100,
                       "overall_percentage": f"{grand_total/100*100:.1f}%"},
        },
    }


SCHOOL = "NAHPI"  

PERSONAL_INFO = {
    "intern_name":       "Jean Dupont",
    "student_id":        "ST2024001",
    "department":        "Computer Engineering",
    "internship_period": "Jan 2025 – Mar 2025",
    "Field_supervisor_name":   "Dr. Nkeng",
    "organization":      "TechCorp Cameroon",
}

PERFORMANCE = {
    "tasks_done":    4,
    "tasks_total":   5,
    "days_present":  45,
    "total_days":    50,
    "average_mark":  72.0,  # out of 100
}

if SCHOOL == "COLTECH":
    result = call_gemini(build_coltech_prompt(PERFORMANCE, COLTECH_REMARKS))
    report = assemble_coltech(PERSONAL_INFO, PERFORMANCE, COLTECH_REMARKS, result)
else:
    result = call_gemini(build_nahpi_prompt(PERFORMANCE, NAHPI_REMARKS))
    report = assemble_nahpi(PERSONAL_INFO, PERFORMANCE, NAHPI_REMARKS, result)

print(json.dumps(report, indent=2))