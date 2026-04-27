"""pdf_reader.py — PDF text extractor using PyMuPDF"""
import fitz

def read_pdf(file):
    doc  = fitz.open(stream=file.read(), filetype="pdf")
    text = "".join(page.get_text() for page in doc)
    return text

def read_pdf_from_path(path):
    doc  = fitz.open(path)
    text = "".join(page.get_text() for page in doc)
    return text
