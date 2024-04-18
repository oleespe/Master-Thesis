from typing import Callable, Any, List, Dict
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