import PyPDF2
import numpy as np
import tesseract
from pdf2image import convert_from_path
from utility import deskew


def pypdf2_parse(
        file_path: str,
        is_wikipedia: bool # Is the pdf a wikipedia article? 
) -> str:
    with open(file_path, "rb") as file:
        pdfReader = PyPDF2.PdfReader(file, strict=True)
        text = ""
        for page in pdfReader.pages:
            text += page.extract_text() + "\n\n"
        # TODO: Potential preprocessing for pypdf
        return text.strip()

def ocr_parse(
        file_path: str,
        is_wikipedia: bool # Is the pdf a wikipedia article? 
) -> str:
    pages = convert_from_path(file_path)
    text = ""
    for page in pages:
        text += tesseract.image_to_string(deskew(np.array(page)), lang="nor")

    # Some custom logic to help with wikipedia articles 
    if is_wikipedia:
        text_split = text.split("\n")
        for i, line in enumerate(text_split):
            # This can lead to mistakes if these strings are in an article without being in the footer.
            if line == "Litteratur" or line == "Referanser" or line == "Eksterne lenker":
                text = "\n".join(text_split[:i])
                break
    return text.strip()