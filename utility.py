import cv2
import numpy as np
import pandas as pd
from typing import Any, List, Dict, Union
from math import exp
from unidecode import unidecode
from lists import *
from tabulate import tabulate

def create_solutions_dict(
        file_path: str
) -> Dict[str, Dict[str, Any]]:
    """
    Creates a dictionary based on the contents of a solutions file.
    The solution file should be the result of manual geoparsing.

    Parameters
    ----------
    file_path : str
        The file path to the solutions file.
        
    Returns
    -------
    Dict[str, Dict[str, Any]]
        A dictionary with a location entity name as key, and dictionary containing further information on that entity, as value. 
    """

    solutions = pd.read_csv(file_path)
    solutions_dict = {}
    for _, row in solutions.iterrows():
        if row["id"] == 0:
            continue
        solutions_dict[row["name"]] = {"id": row["id"], "dataset": row["dataset"]}
    return solutions_dict

# Deskew image for ocr parse.
def deskew(
        pdf : np.NDArray[Any]
) -> cv2.MatLike:
    """
    Deskew a pdf, so that it can be used with pytesseract

    Parameters
    ----------
    pdf : np.NDArray[Any]
        pdf as a numpy array.
        
    Returns
    -------
    Dict[str, Dict[str, Any]]
        A deskewed representation of the pdf.  
    """

    gray = cv2.cvtColor(pdf, cv2.COLOR_BGR2GRAY)
    gray = cv2.bitwise_not(gray)
    coords = np.column_stack(np.where(gray > 0))
    angle = cv2.minAreaRect(coords)[-1]
    
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle

    (h, w) = pdf.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(pdf, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    return rotated

def read_admin1(
        file_path: str
) -> pd.DataFrame:
    """
    Read a GeoNames admin1 file.
    The admin1 file contains information on all countries first order administrative divisions.

    Parameters
    ----------
    file_path : str
        Path to the admin1 file.
        
    Returns
    -------
    pd.DataFrame
        Pandas dataframe representation of the file.
    """

    admin1 = pd.read_csv(file_path, sep="\t", header=None)
    return admin1

def read_admin2(
        file_path: str
) -> pd.DataFrame:
    """
    Read a GeoNames admin2 file.
    The admin2 file contains information on all countries second order administrative divisions.

    Parameters
    ----------
    file_path : str
        Path to the admin2 file.
        
    Returns
    -------
    pd.DataFrame
        Pandas dataframe representation of the file.
    """

    admin2 = pd.read_csv(file_path, sep="\t", header=None)
    return admin2

def write_csv_results(
        file_path: str,
        results: List[Dict[str, Any]]
) -> None:
    """
    Write the results of the geoparser.

    Parameters
    ----------
    file_path : str
        File path where the results should be stored. File needs to be a .csv file.
    results : List[Dict[str, Any]]
        Results from the geoparser.
    """

    with open(file_path, "w") as file:
        file.write("name,id,coordinates,database\n")
        for location in results:
            top_candidate = get_top_candidate(location)
            if top_candidate is None:
                continue
            file.write(f"\"{top_candidate['name']}\",{top_candidate['id']},\"{top_candidate['coordinates']}\",{top_candidate['dataset']}\n")

def logistic_function(
        x: float,
        x0: float = 0,
        l: float = 1,
        k: float = 1
) -> float:
    """
    Calculate the value of a logistic function with the given input parameters.

    Parameters
    ----------
    x : float
        The value to calculate for.
    x0 : float
        x0 is the x value of the function's midpoint.
    l : float
        The carrying capacity of the values of the function.
    k : float
        The growth rate of the function.
        
    Returns
    -------
    float
        The calculated value.
    """

    return l / (1 + exp(-k*(x-x0)))

def print_results(
        results: List[Dict[str, Any]],
        fields: List[str] = ["entity_name"],
        candidate_fields: List[str] = ["name", "dataset", "id", "country_code", "coordinates", "score"],
        n_candidates: int = 2
) -> None:
    """
    Print the results of the geoparser. 

    Parameters
    ----------
    results: List[Dict[str, Any]]
        Results of the geoparser.
    fields: List[str]
        Fields to print for a location entity.
        Valid fields: ["entity_name", "label", "start_char", "end_char"]
    candidate_fields: List[str]
        Fields to print for each candidate of a location entity.
        Valid fields: ["dataset", "id", "name", "asciiname", "alternatenames", "coordinates", "feature_code", 
        "country_code", "admin1_code", "admin2_code", "population", "pop_score", "alt_names_score", "country_score", "admin1_score", "hierarchy_score", "score"]
    n_candidates: int
        The number of candidates that should be shown for each location. The candidates are sorted in descending order based on their score.
        Setting this to 1 will print only the top candidate.
    """

    for location in results:
        for field in fields:
            print(f"{field}: {location[field]}")
        i = 0
        print("candidates: {")
        for candidate in location["candidates"]:
            print("   {")
            for candidate_field in candidate_fields:
                print(f"\t{candidate_field}: {candidate[candidate_field]}")
            print("   }")
            i += 1
            if i == n_candidates: break
        print("}\n")

def print_all_mappings(
        file_path: str,
        results: List[Dict[str, Any]]
) -> None:
    """
    Print all mappings from the geoparser results.
    Depends on there being a solutions file to work.

    Parameters
    ----------
    file_path : str
        File path to the solutions file.
    results : List[Dict[str, Any]]
        Results from geoparsing.
    """

    print_order = [[], [], [], [], []]
    solutions_dict = create_solutions_dict(file_path)
    for location_name, value in solutions_dict.items():
        match_found = False
        for result in results:
            top_candidate = get_top_candidate(result)
            if top_candidate is None:
                if location_name == result["entity_name"]:
                    print_order[0].append([location_name, value['id'], value['dataset'], result['entity_name'], "None", "None", "None"])
                    match_found = True
                    break
                continue
            if location_name == top_candidate["name"] or location_name == top_candidate["asciiname"] or location_name in top_candidate["alternatenames"]:
                print_order[1].append([location_name, value['id'], value['dataset'], result['entity_name'], top_candidate['name'], top_candidate['id'], top_candidate['dataset']])
                match_found = True
                break
        if not match_found:
            print_order[2].append([location_name, value['id'], value['dataset'], "None", "None", "None", "None"])
    for result in results:
        top_candidate = get_top_candidate(result)
        if top_candidate is None:
            if result["entity_name"] not in solutions_dict.keys():
                print_order[3].append(["None", "None", "None", result['entity_name'], "None", "None", "None"])
            continue
        match_found = False
        for location_name, _ in solutions_dict.items():
            if location_name == top_candidate["name"] or location_name == top_candidate["asciiname"] or location_name in top_candidate["alternatenames"]:
                match_found = True
                break
        if not match_found:
            print_order[4].append(["None", "None", "None", result['entity_name'], top_candidate['name'], top_candidate['id'], top_candidate['dataset']])
    
    tabulate_list = []
    for list in print_order:
        for entry in list:
            tabulate_list.append(entry)
    print(tabulate(tabulate_list, headers=["Location Mention", "Toponym ID", "Toponym Dataset", "Entity Name", 
                            "Candidate Name", "Candidate ID", "Candidate Dataset"]))

def convert_geonames(
        geonames_entry: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Convert a GeoNames index entry into one that is usable in the geoparser.

    Parameters
    ----------
    geonames_entry : Dict[str, Any]
        An indexed GeoNames entry.

    Returns
    -------
    Dict[str, Any]
        A dictionary which encapsulates the GeoNames entry with the information needed in the geoparser.
    """

    return {"dataset": "geonames", 
            "id": geonames_entry["geonameid"], 
            "name": geonames_entry["name"], 
            "asciiname": geonames_entry["asciiname"],
            "alternatenames": geonames_entry["alternatenames"],
            "coordinates": geonames_entry["coordinates"],
            "feature_code": geonames_entry["feature_code"],
            "country_code": geonames_entry["country_code"],
            "admin1_code": geonames_entry["admin1_code"],
            "admin2_code": geonames_entry["admin2_code"],
            "population": geonames_entry["population"]}

# TODO: Stedsnavn entries can be part of multiple administrative divisions. Should augment the algorithm so that it can handle multiple entries.
# For now we simply use the first entry administrative divisions.
# TODO: We are currently using the ADMIN1_MAP and ADMIN2_MAP dictionaries to convert stedsnavn entry codes into geonames ones.
# This is because the geonames index and accompanying admin code files still use outdated admin codes.
# In the future, geonames will probably update its info, at which point these maps will be unnecessary.
# https://www.kartverket.no/til-lands/fakta-om-norge/norske-fylke-og-kommunar
# TODO: Apparently Stedsnavn also has nation entries, in which case all of this makes no sense.
# Either need to fix or make sure these entries are not indexed.
# Should not be an issue for the geoparser as it will always find nation candidates from geonames.
def convert_stedsnavn(
        stedsnavn_entry: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Convert a Stedsnavn index entry into one that is usable in the geoparser.

    Parameters
    ----------
    stedsnavn_entry : Dict[str, Any]
        An indexed Stedsnavn entry.

    Returns
    -------
    Dict[str, Any]
        A dictionary which encapsulates the Stedsnavn entry with the information needed in the geoparser.
    """

    return {"dataset": "stedsnavn", 
            "id": stedsnavn_entry["stedsnavnid"], 
            "name": stedsnavn_entry["name"], 
            "asciiname": unidecode(stedsnavn_entry["name"]),
            "alternatenames": stedsnavn_entry["alternatenames"],
            "coordinates": stedsnavn_entry["coordinates"],
            "feature_code": stedsnavn_entry["name_object_type"], # Not really a code for Stedsnavn, but will use the same name anyways
            "country_code": "NO",
            "admin1_code": ADMIN1_MAP[stedsnavn_entry["admin_codes"][0][0]], 
            "admin2_code": ADMIN2_MAP[stedsnavn_entry["admin_codes"][0][1]],
            # "admin1_code": stedsnavn_entry["admin_codes"][0][0],
            # "admin2_code": stedsnavn_entry["admin_codes"][0][1],
            "population": "0"} # Stedsnavn has no population data

def get_top_candidate(
        location: Dict[str, Any]
) -> Union[Dict[str, Any], None]:
    """
    Return the top candidate of a location.
    This will always be the first candidate in the candidate list.

    Parameters
    ----------
    location : Dict[str, Any]
        The location entity to retrieve the top candidate for.

    Returns
    -------
    Union[Dict[str, Any], None]
        The top candidate for a location entity, or None if it does not have any.
    """

    if len(location["candidates"]) == 0: return None
    return location["candidates"][0]