from flask import Flask, request, render_template
import pdfplumber
import docx2txt
import spacy
import re
import os
import pandas as pd
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
nlp = spacy.load("en_core_web_sm")

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# Predefined skill keywords
SKILL_KEYWORDS = [
    'python', 'java', 'html', 'css', 'javascript', 'react', 'node',
    'sql', 'flask', 'aws', 'git', 'linux', 'docker', 'c++', 'c', 'mongodb',
    'machine learning', 'nlp', 'tensorflow', 'keras', 'pandas', 'numpy'
]

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
    # Normalize text to avoid line breaks interfering with numbers
    text = text.replace('\n', ' ').replace('\r', ' ')
    
    # Regex to match common Indian mobile formats
    pattern = r'(?:(?:\+91|91|0)?[\s\-]?)?[6-9]\d{9}'
    matches = re.findall(pattern, text)

    # Clean and format phone numbers
    cleaned = [re.sub(r'\D', '', m)[-10:] for m in matches if len(re.sub(r'\D', '', m)) >= 10]

    # Only return cleaned numbers (this will be shown in the results.html)
    return ', '.join(set(cleaned)) if cleaned else "N/A"

def extract_skills(text):
    text = text.lower()
    found_skills = set()
    for skill in SKILL_KEYWORDS:
        if skill.lower() in text:
            found_skills.add(skill)
    return list(found_skills)

def extract_details(text):
    return {
        'email': ', '.join(re.findall(r'\S+@\S+', text)) if re.findall(r'\S+@\S+', text) else "N/A",
        'phone': extract_phone(text),
        'skills': ', '.join(extract_skills(text)) if extract_skills(text) else "N/A"
    }

def calculate_match_score(resume_skills, job_skills):
    if not resume_skills or not job_skills:
        return 0.0
    resume_set = set(resume_skills)
    job_set = set(job_skills)
    match_count = len(resume_set.intersection(job_set))
    return (match_count / len(job_set)) * 100 if job_set else 0.0

def clear_uploaded_files():
    upload_folder = app.config['UPLOAD_FOLDER']
    for filename in os.listdir(upload_folder):
        file_path = os.path.join(upload_folder, filename)
        try:
            if os.path.isfile(file_path):
                os.remove(file_path)
        except Exception as e:
            # This will now only log errors, not any general information
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

        clear_uploaded_files()

        # Render the results.html page with the results data
        table_html = results.to_html(classes='table table-bordered', index=False)
        return render_template('results.html', table=table_html)

    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
