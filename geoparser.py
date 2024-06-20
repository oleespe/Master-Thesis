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
ADMIN1_LIST = read_admin1("es/data/admin1CodesASCII.txt")[0].to_list()
ADMIN2_LIST = read_admin2("es/data/admin2Codes.txt")[0].to_list()

def geoparse_pdf(
        file_path: str,
        pdf_parser: Callable[[str, bool], str], # pypdf2 or ocr
        is_wikipedia: bool, # Is the pdf a wikipedia article?
        pop_weight: float = 1,
        alt_names_weight: float = 1,
        co_candidates_weight: float = 1,
        co_text_weight: float = 1,
        adm1_candidates_weight: float = 1,
        adm1_text_weight: float = 1,
        co_cutoff: float = 0.05,
        adm1_cutoff: float = 0.05
) -> Dict[str, Any]:
    text = pdf_parser(file_path, is_wikipedia)
    return geoparse(text, pop_weight, alt_names_weight, co_candidates_weight, 
                    co_text_weight, adm1_candidates_weight, adm1_text_weight, co_cutoff, adm1_cutoff)

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
        pop_weight: float = 1,
        alt_names_weight: float = 1,
        co_candidates_weight: float = 1,
        co_text_weight: float = 1,
        adm1_candidates_weight: float = 1,
        adm1_text_weight: float = 1,
        co_cutoff: float = 0.05,
        adm1_cutoff: float = 0.05
) -> List[Dict[str, Any]]:
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
    for location in locations_data:
        location["candidates"] = find_candidates(es, location["entity_name"])

    inferred_countries = infer_countries(locations_data, co_candidates_weight, co_text_weight, co_cutoff)
    inferred_adm1 = infer_adm1(locations_data, es, adm1_candidates_weight, adm1_text_weight, adm1_cutoff)
    
    searched_entries = {}
    for location in locations_data:
        rank_advanced(location, locations_data, es, text, searched_entries, inferred_countries, inferred_adm1, pop_weight, alt_names_weight)
    results = handle_duplicates(entity_names, locations_data)
    return results, locations_data

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
        place_name: str
) -> List[Dict[str, Any]]:
    # Difficulties:
    # 1. We generally want to rank the highest scoring results, i.e., the ones whose name most closely resembles the retrieved place name.
    # A problem with this can be found in found entities such as "Norge", whose name in geonames is "Kingdom of Norway". 
    # And while "Norge" is a registered alternate name for "Kingdom of Norway", it will naturally have a much lower score than the ones whose name is simply "Norge".
    # This should presumably mainly be a problem for country names, as they are the ones that are mainly translated into specific languages, while smaller areas/places are not?

    # Initial baseline approach:
    # If place name is a country, filter for feature_code="PCLI"
    # Select amongst entries whose name matches perfectly in "name", "asciiname" or "alternatenames"

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
            print("Got an unexpected number of results from country query.")
        return [q_results[0].to_dict()]

    q_results = s.query(q)[0:1000].execute()

    # Only use results that match the entity name perfectly.
    results = [convert_geonames(result.to_dict()) for result in q_results if result["name"] == place_name or result["asciiname"] == place_name or place_name in result["alternatenames"]]
    if len(results) != 0:
        return results

    # If there are no candidates in geonames, search stedsnavn.
    # TODO: Best approach for handling stedsnavn results would be to convert them into the same representation as geonames, 
    # otherwise two different sets of logic will have to be produced for the scoring algorithms.
    
    # Two approaches to doing this:
    # Do the representation before indexing - Has the advantage of letting us then use the same queries on both datasets.
    # Do the representation when accessing the data - Will have to convert both datasets on use. Has the advantage of letting the individual datasets be in their rawest form.

    # A common format should look something like this:
    # {type: stedsnavn/geonames, id: "", name: "", asciiname: "", alternatenames: [""], feature_class: "", country_code: "", feature_code: "", admin1_code: "", admin2_code: "", population: "", coordinates: ""}
    # This is basically the geonames format. Feature class is maybe not necessary.
    # In short, we need names info, id, type info, hierarchy info, population, and coordinates.

    # Do we draw candidates from both datasets or only from stedsnavn if geonames returns nothing.
    # The major problem with drawing candidates from both is that we will get duplicate entries a lot of the time, i.e., we will have candidates from both geonames and stedsnavn that refer to the same geographical location.
    # Do not think there is a good way of figuring out if a geonames and stedsnavn entry refer to the same place.
    # Could potentially still run the geoparsing process with duplicate entries like this, but will maybe mess up stuff.
    # Should therefore probably only get candidates from stedsnavn when necessary.

    # TODO: Solution for this.
    # Only draw candidates when none are found from geonames.
    # Convert to geonames like format after indexing.
    s = Search(using=es, index="stedsnavn")
    q = {
        "multi_match": {
            "query": place_name,
            "fields": ["name", "alternatenames"],
            "type": "phrase"
        }
    }
    q_results = s.query(q)[0:1000].execute()
    results = [result.to_dict() for result in q_results if result["name"] == place_name or place_name in result["alternatenames"]]
    return results
    # TODO: If place name is not in "name", "asciiname" or "alternatenames", we currently return nothing.

