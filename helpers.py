from typing import Callable, Any, List, Dict
from math import exp
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
        candidate_fields: List[str] = ["name", "geonameid", "country_code", "coordinates", "score"],
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