from typing import Callable, Any, List, Dict
from math import exp
from unidecode import unidecode
from lists import *
import cv2
import numpy as np
import pandas as pd

def create_solutions_dict(
        file_path: str
) -> Dict[str, int]:
    solutions = pd.read_csv(file_path)
    solutions_dict = {}
    for i, row in solutions.iterrows():
        # Drop rows that don't have a geonames id.
        # This happens when there is a place name in the relevant pdf that has been manually found,
        # but with no record in the geonames database.
        # This can happen if the location is very obscure or if it is a historic location etc.
        # For all purposes, we do not consider these when determining accuracy.
        if row["geonameid"] == -1:
            # solutions.drop(i, inplace=True)
            continue
        solutions_dict[row["name"]] = row["geonameid"]
    return solutions_dict

# Deskew image for ocr parse.
def deskew(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.bitwise_not(gray)
    coords = np.column_stack(np.where(gray > 0))
    angle = cv2.minAreaRect(coords)[-1]
    
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle

    (h, w) = image.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    return rotated

def read_admin1(
        file_path: str
) -> pd.DataFrame:
    admin1 = pd.read_csv(file_path, sep="\t", header=None)
    return admin1

def read_admin2(
        file_path: str
) -> pd.DataFrame:
    admin2 = pd.read_csv(file_path, sep="\t", header=None)
    return admin2

def write_csv_results(
        file_path: str,
        locations_data: List[Dict[str, Any]]
):
    with open(file_path, "w") as file:
        file.write("name,id,coordinates,database\n")
        for location in locations_data:
            if len(location["candidates"]) > 0:
                best_candidate = location["candidates"][0]
                if "geonameid" in best_candidate: file.write(f"{best_candidate['name']},{best_candidate['geonameid']},\"{best_candidate['coordinates']}\",geonames\n")
                else: file.write(f"{best_candidate['name']},{best_candidate['stedsnavnid']},\"{best_candidate['coordinates']}\",stedsnavn\n")

def logistic_function(
        x: float,
        x0: float = 0,
        l: float = 1,
        k: float = 1
) -> float:
    return l / (1 + exp(-k*(x-x0)))

def print_results(
        locations_data: List[Dict[str, Any]],
        fields: List[str] = ["entity_name"],
        candidate_fields: List[str] = ["name", "dataset", "id", "country_code", "coordinates", "score"],
        n_candidates: int = 2
):
    for location in locations_data:
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

def convert_geonames(
        geonames_entry: Dict[str, Any]
) -> Dict[str, Any]:
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
            "population": "0"} # Stedsnavn has no population data