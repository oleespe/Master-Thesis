from typing import Callable, Any, List, Dict
from elasticsearch import Elasticsearch
from elasticsearch_dsl import Search
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
        pdf_parser: Callable[[str, bool], str], # pypdf2 or ocr
        is_wikipedia: bool # Is the pdf a wikipedia article? 
) -> None:
    text = pdf_parser(file_path, is_wikipedia)
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
    data = {}
    nlp = spacy.load("nb_core_news_lg")
    doc = nlp(text)
    places = [[ent.text.strip(), ent.label_] for ent in doc.ents if ent.label_ in ["GPE", "LOC", "GPE_LOC", "GPE_ORG"]]
    for place in places:
        name = place[0]

        # Check if place has already been added
        if name in data:
            continue

        # Check for names that are obviously not places
        if not name.isalpha() or name.isspace() or name.islower():
            continue
        
        data[name] = {"label": place[1]}

    es = Elasticsearch("http://localhost:9200")
    s = Search(using=es, index="geonames")

    # Iterate through found place names and query ES.
    for key, _ in data.items():
        results = query(s, key)
        if len(results) == 0:
            data[key]["candidates"] = None
            data[key]["best_candidate"] = None
            continue
        data[key]["candidates"] = results
        data[key]["best_candidate"] = rank(results)

    # for key, value in data.items():
    #     print(key)
    #     print(value["best_candidate"])
    #     for candidate in value["candidates"]:
    #         print(candidate)

def query(
        s: Search,
        place_name: str
) -> None:
    # Difficulties:
    # 1. We generally want to rank the highest scoring results, i.e., the ones whose name most closely resembles the retrieved place name.
    # A problem with this can be found in found entities such as "Norge", whose name in geonames is "Kingdom of Norway". 
    # And while "Norge" is a registered alternate name for "Kingdom of Norway", it will naturally have a much lower score than the ones whose name is simply "Norge".
    # This should presumably mainly be a problem for country names, as they are the ones that are mainly translated into specific languages, while smaller areas/places are not?

    # Initial baseline approach:
    # If place name is a country, filter for feature_code="PCLI"
    # Select amongst entries whose name matches perfectly.
    # Otherwise return every result.

    q = {
        "multi_match": {
            "query": place_name,
            "fields": ["name", "asciiname", "alternatenames"]
        }
    }

    # TODO: This needs to be replaced with a proper solution.
    if place_name == "Sverige" or place_name == "Norge":
        q_results = s.filter("term", feature_code="PCLI").query(q)[0:5].execute() # Should in theory only ever return one value anyways?
        return [q_results.to_dict()["hits"]["hits"][0]["_source"]]

    q_results = s.query(q)[0:100].execute()
    results = [result.to_dict() for result in q_results if result["name"] == place_name]
    if len(results) == 0: [result.to_dict() for result in q_results] # No search results match the place name perfectly, add everything for now.

    return results

def rank(
        candidates: List[Dict[str, Any]]
) -> Dict[str, Any]:
    # Initial baseline approach:
    # Select country with most alternate names

    n_alt_names = 0
    index = 0
    for i, candidate in enumerate(candidates):
        if len(candidate["alternatenames"]) > n_alt_names:
            index = i
    
    # TODO: This returns only one select candidate atm, 
    # where a proper solution would probably return a sorted ranking amongst all candidate pairs.
    return candidates[index]


if __name__ == "__main__":
    file_path = str(sys.argv[1])
    geoparse_pdf(file_path, pdf_parser=ocr_parse, is_wikipedia=True)
