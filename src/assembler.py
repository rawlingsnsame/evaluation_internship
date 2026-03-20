from typing import Dict

from src.criterions import SCHOOL_CRITERIONS


class ReportAssembler:
    """Merges validated AI output with personal/performance data into the final report."""

    def assemble(self, school: str, personal: dict, performance: dict,
                 remarks: dict, ai_data: dict) -> Dict:
        report = {
            "intern": personal,
            "evaluation": {"summary": ai_data["summary"]},
        }
        t_pct = performance["tasks_done"] / performance["tasks_total"] * 100
        a_pct = performance["days_present"] / performance["total_days"] * 100
        report["performance"] = {
            "tasks":      f"{performance['tasks_done']}/{performance['tasks_total']} ({t_pct:.1f}%)",
            "attendance": f"{performance['days_present']}/{performance['total_days']} ({a_pct:.1f}%)",
            "avg_mark":   f"{performance['average_mark']}%",
        }

        total = 0.0
        if school == "COLTECH":
            items = []
            for cid, m, desc in SCHOOL_CRITERIONS["COLTECH"]["definitions"]:
                entry = ai_data["criteria"][cid]
                score = round(max(0.0, min(float(m), float(entry["score"]))), 1)
                total += score
                items.append({
                    "id": cid, "label": desc.split(":")[0],
                    "score": score, "max": m,
                    "supervisor_comment": remarks["comments"][cid],
                    "reasoning": entry.get("reasoning", ""),
                })
            report["evaluation"]["criteria"] = items
        else:
            sections = []
            for s in SCHOOL_CRITERIONS["NAHPI"]["sections"]:
                sec_items = []
                for iid, desc in s["items"]:
                    entry = ai_data["items"][iid]
                    score = max(1, min(5, int(round(float(entry["score"])))))
                    sec_items.append({
                        "id": iid, "description": desc,
                        "score": score, "max": 5,
                        "reasoning": entry.get("reasoning", ""),
                    })
                s_total = sum(i["score"] for i in sec_items)
                total  += s_total
                sections.append({
                    "label": s["label"], "score": s_total, "max": 20,
                    "items": sec_items,
                })
            report["evaluation"]["sections"] = sections

        max_total = SCHOOL_CRITERIONS[school]["max_total"]
        report["evaluation"]["totals"] = {
            "score": round(total, 1),
            "max": max_total,
            "percentage": f"{total / max_total * 100:.1f}%",
        }
        return report