def find_features():
    # Need to find features for retrieved location entities, as this will most likely be useful regardless of the approach taken to improve ranking algorithm.
    # 1. Some form of hierarchy. Is the place a country or adm1 etc...
    # 2. Check for adjacent words such as "gård/gården", "kirke" or "by/byen". Should also check for suffixes such as "fjellet/fjell/fjellene" or "Tunell".
    # 3. Check for adjacent words that are other entities, i.e., "Trondheim i Trøndelag"

    # Should these features be used when finding candidates or only for ranking them?
    # Some features are also probably on a document level, for example figuring out which countries are relevant.

    pass

# def find_adjacency_features(
#         location: Dict[str, Any],
#         entity_names: List[str],
#         text: str,
#         width: int = 3
# ) -> Dict[str, Any]:
#     adjacency_features = {"adj_entities": []}
#     start_window, end_window = width*50, width*50
#     if start_window > location["start_char"]: start_window = location["start_char"]
#     if end_window > len(text) - location["end_char"]: end_window = len(text) - location["end_char"]

#     prev_split = text[location["start_char"]-start_window:location["start_char"]].split()
#     next_split = text[location["end_char"]:end_window+location["end_char"]].split()
#     prev_text, next_text = [], []
#     if len(prev_split) < width: prev_text = prev_split
#     else: prev_text = prev_split[-width:]
#     if len(next_split) < width: next_text = next_split
#     else: next_text = next_split[:width]

#     for word in prev_text + next_text:
#         word = word.strip(";:-., ")
#         # TODO: This currently does not handle entities with multiple words, e.g., "Fredriksten festning".
#         # Can potentially be solved with ngrams or something similar.
#         if word in entity_names:
#             adjacency_features["adj_entities"].append(word)
        
#     return adjacency_features

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
        candidates_weight: int = 1,
        text_weight: int = 1,
        cutoff: int = 0.05
) -> Dict[str, float]:
    # TODO: Proper error handling
    if candidates_weight == 0 and text_weight == 0:
        print("Cannot have both weights equaling zero")

    candidates_mentions = {}
    text_mentions = {}
    for location in locations_data:
        candidate_countries = []
        if len(location["candidates"]) == 1:
            candidate = location["candidates"][0]
            if candidate["feature_code"] == "PCLI":
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

    # TODO: Proper error handling
    if not isclose(sum(weighted_mentions.values()), 1):
        print("Got weighted mentions not properly normalized: ", sum(weighted_mentions.values()))
    
    # Remove values below cutoff and re-normalize
    factor = 1 / sum([value for value in weighted_mentions.values() if value >= cutoff])
    weighted_mentions_cutoff = {key: value*factor for key, value in weighted_mentions.items() if value >= cutoff}

    # TODO: Proper error handling
    if not isclose(sum(weighted_mentions_cutoff.values()), 1):
        print("Got weighted mentions cutoff not properly normalized: ", sum(weighted_mentions_cutoff.values()))

    return dict(sorted(weighted_mentions_cutoff.items(), key=lambda item: item[1], reverse=True))

