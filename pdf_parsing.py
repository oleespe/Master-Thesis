import PyPDF2
import numpy as np
import pytesseract
from pdf2image import convert_from_path
from utility import deskew


def pypdf2_parse(
        file_path: str,
        is_wikipedia: bool
) -> str:
    """
    Parse a pdf file using the PyPDF2 library.

    Parameters
    ----------
    file_path : str
        Path to a pdf file.
    is_wikipedia : bool
        Is the pdf file a wikipedia article.

    Returns
    -------
    str
        The pdf file parsed into a single string.
    """

    with open(file_path, "rb") as file:
        pdfReader = PyPDF2.PdfReader(file, strict=True)
        text = ""
        for page in pdfReader.pages:
            text += page.extract_text() + "\n\n"

        if is_wikipedia:
            # TODO: Potential extra logic for wikipedia articles.
            pass

        return text.strip()

def ocr_parse(
        file_path: str,
        is_wikipedia: bool
) -> str:
    """
    Parse a pdf file using the pytesseract library.

    Parameters
    ----------
    file_path : str
        Path to a pdf file.
    is_wikipedia : bool
        Is the pdf file a wikipedia article.

    Returns
    -------
    str
        The pdf file parsed into a single string.
    """

    pages = convert_from_path(file_path)
    text = ""
    for page in pages:
        text += pytesseract.image_to_string(deskew(np.array(page)), lang="nor")

    # Some custom logic to help with wikipedia articles 
    if is_wikipedia:
        text_split = text.split("\n")
        for i, line in enumerate(text_split):
            # This can lead to mistakes if these strings are in an article without being in the footer.
            if line == "Litteratur" or line == "Referanser" or line == "Eksterne lenker":
                text = "\n".join(text_split[:i])
                break
    return text.strip()