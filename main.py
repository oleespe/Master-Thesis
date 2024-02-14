from typing import Callable, Any
from elasticsearch import Elasticsearch
import numpy as np
from pdf2image import convert_from_path
import spacy
import PyPDF2
import pandas as pd
import pytesseract
import sys
from helpers import deskew

def geoparse_pdf(
        file_path: str,
        pdf_parser: Callable[[str], str], # pypdf2 or ocr
        is_wikipedia: bool # Is the pdf a wikipedia article? 
) -> None:
    text = pdf_parser(file_path, is_wikipedia)
    # print(text)
    geoparse(text)

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
        text += pytesseract.image_to_string(deskew(np.array(page)), lang="nor")

    # Some custom logic to help with wikipedia articles 
    if is_wikipedia:
        text_split = text.split("\n")
        for i, line in enumerate(text_split):
            # TODO: This can lead to mistakes if these strings are in an article without being in the footer.
            if line == "Litteratur" or line == "Referanser" or line == "Eksterne lenker":
                text = "\n".join(text_split[:i])
    return text.strip()

def geoparse(
        text: str
) -> None:
    df = pd.DataFrame([], columns=["name", "label"])
    nlp = spacy.load("nb_core_news_lg")
    doc = nlp(text)
    places = [[ent.text.strip(), ent.label_] for ent in doc.ents if ent.label_ in ["GPE", "LOC", "GPE_LOC", "GPE_ORG"]]
    for place in places:
        name = place[0]

        # Check for names that are obviously not places
        if not name.isalpha() or name.isspace() or name.islower():
            continue
        
        # Check if place has already been added
        if name in df["name"].tolist():
            continue 
        
        df.loc[len(df.index)] = place

    es = Elasticsearch("http://localhost:9200")

    # Iterate through found place names and query ES.
    # for _, row in df.iterrows():
    #     query(es, row["name"])
    print(df)

def query(
        es: Elasticsearch,
        placename: str
) -> None:
    search = es.search(index="geonames", query={"match": {"name": placename}})
    for result in search["hits"]["hits"]:
        print(result["_source"])
        pass

if __name__ == "__main__":
    file_path = str(sys.argv[1]) 
    geoparse_pdf(file_path, pdf_parser=ocr_parse, is_wikipedia=True)
