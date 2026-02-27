# app.py
import streamlit as st
import os
import requests
from dotenv import load_dotenv
from io import BytesIO
from PyPDF2 import PdfReader
import docx
import re
from fpdf import FPDF
import matplotlib.pyplot as plt

# ==============================
# LOAD ENVIRONMENT VARIABLES
# ==============================
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

GROQ_MODEL = "llama-3.1-8b-instant"
GROQ_ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"

# ==============================
# PAGE CONFIG
# ==============================
st.set_page_config(
    page_title="AI Career Recommender",
    page_icon="🚀",
    layout="wide"
)

st.title("🚀 AI Career Recommender")
st.markdown(
    "Upload your resume or enter skills manually to discover suitable career paths and generate a structured 6-month roadmap."
)

# ==============================
# FILE TEXT EXTRACTION
# ==============================
def extract_text_from_pdf(file_bytes):
    pdf = PdfReader(BytesIO(file_bytes))
    text = ""
    for page in pdf.pages:
        content = page.extract_text()
        if content:
            text += content + "\n"
    return text

def extract_text_from_docx(file_bytes):
    doc = docx.Document(BytesIO(file_bytes))
    return "\n".join([para.text for para in doc.paragraphs])

# ==============================
# CLEAN & EXTRACT SKILLS
# ==============================
def clean_and_extract_skills(text):
    text = text.lower()
    words = re.findall(r'\b[a-zA-Z]+\b', text)
    return list(set(words))

# ==============================
# GROQ API FUNCTION
# ==============================
def groq_generate(prompt, max_tokens=1200):
    if not GROQ_API_KEY:
        return "❌ GROQ_API_KEY not found. Please check your .env file."
    
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": "You are a professional AI career advisor."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": max_tokens
    }

    try:
        response = requests.post(
            GROQ_ENDPOINT,
            headers=headers,
            json=payload,
            timeout=60
        )
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        else:
            return f"❌ API Error {response.status_code}: {response.text}"

    except Exception as e:
        return f"❌ Connection Error: {str(e)}"

# ==============================
# CAREER RECOMMENDATION
# ==============================
def get_career_recommendations(skills):
    prompt = f"""
Based on the following skills:

{', '.join(skills[:50])}

Suggest 5 suitable career paths.

For each career provide:
- Career Name
- Short reason (1-2 lines)

Keep it structured and professional.
"""
    return groq_generate(prompt, max_tokens=600)

# ==============================
# ROADMAP GENERATION
# ==============================
def generate_roadmap(career):
    prompt = f"""
Create a COMPLETE and DETAILED 6-month roadmap for becoming a {career}.

IMPORTANT:
- Provide full details from Month 1 to Month 6
- Do NOT stop early
- Use headings: Month 1, Month 2, Month 3, Month 4, Month 5, Month 6
- Use bullet points
- Avoid tables

For EACH month include:
- Skills to learn
- Tools to master
- 2 Practical Projects
- Certifications (if useful)

Make it structured, detailed, and practical.
"""
    return groq_generate(prompt, max_tokens=1500)

# ==============================
# PDF DOWNLOAD FUNCTION
# ==============================
def download_pdf(content):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Arial", size=12)
    
    for line in content.split("\n"):
        # Prevent FPDF horizontal space error
        line = re.sub(r'(\S{80,})', lambda m: ' '.join([m.group(0)[i:i+80] for i in range(0, len(m.group(0)), 80)]), line)
        pdf.multi_cell(180, 7, line)
    
    pdf_buffer = BytesIO()
    pdf.output(pdf_buffer)
    pdf_buffer.seek(0)
    return pdf_buffer

# ==============================
# SKILL GAP ANALYSIS
# ==============================
def skill_gap_analysis(user_skills, required_skills):
    matched = [s for s in user_skills if s in required_skills]
    missing = [s for s in required_skills if s not in user_skills]
    score = round(len(matched)/len(required_skills)*100, 2) if required_skills else 0
    return matched, missing, score

# ==============================
# SESSION STATE
# ==============================
if "career_output" not in st.session_state:
    st.session_state.career_output = None

if "roadmap" not in st.session_state:
    st.session_state.roadmap = None

if "selected_career" not in st.session_state:
    st.session_state.selected_career = ""

# ==============================
# UI SECTION
# ==============================
uploaded_file = st.file_uploader("📄 Upload Resume (PDF/DOCX/TXT)", type=["pdf","docx","txt"])
manual_skills = st.text_input("✏️ Or enter skills manually (comma-separated):")

resume_text = ""

if uploaded_file:
    file_bytes = uploaded_file.getvalue()
    if uploaded_file.name.endswith(".pdf"):
        resume_text = extract_text_from_pdf(file_bytes)
    elif uploaded_file.name.endswith(".docx"):
        resume_text = extract_text_from_docx(file_bytes)
    elif uploaded_file.name.endswith(".txt"):
        resume_text = file_bytes.decode("utf-8")
    
    st.success("✅ Resume text extracted successfully!")

# Combine Skills
skills = []
if resume_text:
    skills.extend(clean_and_extract_skills(resume_text))

if manual_skills:
    manual_list = [s.strip().lower() for s in manual_skills.split(",") if s.strip()]
    skills.extend(manual_list)

skills = list(set(skills))

# ==============================
# CAREER SUGGESTIONS
# ==============================
if st.button("🎯 Get Career Suggestions"):
    if not skills:
        st.warning("Please upload a resume or enter skills.")
    else:
        st.subheader("✅ Detected Skills")
        st.write(", ".join(skills[:30]))
        
        with st.spinner("Generating career recommendations..."):
            st.session_state.career_output = get_career_recommendations(skills)

if st.session_state.career_output:
    st.subheader("🎯 Career Suggestions")
    st.write(st.session_state.career_output)

    st.markdown("---")
    st.subheader("📌 Generate 6-Month Roadmap")
    selected_career = st.text_input("Enter exact career name from above:", key="selected_career")

    if st.button("📚 Generate Roadmap"):
        if not selected_career.strip():
            st.warning("Please enter a career name.")
        else:
            with st.spinner("Generating roadmap..."):
                st.session_state.roadmap = generate_roadmap(selected_career)

# ==============================
# DISPLAY ROADMAP, PDF, AND SKILL GAP
# ==============================
if st.session_state.roadmap:
    st.subheader("📚 6-Month Roadmap")
    st.write(st.session_state.roadmap)

    # Download PDF
    st.download_button(
        "💾 Download Roadmap as PDF",
        data=download_pdf(st.session_state.roadmap),
        file_name="career_roadmap.pdf",
        mime="application/pdf"
    )

    # Example: simple skill gap chart
    required_skills_example = ["python","machine learning","data analysis","sql","git"]  # Replace with career-specific skills if known
    matched, missing, score = skill_gap_analysis(skills, required_skills_example)
    
    st.subheader("📊 Skill Gap Analysis")
    st.write(f"Match Score: {score}%")
    st.write(f"Matched Skills: {', '.join(matched)}")
    st.write(f"Missing Skills: {', '.join(missing)}")

    # Plot chart
    fig, ax = plt.subplots()
    ax.bar(["Matched", "Missing"], [len(matched), len(missing)], color=["green","red"])
    ax.set_ylabel("Number of Skills")
    ax.set_title("Skill Gap Analysis")
    st.pyplot(fig)