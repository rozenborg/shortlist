import os
import re
from PyPDF2 import PdfReader
from docx import Document

class ResumeParser:
    def __init__(self):
        self.supported_formats = ['.pdf', '.docx', '.txt']
    
    def extract_text_from_pdf(self, file_path):
        """Extract text from PDF file"""
        try:
            reader = PdfReader(file_path)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
            return text.strip()
        except Exception as e:
            print(f"Error reading PDF {file_path}: {e}")
            return ""
    
    def extract_text_from_docx(self, file_path):
        """Extract text from DOCX file"""
        try:
            doc = Document(file_path)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text.strip()
        except Exception as e:
            print(f"Error reading DOCX {file_path}: {e}")
            return ""
    
    def extract_candidate_name(self, filename):
        """Extract candidate name from filename pattern"""
        # Pattern: "Name LastName ID RESUME.ext"
        match = re.match(r'^(.+?)\s+\w+\s+RESUME\.(pdf|docx|txt)$', filename, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return "Unknown Candidate"
    
    def parse_resume(self, file_path):
        """Parse resume and return extracted text"""
        _, ext = os.path.splitext(file_path.lower())
        
        if ext == '.pdf':
            return self.extract_text_from_pdf(file_path)
        elif ext == '.docx':
            return self.extract_text_from_docx(file_path)
        elif ext == '.txt':
            # For testing with text files
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        else:
            raise ValueError(f"Unsupported file format: {ext}")
    
    def get_all_resumes(self, folder_path):
        """Get all resume files from a folder"""
        resumes = []
        if not os.path.exists(folder_path):
            return resumes
        
        for filename in os.listdir(folder_path):
            if (filename.upper().endswith('RESUME.PDF') or 
                filename.upper().endswith('RESUME.DOCX') or 
                filename.upper().endswith('RESUME.TXT')):
                file_path = os.path.join(folder_path, filename)
                candidate_name = self.extract_candidate_name(filename)
                resumes.append({
                    'filename': filename,
                    'path': file_path,
                    'name': candidate_name,
                    'id': filename.replace(' ', '_').replace('.', '_')
                })
        
        return resumes 