"""Simple PDF text extraction for chess content classification."""

import subprocess
from pathlib import Path

def extract_pdf_text(pdf_path):
    """
    Extract text from PDF using pdftotext.

    Returns:
        tuple: (text, error_message)
        - text is None if extraction failed
        - error_message explains why extraction failed
    """
    try:
        # Run pdftotext command
        result = subprocess.run(
            ['pdftotext', pdf_path, '-'],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            return None, f"pdftotext failed: {result.stderr}"

        text = result.stdout
        word_count = len(text.split())

        # Basic quality check
        if word_count < 500:
            return None, f"Insufficient text: {word_count} words"

        return text, None

    except FileNotFoundError:
        return None, "pdftotext not installed"
    except subprocess.TimeoutExpired:
        return None, "PDF extraction timeout"
    except Exception as e:
        return None, f"Extraction error: {str(e)}"