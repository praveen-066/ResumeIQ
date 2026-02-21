"""
Dynamic ATS Scorer
==================
Weighted scoring breakdown (must sum to 100):
  - Keyword Match        : 40 pts
  - Skills Match         : 25 pts
  - Experience Relevance : 20 pts
  - Education Relevance  : 10 pts
  - Formatting Check     :  5 pts

Scores start at 0 and ONLY increase based on actual matches.
No default high-score bias.
"""

import re

# ---------------------------------------------------------------------------
# Role knowledge base  – keywords + required skills per role
# ---------------------------------------------------------------------------

ROLE_KEYWORDS = {
    "Frontend Developer": [
        "html", "css", "javascript", "react", "vue", "angular", "typescript",
        "next.js", "redux", "webpack", "sass", "less", "responsive", "ui/ux",
        "dom", "ajax", "rest api", "git", "figma", "accessibility", "jest",
        "tailwind", "bootstrap", "vite", "component", "hooks", "state management"
    ],
    "Backend Developer": [
        "python", "java", "node.js", "express", "django", "flask", "spring",
        "rest api", "graphql", "sql", "postgresql", "mysql", "mongodb", "redis",
        "docker", "aws", "microservices", "authentication", "jwt", "kafka",
        "rabbitmq", "linux", "nginx", "ci/cd", "git", "orm", "database design",
        "data modeling", "caching", "security"
    ],
    "Full Stack Developer": [
        "html", "css", "javascript", "react", "node.js", "python", "sql",
        "mongodb", "git", "docker", "rest api", "aws", "typescript", "next.js",
        "express", "postgresql", "redux", "authentication", "deployment",
        "linux", "ci/cd", "microservices", "responsive design"
    ],
    "Software Engineer": [
        "python", "java", "c++", "data structures", "algorithms", "system design",
        "object oriented", "design patterns", "git", "sql", "testing", "debugging",
        "agile", "scrum", "code review", "performance", "scalability",
        "distributed systems", "linux", "problem solving"
    ],
    "Web Developer": [
        "html", "css", "javascript", "php", "wordpress", "bootstrap", "jquery",
        "seo", "responsive design", "git", "ftp", "cms", "mysql",
        "web performance", "cross-browser", "accessibility", "web hosting"
    ],
    "Mobile App Developer": [
        "swift", "kotlin", "react native", "flutter", "dart", "ios", "android",
        "firebase", "xcode", "android studio", "rest api", "push notifications",
        "app store", "play store", "mobile ui", "offline storage", "git"
    ],
    "Data Scientist": [
        "python", "r", "sql", "pandas", "numpy", "scikit-learn", "tensorflow",
        "pytorch", "statistics", "machine learning", "data visualization",
        "tableau", "power bi", "jupyter", "big data", "matplotlib", "seaborn",
        "hypothesis testing", "regression", "classification", "clustering",
        "feature engineering", "data cleaning", "etl"
    ],
    "Machine Learning Engineer": [
        "python", "tensorflow", "pytorch", "scikit-learn", "deep learning",
        "neural network", "nlp", "computer vision", "mlops", "data pipeline",
        "feature engineering", "model training", "model deployment", "aws",
        "docker", "kubernetes", "airflow", "spark", "gpu", "cuda"
    ],
    "AI Engineer": [
        "python", "deep learning", "nlp", "transformers", "llm", "bert",
        "computer vision", "tensorflow", "pytorch", "openai", "langchain",
        "rag", "vector database", "prompt engineering", "model fine-tuning",
        "opencv", "hugging face", "cuda", "gpu", "reinforcement learning"
    ],
    "DevOps Engineer": [
        "aws", "docker", "kubernetes", "ci/cd", "jenkins", "linux", "bash",
        "python", "terraform", "ansible", "monitoring", "prometheus", "grafana",
        "git", "helm", "nginx", "load balancing", "infrastructure as code",
        "cloud", "security", "gitlab", "github actions"
    ],
    "Cloud Engineer": [
        "aws", "azure", "google cloud", "terraform", "docker", "kubernetes",
        "linux", "networking", "vpc", "iam", "s3", "ec2", "lambda",
        "cloudwatch", "load balancer", "auto scaling", "database", "security",
        "cost optimization", "serverless", "microservices"
    ],
    "Site Reliability Engineer (SRE)": [
        "linux", "python", "go", "ansible", "terraform", "monitoring",
        "ci/cd", "kubernetes", "prometheus", "grafana", "incident management",
        "sla", "slo", "error budget", "on-call", "reliability",
        "observability", "distributed systems", "performance"
    ],
    "Cybersecurity Analyst": [
        "network security", "linux", "python", "siem", "firewalls", "wireshark",
        "risk assessment", "vulnerability", "penetration testing", "ids/ips",
        "encryption", "forensics", "compliance", "iso 27001", "nist",
        "incident response", "threat intelligence", "zero trust", "vpn"
    ],
    "Penetration Tester": [
        "kali linux", "metasploit", "burp suite", "python", "bash",
        "network security", "ethical hacking", "oscp", "ceh", "nmap",
        "sqlmap", "owasp", "web application", "reverse engineering",
        "social engineering", "exploit", "ctf", "vulnerability assessment"
    ],
    "Blockchain Developer": [
        "solidity", "ethereum", "smart contracts", "web3.js", "cryptography",
        "rust", "go", "hardhat", "truffle", "defi", "nft", "consensus",
        "hyperledger", "ipfs", "erc20", "gas optimization", "wallet"
    ],
    "Embedded Systems Engineer": [
        "c", "c++", "microcontrollers", "rtos", "pcb design", "iot",
        "firmware", "arduino", "raspberry pi", "stm32", "uart", "spi", "i2c",
        "assembly", "debugging", "oscilloscope", "real time", "baremetal"
    ],
    "Game Developer": [
        "c++", "c#", "unity", "unreal engine", "3d math", "graphics programming",
        "opengl", "directx", "vulkan", "physics engine", "shaders", "animation",
        "game design", "multiplayer", "networking", "optimization", "blender"
    ],
    "Database Administrator (DBA)": [
        "sql", "postgresql", "mysql", "oracle", "performance tuning",
        "backup", "recovery", "nosql", "indexing", "query optimization",
        "replication", "sharding", "mongodb", "high availability",
        "data modeling", "stored procedures", "triggers", "etl"
    ],
    "Data Engineer": [
        "python", "sql", "apache spark", "hadoop", "kafka", "etl",
        "data warehouse", "airflow", "aws", "azure", "google cloud",
        "redshift", "snowflake", "bigquery", "data modeling", "pipelines",
        "dbt", "delta lake", "data lake", "streaming", "batch processing"
    ],
    "QA / Automation Test Engineer": [
        "selenium", "python", "java", "jira", "cypress", "testng", "junit",
        "api testing", "postman", "robot framework", "cucumber", "bdd",
        "test plan", "test cases", "regression", "performance testing",
        "load testing", "bug tracking", "ci/cd", "git", "appium"
    ],
    "Network Engineer": [
        "cisco", "tcp/ip", "routing", "switching", "vpn", "firewalls",
        "wireshark", "bgp", "ospf", "vlan", "wan", "lan", "dns", "dhcp",
        "network design", "troubleshooting", "ccna", "ccnp", "load balancer",
        "sdwan", "mpls", "network security", "qos"
    ],
    "Systems Engineer": [
        "linux", "windows server", "virtualization", "vmware", "bash",
        "powershell", "active directory", "ldap", "dns", "dhcp", "networking",
        "storage", "san", "nas", "backup", "disaster recovery",
        "monitoring", "capacity planning", "scripting", "cloud"
    ],
}

