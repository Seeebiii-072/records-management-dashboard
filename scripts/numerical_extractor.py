import pdfplumber
import pandas as pd
import re

def extract_tables_from_pdf(path):
    tables_data = []

    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()

            for table in tables:
                if table and len(table) > 1:
                    df = pd.DataFrame(table[1:], columns=table[0])
                    df.columns = [str(c).strip() if c else f"col_{i}" for i, c in enumerate(df.columns)]
                    tables_data.append(df)

    return tables_data


def extract_numbers_from_text(text):
    numbers = re.findall(r'\b\d+\.?\d*\b', text)
    return list(map(float, numbers)) if numbers else []