from io import BytesIO 
from pdfminer.high_level import extract_pages
from pdfminer.layout import LTTextContainer


def pdf_text(pdf_bytes):
    """
    extract text from the pdf_bytes and return it as a single string
    """
    text = ""
    for page_layout in extract_pages(BytesIO(pdf_bytes)):
        for element in page_layout:
            if isinstance(element, LTTextContainer):
                for text_line in element:
                    text += text_line.get_text().rstrip() + " "
    return text