def infer_adm1(
        locations_data: List[Dict[str, Any]],
        es: Elasticsearch,
        candidates_weight: int = 1,
        text_weight: int = 1,
        cutoff: int = 0.05
):
    # TODO: Proper error handling
    if candidates_weight == 0 and text_weight == 0:
        print("Cannot have both weights equaling zero")
    # Count number of times an adm1 is in at least one of the candidates for a toponym
    candidate_mentions = {}
    for location in locations_data:
        candidates_adm1 = []
        for candidate in location["candidates"]:
            country_admin1 = candidate["country_code"] + "." + candidate["admin1_code"]
            if country_admin1 not in ADMIN1_LIST: continue # TODO: This will ignore any admin code not in the official geonames list. Admin codes such as historical ones.
            if country_admin1 in candidates_adm1: continue
            candidates_adm1.append(candidate["country_code"] + candidate["admin1_code"])
            if candidate["country_code"] not in candidate_mentions:
                candidate_mentions[candidate["country_code"]] = {candidate["admin1_code"]: 1}
            elif candidate["admin1_code"] not in candidate_mentions[candidate["country_code"]]:
                candidate_mentions[candidate["country_code"]][candidate["admin1_code"]] = 1
            else: candidate_mentions[candidate["country_code"]][candidate["admin1_code"]] += 1
    
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

            # TODO: Need actual error handling here. Probably set up some sort of logging.
            if len(q_results) > 1:
                print(f"Found more than one result for adm1 query. adm1: {adm1_code}, country: {country_code}")
                continue
            if len(q_results) == 0:
                print(f"Found no results for adm1 query. adm1: {adm1_code}, country: {country_code}")
                continue
            # Should only ever be one result in q_results here anyways, so it is fine to use indexing.
            adm1_mentions.append(q_results[0].to_dict())
    
    # Make a new dictionary containing all the entries in candidate mentions, but set each count to 0.
    text_mentions = deepcopy(candidate_mentions)
    for country, value in text_mentions.items():
        for adm1, _ in value.items():
            text_mentions[country][adm1] = 0
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
            weighted_mentions[country_code][admin1_code] = (candidates_weight * norm_weights_factor * (candidate_mentions[country_code][admin1_code] / total_candidate_mentions)) \
                                                        + (text_weight * norm_weights_factor * (text_mentions[country_code][admin1_code] / total_text_mentions))
    
    # Check if weighted dictionary is properly normalized
    total_sum = 0
    for _, value in weighted_mentions.items():
        total_sum += sum(value.values())
    # TODO: Proper error handling
    if not isclose(total_sum, 1):
        print("Got weighted mentions not properly normalized: ", total_sum)

    # Remove values below cutoff and re-normalize
    sum_cutoff = 0
    for _, country_dict in weighted_mentions.items():
        for _, value in country_dict.items():
            if value >= cutoff: sum_cutoff += value
    factor = 1 / sum_cutoff
    weighted_mentions_cutoff = {}
    for country_code, country_dict in weighted_mentions.items():
        for admin1_code, value in country_dict.items():
            if value >= cutoff:
                if country_code not in weighted_mentions_cutoff: weighted_mentions_cutoff[country_code] = {}
                weighted_mentions_cutoff[country_code][admin1_code] = value * factor
    # weighted_mentions_cutoff = {key: value*factor for key, value in weighted_mentions.items() if value >= cutoff}

    # Check if weighted cutoff dictionary is properly normalized
    total_sum_cutoff = 0
    for _, value in weighted_mentions_cutoff.items():
        total_sum_cutoff += sum(value.values())
    # TODO: Proper error handling
    if not isclose(total_sum, 1):
        print("Got weighted mentions cutoff not properly normalized: ", total_sum_cutoff)

    return weighted_mentions_cutoff

