from flask import Flask, request, render_template
import pdfplumber
import docx2txt
import spacy
import re
import os
import pandas as pd
from werkzeug.utils import secure_filename
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'

# Load SpaCy model
nlp = spacy.load("en_core_web_sm")

# Email credentials from .env
SENDER_EMAIL = os.getenv("EMAIL_USER")
SENDER_PASSWORD = os.getenv("EMAIL_PASS")

# Create upload folder if not exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# Skill mapping with aliases
SKILL_ALIASES = {
    'python': ['python'],
    'java': ['java'],
    'html': ['html'],
    'css': ['css'],
    'javascript': ['javascript', 'js'],
    'react': ['react', 'reactjs'],
    'node': ['node', 'nodejs'],
    'sql': ['sql'],
    'flask': ['flask'],
    'aws': ['aws', 'amazon web services'],
    'git': ['git'],
    'linux': ['linux'],
    'docker': ['docker'],
    'c++': ['c++'],
    'c': ['c'],
    'mongodb': ['mongodb', 'mongo'],
    'machine learning': ['machine learning', 'ml'],
    'nlp': ['nlp', 'natural language processing'],
    'tensorflow': ['tensorflow'],
    'keras': ['keras'],
    'pandas': ['pandas'],
    'numpy': ['numpy']
}

def extract_text(file_path):
    text = ""
    if file_path.endswith('.pdf'):
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    elif file_path.endswith('.docx'):
        text = docx2txt.process(file_path)
    return text.strip().replace('\n', ' ')

def extract_phone(text):
    text = text.replace('\n', ' ').replace('\r', ' ')
    pattern = r'(?:(?:\+91|91|0)?[\s\-]?)?[6-9]\d{9}'
    matches = re.findall(pattern, text)
    cleaned = [re.sub(r'\D', '', m)[-10:] for m in matches if len(re.sub(r'\D', '', m)) >= 10]
    return ', '.join(set(cleaned)) if cleaned else "N/A"

def extract_skills(text):
    text = text.lower()
    found_skills = set()
    for main_skill, aliases in SKILL_ALIASES.items():
        for alias in aliases:
            if alias in text:
                found_skills.add(main_skill)
                break
    return list(found_skills)

def extract_details(text):
    email_matches = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
    skills = extract_skills(text)
    return {
        'email': ', '.join(email_matches) if email_matches else "N/A",
        'phone': extract_phone(text),
        'skills': ', '.join(skills) if skills else "N/A"
    }

def calculate_match_score(resume_skills, job_skills):
    if not resume_skills or not job_skills:
        return 0.0
    resume_set = set(resume_skills)
    job_set = set(job_skills)
    match_count = len(resume_set.intersection(job_set))
    return (match_count / len(job_set)) * 100 if job_set else 0.0

def send_email(recipient_email, candidate_name="Candidate"):
    subject = "Job Shortlisting Notification"
    body = f"""
    Dear {candidate_name},

    Congratulations! 🎉

    You have been shortlisted for the job based on your resume and skill match.

    We will contact you with further details.

    Regards,
    HR Team
    """

    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = recipient_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
        print(f"✅ Email sent to {recipient_email}")
    except Exception as e:
        print(f"❌ Failed to send email to {recipient_email}: {e}")

def clear_uploaded_files():
    upload_folder = app.config['UPLOAD_FOLDER']
    for filename in os.listdir(upload_folder):
        file_path = os.path.join(upload_folder, filename)
        try:
            if os.path.isfile(file_path):
                os.remove(file_path)
        except Exception as e:
            print(f"Error deleting file {file_path}: {e}")

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        job_desc = request.form['job_desc']
        files = request.files.getlist("resumes")

        if not files or files[0].filename == '':
            return render_template('index.html', message="⚠️ No resumes uploaded! Please try again.")

        job_skills = extract_skills(job_desc)
        extracted_data = []

        for file in files:
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)

            text = extract_text(file_path)
            if text:
                skills = extract_skills(text)
                details = extract_details(text)
                match_score = calculate_match_score(skills, job_skills)
                extracted_data.append({
                    'filename': filename,
                    'email': details['email'],
                    'phone': details['phone'],
                    'skills': details['skills'],
                    'match_score (%)': round(match_score, 2)
                })

        if not extracted_data:
            return render_template('index.html', message="⚠️ No valid resume data found!")

        results = pd.DataFrame(extracted_data)
        results = results.sort_values(by='match_score (%)', ascending=False)

        # Send email to top 2 candidates
        top_candidates = results.head(2)
        for _, row in top_candidates.iterrows():
            recipient = row['email'].split(',')[0].strip()
            if recipient != "N/A":
                send_email(recipient)

        clear_uploaded_files()
        table_html = results.to_html(classes='table table-bordered', index=False)
        return render_template('results.html', table=table_html)

    return render_template('index.html')

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
