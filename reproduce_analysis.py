from utils.analyzer import parse_resume, analyze_skill_gap
from utils.scorer import calculate_ats_score
import json

# Sample Resume Text
sample_text = """
John Doe
johndoe@example.com
(555) 123-4567

Summary
Experienced Software Engineer with 5 years of experience in Python and Flask.

Experience
Software Developer at Tech Co.
- Developed web applications using Flask and React.
- Used SQL for database management.

Skills
Python, Flask, JavaScript, SQL, Git, Docker
"""

print("Testing Analysis Logic...")

try:
    # 1. Parse
    parsed_data = parse_resume(sample_text)
    print("Parsed Data:", json.dumps(parsed_data, indent=2))
    
    # 2. Score
    score, breakdown, feedback = calculate_ats_score(parsed_data)
    print(f"\nScore: {score}")
    print("Breakdown:", breakdown)
    print("Feedback:", feedback)
    
    # 3. Gap Analysis
    target_role = "Backend Developer"
    missing = analyze_skill_gap(parsed_data['skills'], target_role)
    print(f"\nMissing Skills for {target_role}:", missing)
    
    print("\nSUCCESS: Analysis logic executed without errors.")

except Exception as e:
    print(f"\nFAILURE: {e}")
    import traceback
    traceback.print_exc()