def get_ancestors(
        candidate: Dict[str, Any],
        es: Elasticsearch,
        searched_entries: Dict[str, Dict[str, Any]]
) -> Dict[str, Dict[str, Any]]:
    ancestors = {"country": None, "admin1": None, "admin2": None}

    feature_code = candidate['feature_code']
    country_code = candidate['country_code']
    admin1_code = candidate['admin1_code']
    admin2_code = candidate['admin2_code']

    # TODO: See if doing this actually increases performance.
    # Nullify dict for now, to deactivate the feature without having to remove the relevant code.
    searched_entries = {}
    s = Search(using=es, index="geonames_custom")
    # Search for country geonames entry.
    if feature_code != "PCLI":
        if country_code not in searched_entries:
            q = {
                "bool": {
                    "must": [
                        {"match": {"country_code": {"query": country_code}}},
                        {"match": {"feature_code": {"query": "PCLI"}}}
                    ]
                }
            }
            q_results = s.query(q).execute()

            # TODO: Need actual error handling here. Probably set up some sort of logging.
            if len(q_results) > 1:
                print(f"Found more than one result for country query. country: {country_code}")
            elif len(q_results) == 0:
                print(f"Found no results for country query. country: {country_code}")
            else:
                ancestors["country"] = q_results[0].to_dict()
                searched_entries[country_code] = q_results[0].to_dict()
        else:
            ancestors["country"] = searched_entries[country_code]

    # Search for admin1 geonames entry.
    if f"{country_code}.{admin1_code}" in ADMIN1_LIST and feature_code != "ADM1":
        if f"{country_code}.{admin1_code}" not in searched_entries:
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

            # TODO: Need actual error handling here. Probably set up some sort of logging.
            if len(q_results) > 1:
                print(f"Found more than one result for adm1 query. adm1: {admin1_code}, country: {country_code}")
            elif len(q_results) == 0:
                print(f"Found no results for adm1 query. adm1: {admin1_code}, country: {country_code}")
            else:
                ancestors["admin1"] = q_results[0].to_dict()
                searched_entries[f"{country_code}.{admin1_code}"] = q_results[0].to_dict()
        else:
            ancestors["admin1"] = searched_entries[f"{country_code}.{admin1_code}"]

    # Search for admin2 geonames entry.
    if f"{country_code}.{admin1_code}.{admin2_code}" in ADMIN2_LIST and feature_code != "ADM2":
        if f"{country_code}.{admin1_code}.{admin2_code}" not in searched_entries:
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

            # TODO: Need actual error handling here. Probably set up some sort of logging.
            if len(q_results) > 1:
                print(f"Found more than one result for adm2 query. adm2: {admin2_code}, adm1: {admin1_code}, country: {country_code}")
            elif len(q_results) == 0:
                print(f"Found no results for adm2 query. adm2: {admin2_code}, adm1: {admin1_code}, country: {country_code}")
            else:
                ancestors["admin2"] = q_results[0].to_dict()
                searched_entries[f"{country_code}.{admin1_code}.{admin2_code}"] = q_results[0].to_dict()
        else:
            ancestors["admin2"] = searched_entries[f"{country_code}.{admin1_code}.{admin2_code}"]
    return ancestors

def rank_baseline(
        candidates: List[Dict[str, Any]]
) -> Dict[str, Any]:
    # TODO: Not functional atm. Needs to sort candidates by length of alternate names, 
    # instead of just returning one.
    return
    # Initial baseline approach:
    # Select candidate with the most alternate names

    n_alt_names = 0
    index = 0
    for i, candidate in enumerate(candidates):
        if len(candidate["alternatenames"]) > n_alt_names:
            index = i
            n_alt_names = len(candidate["alternatenames"])
    
    # TODO: This returns only one select candidate atm, 
    # where a proper solution would probably return a sorted ranking amongst all candidate pairs.
    return candidates[index]

