import spacy
from typing import Callable, Any, List, Dict, Tuple
from elasticsearch import Elasticsearch
from elasticsearch_dsl import Search
from utility import *
from lists import *
from math import isclose, log2
from copy import deepcopy
from typing import Counter

# These are read here to increase performance.
ADMIN1_LIST = read_admin1("data/admin1CodesASCII.txt")[0].to_list()
ADMIN2_LIST = read_admin2("data/admin2Codes.txt")[0].to_list()

def geoparse_pdf(
        file_path: str,
        pdf_parser: Callable[[str, bool], str],
        is_wikipedia: bool, # Is the pdf a wikipedia article?
        mute_output: bool = False,
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
    """
    Geoparse a pdf file. This function is essentially a wrapper for geoparse(), but takes a pdf parser as input.

    Parameters
    ----------
    file_path : str
        File path to pdf file.
    pdf_parser : Callable[[str, bool], str]
        A pdf parser, that takes a file path as input, and outputs a raw string of text.
        There are two available pdf parsers implemented in this solution: ocr_parse() and pypdf2_parse().
    is_wikipedia : bool
        If the pdf file is from a wikipedia article.
        Makes the pdf parsers perform extra actions to remove clutter from the articles that might otherwise reduce geoparsing performance.
    mute_output : bool
        Mute all text status output of the geoparser.
    pop_weight : float
        How much a candidate's population size should contribute to the overall score.
    alt_names_weight : float
        How much a candidate's number of alternate names should contribute to the overall score.
    country_weight : float
        How much the inferred countries should affect the overall score.
    admin1_weight : float
        How much the inferred first order administrative divisions should affect the overall score.
    hierarchy_weight : float
        How much the text mentions of a candidate's geographical ancestors should contribute to the overall score.
    co_candidates_weight : float
        How much candidate mentions should contribute when inferring countries.
    co_text_weight : float
        How much text mentions should contribute when inferring countries.
    adm1_candidates_weight : float
        How much candidate mentions should contribute when inferring first order administrative divisions.
    adm1_text_weight : float
        How much text mentions should contribute when inferring first order administrative divisions.
    country_cutoff : int
        The number of countries inferred.
    adm1_cutoff : int
        The number of first order administrative divisions inferred.
    
    Returns
    -------
    Dict[str, Any]
        A dictionary containing the inferred countries and first order administrative divisions, as well as the actual geoparsing results.
    """

    if not mute_output: print(f"Started parsing PDF with path: {file_path}")
    text = pdf_parser(file_path, is_wikipedia)
    if not mute_output: print(f"Finished parsing PDF")
    return geoparse(text, mute_output, pop_weight, alt_names_weight, country_weight, admin1_weight, hierarchy_weight, co_candidates_weight, 
                    co_text_weight, adm1_candidates_weight, adm1_text_weight, country_cutoff, adm1_cutoff)

def geoparse(
        text: str,
        mute_output: bool = False,
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
    """
    The main geoparsing function. It will go through the provided text, and return all toponyms it identifies in the text.

    Parameters
    ----------
    text : str
        The text that should be geoparsed.
    mute_output : bool
        Mute all text status output of the geoparser.
    pop_weight : float
        How much a candidate's population size should contribute to the overall score.
    alt_names_weight : float
        How much a candidate's number of alternate names should contribute to the overall score.
    country_weight : float
        How much the inferred countries should affect the overall score.
    admin1_weight : float
        How much the inferred first order administrative divisions should affect the overall score.
    hierarchy_weight : float
        How much the text mentions of a candidate's geographical ancestors should contribute to the overall score.
    co_candidates_weight : float
        How much candidate mentions should contribute when inferring countries.
    co_text_weight : float
        How much text mentions should contribute when inferring countries.
    adm1_candidates_weight : float
        How much candidate mentions should contribute when inferring first order administrative divisions.
    adm1_text_weight : float
        How much text mentions should contribute when inferring first order administrative divisions.
    country_cutoff : int
        The number of countries inferred.
    adm1_cutoff : int
        The number of first order administrative divisions inferred.
    
    Returns
    -------
    Dict[str, Any]
        A dictionary containing the inferred countries and first order administrative divisions, as well as the actual geoparsing results.
    """
    
    if not mute_output: print("Started geoparsing")
    locations_data = []
    nlp = spacy.load("nb_core_news_lg")
    doc = nlp(text)
    entities = [ent for ent in doc.ents if ent.label_ in ["GPE", "LOC", "GPE_LOC", "GPE_ORG"]]
    for entity in entities:
        entity_name = entity.text.strip()

        # Check for names that are obviously not places.
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

    if not mute_output: print("Finding candidates")
    for location in locations_data:
        location["candidates"] = __find_candidates(es, location["entity_name"], mute_output)
    
    inferred_countries = __infer_countries(locations_data, mute_output, co_candidates_weight, co_text_weight, country_cutoff)
    inferred_adm1 = __infer_adm1(locations_data, es, mute_output, adm1_candidates_weight, adm1_text_weight, adm1_cutoff)
    
    if not mute_output: print("Ranking candidates")
    for location in locations_data:
        __rank(location, locations_data, es, text, inferred_countries, inferred_adm1, mute_output,
             pop_weight, alt_names_weight, country_weight, admin1_weight, hierarchy_weight)
    if not mute_output: print("Finished geoparsing")
    return {
        "inferred_countries": inferred_countries, 
        "inferred_admin1": inferred_adm1, 
        "results": __handle_duplicates(entity_names, locations_data)
    }

def __handle_duplicates(
        entity_names: List[str],
        locations_data: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Handle duplicate entries from the geoparser. The common heuristic is to treat all same named location mentions as referring to the same toponym.
    This function looks for duplicates and selects the entry that has the highest scoring top candidate, and deletes the other ones.

    Parameters
    ----------
    entity_names : List[str]
        All location entities found in the text during the toponym recognition step.
    locations_data : List[Dict[str, Any]]
        The results from geoparsing.
    
    Returns
    -------
    List[Dict[str, Any]]
        The same results as in the input, except with all duplicates resolved.
    """
    
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

def __find_candidates(
        es: Elasticsearch,
        place_name: str,
        mute_output: bool = False
) -> List[Dict[str, Any]]:
    """
    Finds toponym candidates from either GeoNames or Stedsnavn for a given location mention.
    Will prioritize GeoNames, and only uses Stedsnavn if no results are returned from the former.
    Discards any results where the query string does not match a toponym's name, ascii name, or one of its alternate names.

    Parameters
    ----------
    es : Elasticsearch
        Elasticsearch instance. Must have the indexes "geonames_custom" and "stedsnavn" to retrieve candidates from the respective datasets.
    place_name : str
        The place name string that the datasets should be queried on.
    mute_output : bool
        Mute all text status output.
    
    Returns
    -------
    List[Dict[str, Any]]
        A list of candidates for the given place name.
    """

    s = Search(using=es, index="geonames_custom")

    # (type: phrase) ensures that the entire place name is present. Without it, a query for a place name like "Rio de Janeiro" would also return any place with "Rio" in it.
    q = {
        "multi_match": {
            "query": place_name,
            "fields": ["name", "asciiname", "alternatenames"],
            "type": "phrase"
        }
    }

    if place_name in COUNTRY_NAMES:
        q_results = s.filter("term", feature_code="PCLI").query(q).execute() # Should in theory only ever return one value anyways.
        # TODO: Proper error handling
        if len(q_results) != 1:
            if not mute_output: print(f"Warning: Got an unexpected number of results from country query: {len(q_results)}.")
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

def __calculate_entity_distance(
        text: str,
        location_entity1: Dict[str, Any],
        location_entity2: Dict[str, Any]
) -> int:
    """
    Calculate the distance in text between two location entities that are found through NER.

    Parameters
    ----------
    text : str
        The text where the entities are located.
    location_entity1 : Dict[str, Any]
        The first entity.
    location_entity2 : Dict[str, Any]
        The second entity.
    
    Returns
    -------
    int
        The distance between the two entities.
    """

    distance = 0
    if location_entity1["start_char"] < location_entity2["end_char"]:
        distance = len(text[location_entity1["end_char"]:location_entity2["start_char"]].split())
    else:
        distance = len(text[location_entity2["end_char"]:location_entity1["start_char"]].split())
    return distance

def __infer_countries(
        locations_data: List[Dict[str, Any]],
        mute_output: bool = False,
        candidates_weight: float = 1,
        text_weight: float = 1,
        cutoff: int = 3
) -> Dict[str, float]:
    """
    Infers countries of relevance. It uses the location entities that are found in the toponym recognition step, as well as the candidates retrieved for them.
    The function counts the number of text mentions for different countries, as well as how representative they are amongst the various candidates.

    Parameters
    ----------
    locations_data : List[Dict[str, Any]]
        Data on every location entity, including its name, as well as the candidates that have been found for it.
    mute_output : bool
        Mute all text status output.
    candidates_weight : float
        How much should a country's representation amongst candidates count towards the overall score.
    text_weight : float
        How much should a country's text mentions count towards the overall score.
    cutoff : int
        The number of inferred countries that should be returned.

    Returns
    -------
    Dict[str, float]
        Dictionary with country codes as keys, and their calculated relevance as value.
    """

    if candidates_weight == 0 and text_weight == 0:
        raise ValueError("both candidates_weight and text_weight are set to 0")

    candidates_mentions = {}
    text_mentions = {}
    for location in locations_data:
        candidate_countries = []
        if len(location["candidates"]) == 1:
            candidate = location["candidates"][0]

            # candidate["feature_code"] == "nasjon" is technically redundant as these entries should always be found by GeoNames
            if candidate["feature_code"] == "PCLI" or candidate["feature_code"] == "nasjon":
                if candidate["country_code"] not in text_mentions:
                    text_mentions[candidate["country_code"]] = 1
                else: text_mentions[candidate["country_code"]] += 1
        for candidate in location["candidates"]:
            if candidate["country_code"] in candidate_countries: continue
            candidate_countries.append(candidate["country_code"])
            if candidate["country_code"] not in candidates_mentions:
                candidates_mentions[candidate["country_code"]] = 1
            else: candidates_mentions[candidate["country_code"]] += 1
    
    # Calculate a combined weighted sum between country mentions in text and country mentions in candidates.
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
        if not mute_output: print("Warning: Got country weighted mentions not properly normalized: ", sum(weighted_mentions.values()))
    
    # Select top n countries.
    top_n_list = sorted(zip(weighted_mentions.values(), weighted_mentions.keys()), reverse=True)[:cutoff]
    top_n = {code: value for value, code in top_n_list}
    factor = 1 / sum([value for value, _ in top_n_list])
    top_n_refactored = {code: value * factor for code, value in top_n.items()}
    total_sum_cutoff = sum(top_n_refactored.values())
    if not isclose(total_sum_cutoff, 1):
        if not mute_output: print("Warning: Got country weighted mentions cutoff not properly normalized: ", top_n_refactored)
    
    return top_n_refactored

def __infer_adm1(
        locations_data: List[Dict[str, Any]],
        es: Elasticsearch,
        mute_output: bool = False,
        candidates_weight: float = 1,
        text_weight: float = 1,
        cutoff: int = 3
):
    """
    Infers first order administrative divisions of relevance. It uses the location entities that are found in the toponym recognition step, as well as the candidates retrieved for them.
    The function counts the number of text mentions for different first order administrative divisions, as well as how representative they are amongst the various candidates.

    Parameters
    ----------
    locations_data : List[Dict[str, Any]]
        Data on every location entity, including its name, as well as the candidates that have been found for it.
    es : Elasticsearch
        Elasticsearch instance that must have the "geonames_custom" index.
    mute_output : bool
        Mute all text status output.
    candidates_weight : float
        How much should a country's representation amongst candidates count towards the overall score.
    text_weight : float
        How much should a country's text mentions count towards the overall score.
    cutoff : int
        The number of inferred countries that should be returned.

    Returns
    -------
    Dict[str, Dict[str, float]]
        Dictionary with country codes as keys, that point to another dictionary with admin1 codes as key, and their calculated relevance as value.
    """

    if candidates_weight == 0 and text_weight == 0:
        raise ValueError("both candidates_weight and text_weight are set to 0")
    
    # Count number of times an adm1 is in at least one of the candidates for a toponym.
    candidate_mentions = {}
    for location in locations_data:
        candidates_adm1 = []
        for candidate in location["candidates"]:
            country_admin1 = candidate["country_code"] + "." + candidate["admin1_code"]

            # This will ignore any admin code not in the official geonames list. Admin codes such as historical ones.
            if country_admin1 not in ADMIN1_LIST: continue

            # Do not count if the admin1 has already been counted for this location entity.
            if country_admin1 in candidates_adm1: continue
            
            candidates_adm1.append(country_admin1)
            if candidate["country_code"] not in candidate_mentions:
                candidate_mentions[candidate["country_code"]] = {candidate["admin1_code"]: 1}
            elif candidate["admin1_code"] not in candidate_mentions[candidate["country_code"]]:
                candidate_mentions[candidate["country_code"]][candidate["admin1_code"]] = 1
            else: candidate_mentions[candidate["country_code"]][candidate["admin1_code"]] += 1
    
    # For all adm1 mentions retrieved in the previous process, find their entry in Elasticsearch.
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
                if not mute_output: print(f"Info: Found more than one result for adm1 query. adm1: {adm1_code}, country: {country_code}")
                continue
            if len(q_results) == 0:
                if not mute_output: print(f"Info: Found no results for adm1 query. adm1: {adm1_code}, country: {country_code}")
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
    
    # Calculate total number of mentions.
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
    
    # Check if weighted dictionary is properly normalized.
    total_sum = 0
    for _, value in weighted_mentions.items():
        total_sum += sum(value.values())
    if not isclose(total_sum, 1):
        if not mute_output: print("Warning: Got admin1 weighted mentions not properly normalized: ", total_sum)

    # Create simplified representation of dictionary. Instead of {country_code: {admin_code: value}} we have {country_code.admin_code: value}.
    simplified_weighted_mentions = {}
    for country_code, country_dict in weighted_mentions.items():
        for admin1_code, value in country_dict.items():
            simplified_weighted_mentions[f"{country_code}.{admin1_code}"] = value

    # Get the top n admin1 codes.
    top_n_list = sorted(zip(simplified_weighted_mentions.values(), simplified_weighted_mentions.keys()), reverse=True)[:cutoff]
    top_n = {}
    for value, code in top_n_list:
        code_split = code.split(".")
        country_code = code_split[0]
        admin1_code = code_split[1]
        if country_code not in top_n: top_n[country_code] = {}
        top_n[country_code][admin1_code] = value

    # Normalize.
    factor = 1 / sum([value for value, _ in top_n_list])
    top_n_refactored = {}
    for country_code, country_dict in top_n.items():
        for admin1_code, value in country_dict.items():
            if country_code not in top_n_refactored: top_n_refactored[country_code] = {}
            top_n_refactored[country_code][admin1_code] = value * factor

    # Check if weighted list is properly normalized.
    total_sum_cutoff = 0
    for _, value in top_n_refactored.items():
        total_sum_cutoff += sum(value.values())
    if not isclose(total_sum_cutoff, 1):
        if not mute_output: print("Warning: Got admin1 weighted mentions cutoff not properly normalized: ", top_n_refactored)
    
    return top_n_refactored

def __get_ancestors(
        candidate: Dict[str, Any],
        es: Elasticsearch,
        mute_output: bool = False
) -> Dict[str, Dict[str, Any]]:
    """
    Retrieve the ancestors for a candidate. Ancestors in this context, refer to the administrative divisions a toponym belongs to.
    I.e., A first order administrative division belongs to a country, etc. 

    Parameters
    ----------
    candidate : Dict[str, Any]
        Candidate to find ancestors for.
    es : Elasticsearch
        Elasticsearch instance to search for ancestors. Must have the "geonames_custom" index.
    mute_output : bool
        Mute all text status output.

    Returns
    -------
    Dict[str, Dict[str, Any]]
        Dictionary with three entries, one for each of the country, first order, and second order administrative division entries.
    """

    ancestors = {"country": None, "admin1": None, "admin2": None}

    feature_code = candidate['feature_code']
    country_code = candidate['country_code']
    admin1_code = candidate['admin1_code']
    admin2_code = candidate['admin2_code']

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
            if not mute_output: print(f"Warning: Found more than one result for country query. country: {country_code}")
        elif len(q_results) == 0:
            if not mute_output: print(f"Info: Found no results for country query. country: {country_code}")
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
            if not mute_output: print(f"Warning: Found more than one result for adm1 query. adm1: {admin1_code}, country: {country_code}")
        elif len(q_results) == 0:
            if not mute_output: print(f"Info: Found no results for adm1 query. adm1: {admin1_code}, country: {country_code}")
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
            if not mute_output: print(f"Warning: Found more than one result for adm2 query. adm2: {admin2_code}, adm1: {admin1_code}, country: {country_code}")
        elif len(q_results) == 0:
            if not mute_output: print(f"Info: Found no results for adm2 query. adm2: {admin2_code}, adm1: {admin1_code}, country: {country_code}")
        else:
            ancestors["admin2"] = q_results[0].to_dict()

    return ancestors

def __rank(
        location: Dict[str, Any],
        locations_data: List[Dict[str, Any]],
        es: Elasticsearch,
        text: str,
        inferred_countries: Dict[str, float],
        inferred_adm1: Dict[str, Dict[str, float]],
        mute_output: bool = False,
        pop_weight: float = 1,
        alt_names_weight: float = 1,
        country_weight: float = 1,
        admin1_weight: float = 1,
        hierarchy_weight: float = 1
) -> None:
    """
    Rank a locations toponym candidates with a value between 0 and 1.
    This value is the 4th-root of the normalized sum of different scoring methods.

    Parameters
    ----------
    location : Dict[str, Any]
        The location entry for a given location entity. Contains information such as its name in text, as well as its candidates.
    locations_data : List[Dict[str, Any]]
        All location entries generated in the geoparsing process.
    es : Elasticsearch
        Elasticsearch instance with the "geonames_custom" index.
    inferred_countries : Dict[str, float]
        Countries that have been inferred with infer_countries().
    inferred_adm1 : Dict[str, Dict[str, float]]
        First order administrative divisions that have been inferred with infer_adm1().
    mute_output : bool = False
        Mute all text status output.
    pop_weight : float
        How much a candidate's population size should contribute to the overall score.
    alt_names_weight : float
        How much a candidate's number of alternate names should contribute to the overall score.
    country_weight : float
        How much the inferred countries should affect the overall score.
    admin1_weight : float
        How much the inferred first order administrative divisions should affect the overall score.
    hierarchy_weight : float
        How much the text mentions of a candidate's geographical ancestors should contribute to the overall score.
    """

    if len(location["candidates"]) == 0: return
    for candidate in location["candidates"]:
        norm_factor = 1 / (pop_weight + alt_names_weight + country_weight + admin1_weight + hierarchy_weight)
        candidate["pop_score"] = __pop_score(int(candidate["population"]))
        candidate["alt_names_score"] = __alt_names_score(len(candidate["alternatenames"]))
        candidate["country_score"] = __country_score(inferred_countries, candidate["country_code"])
        candidate["admin1_score"] = __admin1_score(inferred_adm1, candidate["country_code"], candidate["admin1_code"])
        candidate["hierarchy_score"] = __hierarchy_score(candidate, es, location, locations_data, text, mute_output)
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

def __find_hierarchy_distances(
        ancestors: Dict[str, Dict[str, Any]],
        location: Dict[str, Any],
        locations_data: List[Dict[str, Any]],
        text: str
) -> Dict[str, int]:
    """
    Find the distance in text between a location entity and one of its candidate's ancestors.
    A candidate's ancestors, are toponyms that are higher in its hierarchical tree.
    Will only calculate these distances if they actually exist in the text.

    Parameters
    ----------
    ancestors : Dict[str, Dict[str, Any]]
        A candidate's hierarchical ancestors.
    location : Dict[str, Any]
        The location entity that a distance should be calculated for.
    locations_data : List[Dict[str, Any]]
        All location entities in the geoparsing process.
    text : str
        The text that the distance should be calculated in.
    
    Returns
    -------
    Dict[str, int]
        Dictionary with hierarchical levels as keys (country, admin1, admin2) and their shortest calculated distance as values.
    """

    hierarchy_distances = {}
    for key, value in ancestors.items():
        if value is None:
            continue
        for entry in locations_data:
            if entry["entity_name"] == value["name"] or entry["entity_name"] == value["asciiname"] or entry["entity_name"] in value["alternatenames"]:
                distance = __calculate_entity_distance(text, location, entry)
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

def __pop_score(
        candidate_pop: int
) -> float:
    """
    Calculate the population score for a candidate.
    Uses a logistic function to produce an output.
    The population size is scaled to better fit with the logistic function.

    Parameters
    ----------
    candidate_pop : int
        The population size of a candidate.
    
    Returns
    -------
    float
        The score given a population size.
    """

    if candidate_pop == 0: return 0
    scaled_pop = candidate_pop / 10000
    return logistic_function(log2(scaled_pop), 3)

def __alt_names_score(
        num_alt_names: int
) -> float:
    """
    Calculate the alternate names score for a candidate.
    Uses a logistic function to produce an output.

    Parameters
    ----------
    num_alt_names : int
        The number of alternate names for a candidate.
    
    Returns
    -------
    float
        The score given the number of alternate names.
    """

    if num_alt_names == 0: return 0
    return logistic_function(log2(num_alt_names), 3)

def __country_score(
        inferred_countries: Dict[str, float],
        country_code: str
) -> float:
    """
    The score a candidate receives depending on whether it belongs to any of the inferred countries.

    Parameters
    ----------
    inferred_countries : Dict[str, float]
        Inferred countries determined by the infer_countries() function.
    country_code : str
        Country code of a given candidate.
    
    Returns
    -------
    float
        The inferred relevance of a country, or 0 if it is not present.
    """

    if country_code not in inferred_countries: return 0
    return inferred_countries[country_code]

def __admin1_score(
        inferred_adm1: Dict[str, Dict[str, float]],
        country_code: str,
        admin1_code: str
) -> float:
    """
    The score a candidate receives depending on whether it belongs to any of the inferred first order administrative divisions.

    Parameters
    ----------
    inferred_adm1 : Dict[str, float]
        Inferred first order administrative divisions determined by the infer_adm1() function.
    country_code : str
        Country code of a given candidate.
    admin1_code : str
        Admin1 code of a given candidate.
        
    Returns
    -------
    float
        The inferred relevance of a first order administrative division, or 0 if it is not present.
    """

    if country_code not in inferred_adm1: return 0
    if admin1_code not in inferred_adm1[country_code]: return 0
    return inferred_adm1[country_code][admin1_code]

def __hierarchy_score(
        candidate: Dict[str, Any],
        es: Elasticsearch,
        location: Dict[str, Any],
        locations_data: List[Dict[str, Any]],
        text: str,
        mute_output: bool = False
) -> float:
    """
    Calculate the score a candidate should receive based on how close its hierarchical ancestors are in text.
    The score is based on the inverse of the log2 distance to the ancestor.

    Parameters
    ----------
    candidate : Dict[str, Any]
        The candidate to score.
    es : Elasticsearch
        Elasticsearch instance. Must have the "geonames_custom" index.
    location : Dict[str, Any]
        The location entity that the candidate belongs to.
    locations_data : List[Dict[str, Any]]
        All location entities in the geoparsing process.
    text : str
        The text that is being geoparsed.
    mute_output : bool
        Mute all text status output.
        
    Returns
    -------
    float
        The score a candidate should receive based on its distance to hierarchical ancestors.
    """

    ancestors = __get_ancestors(candidate, es, mute_output)
    hierarchy_distances = __find_hierarchy_distances(ancestors, location, locations_data, text)
    score = 0
    for key, value in hierarchy_distances.items():
        temp_score = 0
        if key == "admin2": temp_score = (1 / log2(value+1)) * 1
        if key == "admin1": temp_score = (1 / log2(value+1)) * 0.5
        if key == "country": temp_score = (1 / log2(value+1)) * 0.25
        if temp_score > score: score = temp_score
    return score
