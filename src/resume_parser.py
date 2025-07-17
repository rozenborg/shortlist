import os
import re
import hashlib
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
        """Extract candidate name from filename - takes first two words as Firstname Lastname"""
        # Remove file extension first
        name_without_ext = os.path.splitext(filename)[0]
        
        # Split by spaces, underscores, or other common separators
        parts = re.split(r'[_\s]+', name_without_ext)
        
        # Filter out empty parts
        parts = [part.strip() for part in parts if part.strip()]
        
        if len(parts) >= 2:
            # Return first two parts as "Firstname Lastname"
            return f"{parts[0]} {parts[1]}"
        elif len(parts) == 1:
            # Only one name part available
            return parts[0]
        else:
            return "Unknown Candidate"
    
    def generate_candidate_id(self, filename):
        """Generate a clean, consistent candidate ID"""
        # Extract name first
        name = self.extract_candidate_name(filename)
        
        # Create a simple hash of the full filename for uniqueness
        filename_hash = hashlib.md5(filename.encode()).hexdigest()[:8]
        
        # Create ID from name + hash
        name_parts = name.split()
        if len(name_parts) >= 2:
            return f"{name_parts[0]}_{name_parts[1]}_{filename_hash}"
        else:
            return f"{name_parts[0] if name_parts else 'Unknown'}_{filename_hash}"
    
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
        """Get all resume files from a folder - accepts any PDF, DOCX, or TXT file"""
        resumes = []
        if not os.path.exists(folder_path):
            return resumes
        
        for filename in os.listdir(folder_path):
            # Accept any PDF, DOCX, or TXT file (much more flexible)
            if filename.lower().endswith(('.pdf', '.docx', '.txt')):
                file_path = os.path.join(folder_path, filename)
                candidate_name = self.extract_candidate_name(filename)
                candidate_id = self.generate_candidate_id(filename)
                
                resumes.append({
                    'filename': filename,
                    'path': file_path,
                    'name': candidate_name,
                    'id': candidate_id
                })
        
        return resumes 