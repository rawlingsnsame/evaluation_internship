_HOW_TO = {
    "message": "Welcome to the Internship Evaluation API.",
    "usage": "Send a POST request to /evaluate with the intern's details to generate an evaluation report.",
    "docs": "Visit /docs for the full interactive API documentation.",
    "example_request": {
        "url": "POST /evaluate",
        "body": {
            "personal": {
                "id": "ST001",
                "name": "Jean Dupont",
                "school": "COLTECH"
            },
            "performance": {
                "tasks_done": 4,
                "tasks_total": 5,
                "days_present": 45,
                "total_days": 50,
                "average_mark": 78
            },
            "remarks": {
                "supervisor_remark": "A dedicated intern with good potential.",
                "comments": {
                    "participation":    "Hardworking and proactive.",
                    "discipline":       "Punctual and regular.",
                    "integration":      "Shows creativity and independence.",
                    "general_behavior": "Professional with all staff."
                }
            }
        }
    }
}