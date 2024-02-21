from typing import Callable, Any, List, Dict
from elasticsearch import Elasticsearch
from elasticsearch_dsl import Search
import numpy as np
from pdf2image import convert_from_path
import spacy
import PyPDF2
import pytesseract
from helpers import *

def geoparse_pdf(
        file_path: str,
        pdf_parser: Callable[[str, bool], str], # pypdf2 or ocr
        is_wikipedia: bool # Is the pdf a wikipedia article? 
) -> Dict[str, Any]:
    text = pdf_parser(file_path, is_wikipedia)
    return geoparse(text)

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
                break
    return text.strip()

def geoparse(
        text: str
) -> Dict[str, Any]:
    data = {}
    nlp = spacy.load("nb_core_news_lg")
    doc = nlp(text)
    places = [[ent.text.strip(), ent.label_] for ent in doc.ents if ent.label_ in ["GPE", "LOC", "GPE_LOC", "GPE_ORG"]]
    for place in places:
        name = place[0]

        # TODO: This currently assumes that every mention of a place with the same name refers to the same name,
        # but you could have places with the same name in a text refer to different places. How do we handle this?
        # Check if place has already been added
        if name in data:
            continue

        # Check for names that are obviously not places
        if name.isspace() or name.islower():
            continue
        
        data[name] = {"label": place[1]}

    es = Elasticsearch("http://localhost:9200")
    s = Search(using=es, index="geonames")

    # Iterate through found place names and query ES.
    for key, _ in data.items():
        candidates = find_candidates(s, key)
        if len(candidates) == 0:
            data[key]["candidates"] = None
            data[key]["best_candidate"] = None
            continue
        data[key]["candidates"] = candidates
        data[key]["best_candidate"] = rank(candidates)
        
    return data

def find_candidates(
        s: Search,
        place_name: str
) -> Dict[str, Any]:
    # Difficulties:
    # 1. We generally want to rank the highest scoring results, i.e., the ones whose name most closely resembles the retrieved place name.
    # A problem with this can be found in found entities such as "Norge", whose name in geonames is "Kingdom of Norway". 
    # And while "Norge" is a registered alternate name for "Kingdom of Norway", it will naturally have a much lower score than the ones whose name is simply "Norge".
    # This should presumably mainly be a problem for country names, as they are the ones that are mainly translated into specific languages, while smaller areas/places are not?

    # Initial baseline approach:
    # If place name is a country, filter for feature_code="PCLI"
    # Select amongst entries whose name matches perfectly in "name", "asciiname" or "alternatenames"

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
    return [result.to_dict() for result in q_results if result["name"] == place_name or result["asciiname"] == place_name or place_name in result["alternatenames"]]

    # TODO: If place name is not in "name", "asciiname" or "alternatenames", we currently return nothing.
    # Might be worth looking into geonames "Fuzzy search" feature.

def rank(
        candidates: List[Dict[str, Any]]
) -> Dict[str, Any]:
    # Initial baseline approach:
    # Select candidate with most alternate names

    n_alt_names = 0
    index = 0
    for i, candidate in enumerate(candidates):
        if len(candidate["alternatenames"]) > n_alt_names:
            index = i
            n_alt_names = len(candidate["alternatenames"])
    
    # TODO: This returns only one select candidate atm, 
    # where a proper solution would probably return a sorted ranking amongst all candidate pairs.
    return candidates[index]

def analyze_performance(
        file_path: str,
        geoparse_result: Dict[str, Any]
):
    solutions_dict = create_solutions_dict(file_path)
    
    # P0 and P1 performance
    matching_placenames = {key: value for key, value in geoparse_result.items() if key in solutions_dict} # Place names present in both solution and found through NER
    excess_placenames = [key for key, _ in geoparse_result.items() if key not in solutions_dict] # Place names found through NER, but not in solution
    missing_placenames = [key for key, _ in solutions_dict.items() if key not in matching_placenames] # Place names present in solution but not found through NER
    print(f"Pdf place names: {len(solutions_dict)} \
          \nTotal found place names: {len(geoparse_result)}, excess: {excess_placenames} \
          \nMatching place names: {len(matching_placenames)}, missing: {missing_placenames}")
    
    # P2 performance
    missing_query_placename = []
    for key, value in matching_placenames.items():
        found_solution = False

        # Search through all candidates, and see if the correct solution is there.
        for candidate in value["candidates"]:
            if int(candidate["geonameid"]) == solutions_dict[key]:
                found_solution = True
                break

        # No candidate matching the correct geonameid
        if not found_solution:
            missing_query_placename.append(key)
                
    print(f"Solution in candidates: {len(matching_placenames) - len(missing_query_placename)}, missing: {missing_query_placename}")

    # P3 performance
    incorrect_best_candidate = [key for key, value in matching_placenames.items() if int(value["best_candidate"]["geonameid"]) != solutions_dict[key]]
    print(f"Correct best candidates: {len(matching_placenames) - len(incorrect_best_candidate)}, missing: {incorrect_best_candidate}")

def print_mappings(
        geoparse_result: Dict[str, Any]
):
    for key, value in geoparse_result.items():
        if value['best_candidate'] is None:
            print(f"{key} -> None")
            continue
        print(f"{key} -> ({value['best_candidate']['name']}, {value['best_candidate']['geonameid']}, {value['best_candidate']['country_code']}, {value['best_candidate']['coordinates']})")

def print_solutions_mappings(
        file_path: str,
        geoparse_result: Dict[str, Any],
):
    solutions_dict = create_solutions_dict(file_path)
    matching_placenames = {key: value for key, value in geoparse_result.items() if key in solutions_dict}
    for key, value in solutions_dict.items():
        if key not in geoparse_result:
            print(f"({key}, {value}) -> None")
            continue
        print(f"({key}, {value}) -> ({matching_placenames[key]['best_candidate']['name']}, {matching_placenames[key]['best_candidate']['geonameid']})")