# Degree keywords for education scoring
EDUCATION_KEYWORDS = [
    "bachelor", "b.tech", "b.e", "b.sc", "bs", "undergraduate",
    "master", "m.tech", "m.e", "m.sc", "ms", "mba",
    "phd", "doctorate", "computer science", "information technology",
    "electronics", "engineering", "mathematics", "statistics",
    "degree", "university", "college", "institute of technology"
]

# Experience keywords for experience scoring
EXPERIENCE_KEYWORDS = [
    "experience", "work experience", "employment", "work history",
    "developer", "engineer", "analyst", "intern", "internship",
    "project", "built", "developed", "implemented", "designed",
    "worked at", "company", "organization", "position", "role",
    "years", "months", "full-time", "part-time", "freelance",
    "led", "managed", "delivered", "collaborated", "contributed"
]


# ---------------------------------------------------------------------------
# Helper: count keyword matches in resume text
# ---------------------------------------------------------------------------

def _count_matches(text: str, keyword_list: list) -> tuple[int, list]:
    """Return (match_count, matched_keywords) for a list of keywords."""
    found = []
    text_lower = text.lower()
    for kw in keyword_list:
        # Word boundary match – handles multi-word phrases too
        pattern = r'\b' + re.escape(kw.lower()) + r'\b'
        if re.search(pattern, text_lower):
            found.append(kw)
    return len(found), found


# ---------------------------------------------------------------------------
# Main scoring function
# ---------------------------------------------------------------------------