def rank_advanced(
        location: Dict[str, Any],
        locations_data: List[Dict[str, Any]],
        es: Elasticsearch,
        text: str,
        searched_entries: Dict[str, Dict[str, Any]],
        inferred_countries: Dict[str, float],
        inferred_adm1: Dict[str, Dict[str, float]],
        pop_weight: float,
        alt_names_weight: float,
):
    if len(location["candidates"]) == 0: return
    # 1. Hierarchy
    # 2. Proximity minimization?
    # Can the candidate be resolved to a hierarchy?
    # How to resolve to hierarchy?
    # Do several passes to develop a hierarchy? E.g., do one pass to find country, then another to find first-order admin levels?
    # Another approach would be to check every other candidate for other toponyms and see if a hierarchy can be established like that.

    # Bottom-up approach:
    # Look at all entities individually.
    # For each one, see if any other toponym forms a hierarchy with it.
    # Geotxt kinda does this, and assigns a score to each combination, which is then in turn used to select the best total combination.

    # Top-down approach:
    # Try and resolve top level toponyms first, such as first order administrative ones.
    # If we are confident that a toponym is i.e., an adm1, use it to resolve other toponyms in the text that belong to its hierarchy.

    # Two ways of establishing hierarchies:
    # First is to look at each toponym, and see if any ancestor's exist in the text.
    # Second is to see if any of the toponyms are part of a common hierarchy, i.e., a sort of spatial minimization.

    # Inferring geographic scope:
    # Can do this on adm1 and adm2.
    # Do a pass and look for potential adm1 mentions, as well as mentions in toponym candidates.
    # Do the same thing but for adm2.

    # Attempt1:
    # Infer relevant countries.
    # Infer relevant geographic scope.
    # Go through every toponym and look for ancestors nearby in text.
    # Calculate confidence score for each candidate based on inclusion in relevant country, relevant geographic scope, and distance to ancestor mentions.

    for candidate in location["candidates"]:
        candidate["pop_score"] = pop_score(int(candidate["population"]), pop_weight)
        candidate["alt_names_score"] = alt_names_score(len(candidate["alternatenames"]), alt_names_weight)
        candidate["country_score"] = country_score(inferred_countries, candidate["country_code"])
        candidate["admin1_score"] = admin1_score(inferred_adm1, candidate["country_code"], candidate["admin1_code"])
        candidate["hierarchy_score"] = hierarchy_score(candidate, es, location, locations_data, text, searched_entries)
        candidate["score"] = candidate["pop_score"] + candidate["alt_names_score"] + candidate["country_score"] + candidate["admin1_score"] + candidate["hierarchy_score"]
    
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
        # TODO: If the distance is ever 0, it means that a candidate shares the same name with its hierarchical ancestors.
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
        searched_entries: Dict[str, Dict[str, Any]]
) -> float:
    ancestors = get_ancestors(candidate, es, searched_entries)
    hierarchy_distances = find_hierarchy_distances(ancestors, location, locations_data, text)
    # TODO: These are random weights for now
    score = 0
    for key, value in hierarchy_distances.items():
        temp_score = 0
        if key == "admin2": temp_score = (1 / value) * 1
        if key == "admin1": temp_score = (1 / value) * 0.2
        if key == "country": temp_score = (1 / value) * 0.1
        if temp_score > score: score = temp_score
    return score

def pop_score(
        candidate_pop: int,
        weight: int
) -> float:
    if candidate_pop == 0: return 0
    scaled_pop = candidate_pop / 10000
    return logistic_function(log2(scaled_pop), 3) * weight

def alt_names_score(
        num_alt_names: int,
        weight: int
) -> float:
    if num_alt_names == 0: return 0
    return logistic_function(log2(num_alt_names), 3) * weight

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

def analyze_performance(
        file_path: str,
        locations_data: List[Dict[str, Any]]
):  
    # TODO: Needs to be fixed to actually support multiple entries of same entity.
    return
    solutions_dict = create_solutions_dict(file_path)
    
    # P0 and P1 performance
    # matching_placenames = {key: value for key, value in geoparse_result.items() if key in solutions_dict} # Place names present in both solution and found through NER
    matching_placenames = [location for location in locations_data if location["entity_name"] in solutions_dict and location["entity_name"] not in matching_placenames] # Place names present in both solution and found through NER
    excess_placenames = [key for key, _ in locations_data.items() if key not in solutions_dict] # Place names found through NER, but not in solution
    missing_placenames = [key for key, _ in solutions_dict.items() if key not in matching_placenames] # Place names present in solution but not found through NER
    print(f"Pdf place names: {len(solutions_dict)} \
          \nTotal found place names: {len(locations_data)}, excess: {excess_placenames} \
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
        locations_data: List[Dict[str, Any]]
):
    # TODO: Will not work currently as the "best_candidate" field has been removed
    return
    for location in locations_data:
        if location['best_candidate'] is None:
            print(f"{location['entity_name']} -> None")
            continue
        print(f"{location['entity_name']} -> ({location['best_candidate']['name']}, {location['best_candidate']['geonameid']}, {location['best_candidate']['country_code']}, {location['best_candidate']['coordinates']})")

def print_solutions_mappings(
        file_path: str,
        locations_data: List[Dict[str, Any]],
):
    # TODO: Needs to be fixed to actually support multiple entries of same entity.
    return
    solutions_dict = create_solutions_dict(file_path)
    matching_placenames = {key: value for key, value in locations_data.items() if key in solutions_dict}
    for key, value in solutions_dict.items():
        if key not in locations_data:
            print(f"({key}, {value}) -> None")
            continue
        print(f"({key}, {value}) -> ({matching_placenames[key]['best_candidate']['name']}, {matching_placenames[key]['best_candidate']['geonameid']})")
