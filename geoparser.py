from typing import Callable, Any, List, Dict, Tuple
from elasticsearch import Elasticsearch
from elasticsearch_dsl import Search
from pdf2image import convert_from_path
from helpers import *
from lists import *
from math import isclose, log2
from copy import deepcopy
from typing import Counter
import spacy
import PyPDF2
import pytesseract
import numpy as np

# These are read here to increase performance.
ADMIN1_LIST = read_admin1("data/admin1CodesASCII.txt")[0].to_list()
ADMIN2_LIST = read_admin2("data/admin2Codes.txt")[0].to_list()

def geoparse_pdf(
        file_path: str,
        pdf_parser: Callable[[str, bool], str], # pypdf2 or ocr
        is_wikipedia: bool, # Is the pdf a wikipedia article?
        verbose: bool = True,
        pop_weight: float = 1,
        alt_names_weight: float = 1,
        country_weight: float = 1,
        admin1_weight: float = 1,
        hierarchy_weight: float = 1,
        co_candidates_weight: float = 1,
        co_text_weight: float = 1,
        adm1_candidates_weight: float = 1,
        adm1_text_weight: float = 1,
        country_cutoff: int = 3,
        adm1_cutoff: int = 3
) -> Dict[str, Any]:
    if verbose: print(f"Started parsing PDF with path: {file_path}")
    text = pdf_parser(file_path, is_wikipedia)
    if verbose: print(f"Finished parsing PDF")
    return geoparse(text, verbose, pop_weight, alt_names_weight, country_weight, admin1_weight, hierarchy_weight, co_candidates_weight, 
                    co_text_weight, adm1_candidates_weight, adm1_text_weight, country_cutoff, adm1_cutoff)

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
        text: str,
        verbose: bool = True,
        pop_weight: float = 1,
        alt_names_weight: float = 1,
        country_weight: float = 1,
        admin1_weight: float = 1,
        hierarchy_weight: float = 1,
        co_candidates_weight: float = 1,
        co_text_weight: float = 1,
        adm1_candidates_weight: float = 1,
        adm1_text_weight: float = 1,
        country_cutoff: int = 3,
        adm1_cutoff: int = 3
) -> List[Dict[str, Any]]:
    if verbose: print("Started geoparsing process")
    locations_data = []
    nlp = spacy.load("nb_core_news_lg")
    doc = nlp(text)
    entities = [ent for ent in doc.ents if ent.label_ in ["GPE", "LOC", "GPE_LOC", "GPE_ORG"]]
    for entity in entities:
        entity_name = entity.text.strip()

        # Check for names that are obviously not places
        if entity_name.isspace() or entity_name.islower():
            continue
        
        locations_data.append({
            "entity_name": entity_name,
            "label": entity.label_, 
            "start_char": entity.start_char, 
            "end_char": entity.end_char,
            "candidates": []
            })

    es = Elasticsearch("http://localhost:9200")
    entity_names = [location["entity_name"] for location in locations_data]

    # Iterate through found place names.
    if verbose: print("Finding candidates")
    for location in locations_data:
        location["candidates"] = find_candidates(es, location["entity_name"])
    
    inferred_countries = infer_countries(locations_data, co_candidates_weight, co_text_weight, country_cutoff)
    inferred_adm1 = infer_adm1(locations_data, es, adm1_candidates_weight, adm1_text_weight, adm1_cutoff)
    
    if verbose: print("Ranking candidates")
    for location in locations_data:
        rank(location, locations_data, es, text, inferred_countries, inferred_adm1, 
             pop_weight, alt_names_weight, country_weight, admin1_weight, hierarchy_weight)
    if verbose: print("Finished geoparsing process")
    return {
        "inferred_countries": inferred_countries, 
        "inferred_admin1": inferred_adm1, 
        "results": handle_duplicates(entity_names, locations_data)
    }