def calculate_ats_score(data: dict, target_role: str = "") -> tuple[int, dict, list]:
    """
    Calculate a dynamic ATS score (0–100) based on actual resume content
    versus the target role's requirements.

    Weights:
      Keyword Match        : 40 pts
      Skills Match         : 25 pts
      Experience Relevance : 20 pts
      Education Relevance  : 10 pts
      Formatting Check     :  5 pts

    All scores start at 0 and grow only from actual matches.
    """

    text: str = data.get("text", "")
    resume_skills: list = [s.lower() for s in data.get("skills", [])]
    feedback: list = []

    # Resolve role keyword list (fall back to a generic common-skills list)
    role_kws = ROLE_KEYWORDS.get(target_role, list(set(
        kw for kws in ROLE_KEYWORDS.values() for kw in kws
    )))

    # ── 1. KEYWORD MATCH  (40 pts) ──────────────────────────────────────────
    total_kws = len(role_kws)
    matched_count, matched_kws = _count_matches(text, role_kws)

    if total_kws > 0:
        kw_ratio = matched_count / total_kws
    else:
        kw_ratio = 0.0

    # Tiered keyword score to avoid inflated scores from partial matches
    if kw_ratio >= 0.70:
        keyword_score = 40
    elif kw_ratio >= 0.50:
        keyword_score = 32
    elif kw_ratio >= 0.35:
        keyword_score = 24
    elif kw_ratio >= 0.20:
        keyword_score = 16
    elif kw_ratio >= 0.10:
        keyword_score = 8
    elif kw_ratio > 0:
        keyword_score = 4
    else:
        keyword_score = 0

    if keyword_score < 20:
        feedback.append(
            f"Low keyword density for '{target_role}'. "
            f"Only {matched_count}/{total_kws} role keywords found."
        )

    # ── 2. SKILLS MATCH  (25 pts) ───────────────────────────────────────────
    required_skills = [s.lower() for s in ROLE_KEYWORDS.get(target_role, [])]
    if required_skills:
        skills_matched = [s for s in required_skills if s in resume_skills or
                          any(s in rs for rs in resume_skills)]
        skills_ratio = len(skills_matched) / len(required_skills)
    else:
        skills_matched = []
        skills_ratio = 0.0

    if skills_ratio >= 0.65:
        skills_score = 25
    elif skills_ratio >= 0.45:
        skills_score = 20
    elif skills_ratio >= 0.30:
        skills_score = 15
    elif skills_ratio >= 0.15:
        skills_score = 10
    elif skills_ratio > 0:
        skills_score = 5
    else:
        skills_score = 0

    if skills_score < 15:
        feedback.append(
            f"Skills gap detected. Matched {len(skills_matched)}/{len(required_skills)} "
            f"required skills for '{target_role}'."
        )

    # ── 3. EXPERIENCE RELEVANCE  (20 pts) ───────────────────────────────────
    exp_matched, _ = _count_matches(text, EXPERIENCE_KEYWORDS)

    # Count number of years/duration signals
    year_pattern = r'\b(\d{1,2})\s*\+?\s*(?:years?|yrs?)\b'
    year_mentions = re.findall(year_pattern, text.lower())
    total_exp_years = sum(int(y) for y in year_mentions) if year_mentions else 0

    if exp_matched >= 8 and total_exp_years >= 2:
        experience_score = 20
    elif exp_matched >= 6:
        experience_score = 16
    elif exp_matched >= 4:
        experience_score = 12
    elif exp_matched >= 2:
        experience_score = 7
    elif exp_matched >= 1:
        experience_score = 3
    else:
        experience_score = 0

    if experience_score < 10:
        feedback.append(
            "Experience section appears weak or missing. Add role titles, "
            "companies, durations, and specific contributions."
        )

    # ── 4. EDUCATION RELEVANCE  (10 pts) ────────────────────────────────────
    edu_matched, _ = _count_matches(text, EDUCATION_KEYWORDS)

    if edu_matched >= 4:
        education_score = 10
    elif edu_matched >= 2:
        education_score = 7
    elif edu_matched >= 1:
        education_score = 4
    else:
        education_score = 0

    if education_score == 0:
        feedback.append(
            "Education section not detected. Include degree, institution, "
            "and graduation year."
        )

    # ── 5. FORMATTING CHECK  (5 pts) ────────────────────────────────────────
    text_len = len(text.strip())
    word_count = len(text.split())

    has_email = bool(re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text))
    has_phone = bool(re.search(r'(\+?\d[\d\s\-().]{7,}\d)', text))
    has_sections = sum([
        bool(re.search(r'\b(experience|education|skills|projects|summary|objective)\b', text.lower())),
        bool(re.search(r'\b(certifications?|achievements?|awards?)\b', text.lower())),
    ])

    formatting_score = 0
    if 200 <= word_count <= 1200:
        formatting_score += 2
    elif word_count > 0:
        formatting_score += 1
    if has_email and has_phone:
        formatting_score += 2
    elif has_email or has_phone:
        formatting_score += 1
    if has_sections >= 2:
        formatting_score += 1

    formatting_score = min(5, formatting_score)

    if not has_email or not has_phone:
        feedback.append("Contact information incomplete. Include both email and phone.")
    if word_count < 200:
        feedback.append("Resume appears too short. Aim for 400–900 words.")
    elif word_count > 1200:
        feedback.append("Resume may be too long. Keep it focused (400–900 words ideal).")

    # ── Final Score ──────────────────────────────────────────────────────────
    total_score = (
        keyword_score +
        skills_score +
        experience_score +
        education_score +
        formatting_score
    )

    breakdown = {
        "Keyword Match": keyword_score,
        "Skills Match": skills_score,
        "Experience": experience_score,
        "Education": education_score,
        "Formatting": formatting_score,
    }

    return int(min(100, total_score)), breakdown, feedback
