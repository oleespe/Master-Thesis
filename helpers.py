import pandas as pd

def read_solution(filename: str) -> pd.DataFrame:
    return pd.read_csv("sample_data_solutions/" + filename)
