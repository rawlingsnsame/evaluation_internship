SCHOOL_CRITERIONS = {
    "COLTECH": {
        "max_total": 30,
        "definitions": [
            ("participation", 12, "Participation at work: Assiduous, hardworking, intelligent, quality of work output."),
            ("discipline", 6, "Discipline: Punctuality, regularity, adherence to rules."),
            ("integration", 7, "Ability to integrate: Independence, curiosity, logical thinking, skillful, creative."),
            ("general_behavior", 5, "General Behavior: Rapport with staff, hierarchy, maturity, professional conduct.")
        ]
    },
    "NAHPI": {
        "max_total": 100,
        "sections": [
            {
                "letter": "A", "label": "Quality of Work", "max": 20,
                "items": [
                    ("1", "Competency in performing assigned tasks"),
                    ("2", "Respect of established standards"),
                    ("3", "Respect of time allowed (deadline)"),
                    ("4", "Respect of organization and engagement")
                ]
            },
            {
                "letter": "B", "label": "Job Knowledge/Technical Skills", "max": 20,
                "items": [
                    ("5", "Demonstration of skills required to perform assigned tasks"),
                    ("6", "Ability to use tools, materials, and equipment effectively"),
                    ("7", "Ability to use computer related technology effectively"),
                    ("8", "Respect of established standards, and operating procedure (ethics and safety protocols)")
                ]
            },
            {
                "letter": "C", "label": "Communication & Interpersonal Skills", "max": 20,
                "items": [
                    ("9", "Ability to communicate effectively"),
                    ("10", "Ability to listen and understand others (colleagues, customers, partners and supervisors)"),
                    ("11", "Ability to work in a team to perform tasks effectively"),
                    ("12", "Demonstration of mutual respect towards colleagues")
                ]
            },
            {
                "letter": "D", "label": "Initiative and Leadership Qualities", "max": 20,
                "items": [
                    ("13", "Demonstration of commitment on the Job"),
                    ("14", "Initiative and Motivation"),
                    ("15", "Ability to think Analytically"),
                    ("16", "Ability to generate creative solutions to problems")
                ]
            },
            {
                "letter": "E", "label": "Personal Development and Learning", "max": 20,
                "items": [
                    ("17", "Ability to adapt to changing dynamics in the work environment"),
                    ("18", "Disposition to learn new skills and knowledge"),
                    ("19", "Ability to receive feedback"),
                    ("20", "Endeavor to pursue opportunities for professional growth")
                ]
            }
        ]
    }
}