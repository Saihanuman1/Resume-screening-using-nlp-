# Resume-screening-using-nlp
Overview A web-based application that automates the resume screening process using Flask and Natural Language Processing (NLP). This system extracts important details such as phone numbers, email addresses, and skills from resumes, and compares the extracted skills with the job description to generate a match score for each candidate.

Key Features Resume Upload: Supports PDF and DOCX formats.

Information Extraction: Extracts phone numbers, email addresses, and skills from resumes.

Skill Matching: Compares the extracted skills with job description keywords.

Match Score: Generates a score to assess candidate suitability based on skill match.

Technologies Used

Flask for the web application framework.

NLP libraries for text processing, including:

pdfplumber for extracting text from PDFs.

docx2txt for extracting text from DOCX files.

spaCy for Named Entity Recognition (NER) to extract phone numbers, emails, and skills.
