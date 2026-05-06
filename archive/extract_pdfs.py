import sys
try:
    from pypdf import PdfReader
except ImportError:
    print("pypdf not installed")
    sys.exit(1)

def extract_pdf(pdf_path, txt_path):
    try:
        reader = PdfReader(pdf_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"Successfully extracted {pdf_path} to {txt_path}")
    except Exception as e:
        print(f"Error processing {pdf_path}: {e}")

if __name__ == "__main__":
    extract_pdf("AI407 Mid Exam Formatted (1).pdf", "exam_guidelines.txt")
    extract_pdf("Lab_03 (1).pdf", "lab3_guidelines.txt")
