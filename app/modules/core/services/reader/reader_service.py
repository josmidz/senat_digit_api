

from fastapi import HTTPException
from docx import Document
import PyPDF2

class ReaderService:
    def read_pdf(file_path: str) -> str:
        content = ""
        try:
            with open(file_path, "rb") as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    content += page.extract_text() + "\n"
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail="PDF file not found")
        except Exception as e:
            print(e)
            raise HTTPException(status_code=500, detail=f"Error reading PDF file: {str(e)}")
        return content

    def read_docx(file_path: str) -> str:
        content = ""
        try:
            doc = Document(file_path)
            for paragraph in doc.paragraphs:
                content += paragraph.text + "\n"
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail="DOCX file not found")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error reading DOCX file: {str(e)}")
        return content

    def read_txt(file_path: str) -> str:
        content = ""
        try:
            with open(file_path, "r") as file:
                content = file.read()
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail="TXT file not found")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error reading TXT file: {str(e)}")
        return content