def handle_duplicates(
        entity_names: List[str],
        locations_data: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    # For duplicate entries the common heuristic is to treat them all as referring to the same toponym.
    # It is however quite useful to run the ranking process on all of them, as we want to use their location in text etc.
    # When presenting our results however, we want to return only one result per toponym.
    # To solve this, this function looks for duplicates and selects the entry that has the highest scoring top candidate, and deletes the other ones.
    
    counts = Counter(entity_names)
    locations_data_copy = deepcopy(locations_data)
    results = []
    for key, value in counts.items():
        if value == 1:
            for location in locations_data_copy:
                if location["entity_name"] == key: results.append(location)
            continue
        best_score = 0
        best_index = -1
        for index, location in enumerate(locations_data_copy):
            if location["entity_name"] != key:
                continue
            if best_index == -1:
                best_index = index
            if len(location["candidates"]) == 0:
                continue
            if best_score < location["candidates"][0]["score"]:
                best_score = location["candidates"][0]["score"]
                best_index = index
        results.append(locations_data_copy[best_index])
    return results


def find_candidates(
        es: Elasticsearch,
        place_name: str,
) -> List[Dict[str, Any]]:
    s = Search(using=es, index="geonames_custom")
    q = {
        "multi_match": {
            "query": place_name,
            "fields": ["name", "asciiname", "alternatenames"],
            "type": "phrase" # (type: phrase) ensures that the entire place name is present. Without it, a query for a place name like "Rio de Janeiro" would also return any place with "Rio" in it.
        }
    }

    if place_name in COUNTRY_NAMES:
        q_results = s.filter("term", feature_code="PCLI").query(q).execute() # Should in theory only ever return one value anyways.
        # TODO: Proper error handling
        if len(q_results) != 1:
            print(f"Warning: Got an unexpected number of results from country query: {len(q_results)}.")
        return [convert_geonames(q_results[0].to_dict())]

    q_results = s.query(q)[0:1000].execute()

    # Only use results that match the entity name perfectly.
    results = [convert_geonames(result.to_dict()) for result in q_results if result["name"] == place_name or result["asciiname"] == place_name or place_name in result["alternatenames"]]
    if len(results) != 0:
        return results
    
    s = Search(using=es, index="stedsnavn")
    q = {
        "multi_match": {
            "query": place_name,
            "fields": ["name", "alternatenames"],
            "type": "phrase"
        }
    }
    q_results = s.query(q)[0:1000].execute()
    # TODO: This currently omits results based on capitalization, e.g., query for "Odda Kommune" will result in "Odda kommune",
    # which therefore gets omitted in the below check.
    results = [convert_stedsnavn(result.to_dict()) for result in q_results if result["name"] == place_name or place_name in result["alternatenames"]]
    return results

def calculate_entity_distance(
        text: str,
        location_entity1: Dict[str, Any],
        location_entity2: Dict[str, Any]
) -> int:
    # Calculates the distance between two entities in a text

    distance = 0
    if location_entity1["start_char"] < location_entity2["end_char"]:
        distance = len(text[location_entity1["end_char"]:location_entity2["start_char"]].split())
    else:
        distance = len(text[location_entity2["end_char"]:location_entity1["start_char"]].split())
    return distance

def infer_countries(
        locations_data: List[Dict[str, Any]],
        candidates_weight: float = 1,
        text_weight: float = 1,
        cutoff: int = 3
) -> Dict[str, float]:
    if candidates_weight == 0 and text_weight == 0:
        raise ValueError("both candidates_weight and text_weight are set to 0")

    candidates_mentions = {}
    text_mentions = {}
    for location in locations_data:
        candidate_countries = []
        if len(location["candidates"]) == 1:
            candidate = location["candidates"][0]
            if candidate["feature_code"] == "PCLI" or candidate["feature_code"] == "nasjon": # candidate["feature_code"] == "nasjon" is technically redundant as these entries should always be found by GeoNames
                if candidate["country_code"] not in text_mentions:
                    text_mentions[candidate["country_code"]] = 1
                else: text_mentions[candidate["country_code"]] += 1
        for candidate in location["candidates"]:
            if candidate["country_code"] in candidate_countries: continue
            candidate_countries.append(candidate["country_code"])
            if candidate["country_code"] not in candidates_mentions:
                candidates_mentions[candidate["country_code"]] = 1
            else: candidates_mentions[candidate["country_code"]] += 1
    
    # Calculate a combined weighted sum between country mentions in text and country mentions in candidates
    weighted_mentions = {}
    total_mentions_candidates = sum(candidates_mentions.values())
    total_mentions_text = sum(text_mentions.values())
    norm_weights_factor = 1 / (candidates_weight + text_weight)
    for key, _ in candidates_mentions.items():
        if not text_mentions:
            weighted_mentions[key] = candidates_mentions[key] / total_mentions_candidates
            continue
        if key not in text_mentions:
            weighted_mentions[key] = candidates_weight * norm_weights_factor * (candidates_mentions[key] / total_mentions_candidates)
        else:
            weighted_mentions[key] = (candidates_weight * norm_weights_factor * (candidates_mentions[key] / total_mentions_candidates)) + (text_weight * norm_weights_factor * (text_mentions[key] / total_mentions_text))

    if not isclose(sum(weighted_mentions.values()), 1):
        print("Warning: Got country weighted mentions not properly normalized: ", sum(weighted_mentions.values()))
    
    # Select top n countries.
    top_n_list = sorted(zip(weighted_mentions.values(), weighted_mentions.keys()), reverse=True)[:cutoff]
    top_n = {code: value for value, code in top_n_list}
    factor = 1 / sum([value for value, _ in top_n_list])
    top_n_refactored = {code: value * factor for code, value in top_n.items()}
    total_sum_cutoff = sum(top_n_refactored.values())
    if not isclose(total_sum_cutoff, 1):
        print("Warning: Got country weighted mentions cutoff not properly normalized: ", top_n_refactored)
    
    return top_n_refactored

def infer_adm1(
        locations_data: List[Dict[str, Any]],
        es: Elasticsearch,
        candidates_weight: float = 1,
        text_weight: float = 1,
        cutoff: int = 3
):
    # TODO: Proper error handling
    if candidates_weight == 0 and text_weight == 0:
        raise ValueError("both candidates_weight and text_weight are set to 0")
    
    # Count number of times an adm1 is in at least one of the candidates for a toponym
    candidate_mentions = {}
    for location in locations_data:
        candidates_adm1 = []
        for candidate in location["candidates"]:
            country_admin1 = candidate["country_code"] + "." + candidate["admin1_code"]
            if country_admin1 not in ADMIN1_LIST: continue # TODO: This will ignore any admin code not in the official geonames list. Admin codes such as historical ones.
            if country_admin1 in candidates_adm1: continue
            candidates_adm1.append(country_admin1)
            if candidate["country_code"] not in candidate_mentions:
                candidate_mentions[candidate["country_code"]] = {candidate["admin1_code"]: 1}
            elif candidate["admin1_code"] not in candidate_mentions[candidate["country_code"]]:
                candidate_mentions[candidate["country_code"]][candidate["admin1_code"]] = 1
            else: candidate_mentions[candidate["country_code"]][candidate["admin1_code"]] += 1
    
    # TODO: The statement below might not be true if the NER step fails to find the in text mention?

    # For all adm1 mentions retrieved in the previous process, find their entry in Elasticsearch.
    # This should in theory also always include any of the potential adm1 entities found in the text,
    # as it should then be one of the results counted from the previous process.
    adm1_mentions = []
    for country_code, value in candidate_mentions.items():
        for adm1_code, _ in value.items():
            s = Search(using=es, index="geonames_custom")
            q = {
                "bool": {
                    "must": [
                        {"match": {"country_code": {"query": country_code}}},
                        {"match": {"admin1_code": {"query": adm1_code}}},
                        {"match": {"feature_code": {"query": "ADM1"}}},
                        # {"query_string": {"query": "(ADM1) OR (ADM1H)", "fields": ["feature_code"]}}
                    ]
                }
            }
            q_results = s.query(q).execute()

            if len(q_results) > 1:
                print(f"Warning: Found more than one result for adm1 query. adm1: {adm1_code}, country: {country_code}")
                continue
            if len(q_results) == 0:
                print(f"Warning: Found no results for adm1 query. adm1: {adm1_code}, country: {country_code}")
                continue
            # Should only ever be one result in q_results here anyways, so it is fine to use indexing.
            adm1_mentions.append(q_results[0].to_dict())
    
    # Make a new dictionary containing all the entries in candidate mentions, but set each count to 0.
    text_mentions = deepcopy(candidate_mentions)
    for country, value in text_mentions.items():
        for adm1, _ in value.items():
            text_mentions[country][adm1] = 0

    
    # Count the number of times an admin1 is mentioned in the text.
    for location in locations_data:
        for adm1_mention in adm1_mentions:
            if location["entity_name"] == adm1_mention["name"] or location["entity_name"] == adm1_mention["asciiname"] or location["entity_name"] in adm1_mention["alternatenames"]:
                text_mentions[adm1_mention["country_code"]][adm1_mention["admin1_code"]] += 1
    
    # Calculate total number of mentions
    weighted_mentions = {}
    total_candidate_mentions = 0
    total_text_mentions = 0
    norm_weights_factor = 1 / (candidates_weight + text_weight) 
    for _, value in candidate_mentions.items():
        total_candidate_mentions += sum(value.values())
    for _, value in text_mentions.items():
        total_text_mentions += sum(value.values())

    # Divide each mention by total, so as to get weighted count.
    for country_code, country_dict in candidate_mentions.items():
        for admin1_code, _ in country_dict.items():
            if country_code not in weighted_mentions: weighted_mentions[country_code] = {}
            if total_text_mentions == 0: 
                weighted_mentions[country_code][admin1_code] = candidate_mentions[country_code][admin1_code] / total_candidate_mentions
                continue
            candidates_weighted_mentions = candidates_weight * norm_weights_factor * (candidate_mentions[country_code][admin1_code] / total_candidate_mentions) if total_candidate_mentions != 0 else 0
            text_weighted_mentions = text_weight * norm_weights_factor * (text_mentions[country_code][admin1_code] / total_text_mentions) if total_text_mentions != 0 else 0
            weighted_mentions[country_code][admin1_code] = candidates_weighted_mentions + text_weighted_mentions
    
    # Check if weighted dictionary is properly normalized
    total_sum = 0
    for _, value in weighted_mentions.items():
        total_sum += sum(value.values())
    if not isclose(total_sum, 1):
        print("Warning: Got admin1 weighted mentions not properly normalized: ", total_sum)

    simplified_weighted_mentions = {} # Instead of {country_code: {admin_code: value}} we have {country_code.admin_code: value}
    for country_code, country_dict in weighted_mentions.items():
        for admin1_code, value in country_dict.items():
            simplified_weighted_mentions[f"{country_code}.{admin1_code}"] = value
    top_n_list = sorted(zip(simplified_weighted_mentions.values(), simplified_weighted_mentions.keys()), reverse=True)[:cutoff]
    top_n = {}
    for value, code in top_n_list:
        code_split = code.split(".")
        country_code = code_split[0]
        admin1_code = code_split[1]
        if country_code not in top_n: top_n[country_code] = {}
        top_n[country_code][admin1_code] = value

    factor = 1 / sum([value for value, _ in top_n_list])
    top_n_refactored = {}
    for country_code, country_dict in top_n.items():
        for admin1_code, value in country_dict.items():
            if country_code not in top_n_refactored: top_n_refactored[country_code] = {}
            top_n_refactored[country_code][admin1_code] = value * factor

    total_sum_cutoff = 0
    for _, value in top_n_refactored.items():
        total_sum_cutoff += sum(value.values())
    if not isclose(total_sum_cutoff, 1):
        print("Warning: Got admin1 weighted mentions cutoff not properly normalized: ", top_n_refactored)
    return top_n_refactored

def get_ancestors(
        candidate: Dict[str, Any],
        es: Elasticsearch,
) -> Dict[str, Dict[str, Any]]:
    ancestors = {"country": None, "admin1": None, "admin2": None}

    feature_code = candidate['feature_code']
    country_code = candidate['country_code']
    admin1_code = candidate['admin1_code']
    admin2_code = candidate['admin2_code']

    # TODO: See if doing this actually increases performance.
    # Nullify dict for now, to deactivate the feature without having to remove the relevant code.
    s = Search(using=es, index="geonames_custom")
    # Search for country geonames entry.
    if not (feature_code == "PCLI" or feature_code == "nasjon"):
        q = {
            "bool": {
                "must": [
                    {"match": {"country_code": {"query": country_code}}},
                    {"match": {"feature_code": {"query": "PCLI"}}}
                ]
            }
        }
        q_results = s.query(q).execute()

        if len(q_results) > 1:
            print(f"Warning: Found more than one result for country query. country: {country_code}")
        elif len(q_results) == 0:
            print(f"Warning: Found no results for country query. country: {country_code}")
        else:
            ancestors["country"] = q_results[0].to_dict()

    # Search for admin1 geonames entry.
    if f"{country_code}.{admin1_code}" in ADMIN1_LIST and not (feature_code == "ADM1" or feature_code == "fylke"):
        q = {
            "bool": {
                "must": [
                    {"match": {"country_code": {"query": country_code}}},
                    {"match": {"admin1_code": {"query": admin1_code}}},
                    {"match": {"feature_code": {"query": "ADM1"}}}
                ]
            }
        }
        q_results = s.query(q).execute()

        if len(q_results) > 1:
            print(f"Warning: Found more than one result for adm1 query. adm1: {admin1_code}, country: {country_code}")
        elif len(q_results) == 0:
            print(f"Warning: Found no results for adm1 query. adm1: {admin1_code}, country: {country_code}")
        else:
            ancestors["admin1"] = q_results[0].to_dict()

    # Search for admin2 geonames entry.
    if f"{country_code}.{admin1_code}.{admin2_code}" in ADMIN2_LIST and not (feature_code == "ADM2" or feature_code == "kommune"):
        q = {
            "bool": {
                "must": [
                    {"match": {"country_code": {"query": country_code}}},
                    {"match": {"admin1_code": {"query": admin1_code}}},
                    {"match": {"admin2_code": {"query": admin2_code}}},
                    {"match": {"feature_code": {"query": "ADM2"}}}
                ]
            }
        }
        q_results = s.query(q).execute()

        if len(q_results) > 1:
            print(f"Warning: Found more than one result for adm2 query. adm2: {admin2_code}, adm1: {admin1_code}, country: {country_code}")
        elif len(q_results) == 0:
            print(f"Warning: Found no results for adm2 query. adm2: {admin2_code}, adm1: {admin1_code}, country: {country_code}")
        else:
            ancestors["admin2"] = q_results[0].to_dict()

    return ancestors

def rank(
        location: Dict[str, Any],
        locations_data: List[Dict[str, Any]],
        es: Elasticsearch,
        text: str,
        inferred_countries: Dict[str, float],
        inferred_adm1: Dict[str, Dict[str, float]],
        pop_weight: float,
        alt_names_weight: float,
        country_weight: float = 1,
        admin1_weight: float = 1,
        hierarchy_weight: float = 1
):
    if len(location["candidates"]) == 0: return

    for candidate in location["candidates"]:
        norm_factor = 1 / (pop_weight + alt_names_weight + country_weight + admin1_weight + hierarchy_weight)
        candidate["pop_score"] = pop_score(int(candidate["population"]))
        candidate["alt_names_score"] = alt_names_score(len(candidate["alternatenames"]))
        candidate["country_score"] = country_score(inferred_countries, candidate["country_code"])
        candidate["admin1_score"] = admin1_score(inferred_adm1, candidate["country_code"], candidate["admin1_code"])
        candidate["hierarchy_score"] = hierarchy_score(candidate, es, location, locations_data, text)
        candidate["score"] = \
                (candidate["pop_score"] * pop_weight) + \
                (candidate["alt_names_score"] * alt_names_weight) + \
                (candidate["country_score"] * country_weight) + \
                (candidate["admin1_score"] * admin1_weight) + \
                (candidate["hierarchy_score"] * hierarchy_weight)
        candidate["score"] = (candidate["score"] * norm_factor)**(1/4)
    
    # TODO: Should try and implement an algorithm that tries to find hierarchical pairs.
    # For instance, in the text "Jeg reiste fra Bergen til Oslo", it determines Bergen as Bergen County, USA, and Oslo as Oslo, Norway.
    # In cases like these, it should recognize that these can both potentially belong to Norway, 
    # and therefore boost their corresponding scores accordingly.

    def sort(candidate):
        return candidate["score"]
    location["candidates"] = sorted(location["candidates"], key=sort, reverse=True)

def find_hierarchy_distances(
        ancestors: Dict[str, Dict[str, Any]],
        location: Dict[str, Any],
        locations_data: List[Dict[str, Any]],
        text: str
):
    hierarchy_distances = {}
    for key, value in ancestors.items():
        if value is None:
            continue
        for entry in locations_data:
            if entry["entity_name"] == value["name"] or entry["entity_name"] == value["asciiname"] or entry["entity_name"] in value["alternatenames"]:
                distance = calculate_entity_distance(text, location, entry)
                if key not in hierarchy_distances: hierarchy_distances[key] = distance
                elif distance < hierarchy_distances[key]: hierarchy_distances[key] = distance
    
    hierarchy_distances_copy = deepcopy(hierarchy_distances)
    for key, value in hierarchy_distances.items():
        # If the distance is ever 0, it means that a candidate shares the same name with its hierarchical ancestors.
        # For instance, the entity Trøndelag will return the candidate Trøndelag with feature_code RGN, as being part of the admin1 division Trøndelag.
        # Calculating the distance for these types of entries will always return 0.
        # For now we will simply remove these.
        if value == 0: del hierarchy_distances_copy[key]
    return hierarchy_distances_copy

def hierarchy_score(
        candidate: Dict[str, Any],
        es: Elasticsearch,
        location: Dict[str, Any],
        locations_data: List[Dict[str, Any]],
        text: str,
) -> float:
    ancestors = get_ancestors(candidate, es)
    hierarchy_distances = find_hierarchy_distances(ancestors, location, locations_data, text)
    score = 0
    for key, value in hierarchy_distances.items():
        temp_score = 0
        if key == "admin2": temp_score = (1 / log2(value+1)) * 1
        if key == "admin1": temp_score = (1 / log2(value+1)) * 0.5
        if key == "country": temp_score = (1 / log2(value+1)) * 0.25
        if temp_score > score: score = temp_score
    return score

def pop_score(
        candidate_pop: int
) -> float:
    if candidate_pop == 0: return 0
    scaled_pop = candidate_pop / 10000
    return logistic_function(log2(scaled_pop), 3)

def alt_names_score(
        num_alt_names: int
) -> float:
    if num_alt_names == 0: return 0
    return logistic_function(log2(num_alt_names), 3)

def country_score(
        inferred_countries: Dict[str, float],
        country_code: str
) -> float:
    if country_code not in inferred_countries: return 0
    return inferred_countries[country_code]

def admin1_score(
        inferred_adm1: Dict[str, Dict[str, float]],
        country_code: str,
        admin1_code: str
) -> float:
    if country_code not in inferred_adm1: return 0
    if admin1_code not in inferred_adm1[country_code]: return 0
    return inferred_adm1[country_code][admin1_code]
