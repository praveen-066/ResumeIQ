TARGET_ROLES = {
    "Software Development": [
        "Frontend Developer",
        "Backend Developer",
        "Full Stack Developer",
        "Software Engineer",
        "Mobile App Developer (iOS/Android)",
        "Game Developer",
        "Embedded Systems Engineer",
        "Blockchain Developer"
    ],
    "Data & AI": [
        "Data Scientist",
        "Data Engineer",
        "Data Analyst",
        "Machine Learning Engineer",
        "AI Research Engineer",
        "Business Intelligence (BI) Developer"
    ],
    "Cloud & DevOps": [
        "DevOps Engineer",
        "Cloud Architect",
        "Site Reliability Engineer (SRE)",
        "System Administrator"
    ],
    "Design & Product": [
        "UI/UX Designer",
        "Product Manager",
        "Product Designer",
        "Graphic Designer"
    ],
    "Cybersecurity": [
        "Cybersecurity Analyst",
        "Ethical Hacker / Pen Tester",
        "Security Engineer"
    ],
    "Management & Business": [
        "Project Manager",
        "Business Analyst",
        "HR Manager",
        "Talent Acquisition Specialist",
        "Marketing Manager",
        "Sales Executive",
        "Customer Success Manager"
    ],
    "Testing": [
        "QA Engineer",
        "Automation Test Engineer"
    ]
}

def get_all_roles():
    all_roles = []
    for category in TARGET_ROLES.values():
        all_roles.extend(category)
    return sorted(all_roles)
