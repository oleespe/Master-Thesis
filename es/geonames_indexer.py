import sys
from elasticsearch import Elasticsearch, helpers
from tqdm import tqdm
import csv

INDEX_NAME = "geonames_custom"
INDEX_SETTINGS = {
    "mappings": {
        "properties": {
            "geonameid": {"type": "keyword"},
            "name": {"type": "text"},
            "asciiname": {"type": "text"},
            "alternatenames": {"type": "text", "norms": False, "similarity": "boolean"},
            "coordinates": {"type": "geo_point"},
            "feature_class": {"type": "keyword"},
            "feature_code": {"type": "keyword"},
            "country_code": {"type": "keyword"},
            "admin1_code": {"type": "keyword"},
            "admin2_code": {"type": "keyword"},
            "admin3_code": {"type": "keyword"},
            "admin4_code": {"type": "keyword"},
            "population": {"type": "long"},
            "modification_date": {"type": "date", "format": "date"}
        }
    }
}

def parse_geonames_data(reader):
    for row in tqdm(reader, total=12571835):
        try:
            coords = f"{row[4]},{row[5]}"
            alt_names = list(set(row[3].split(",")))
            
            if str(row[0]) == "6252001":
                alt_names.append("US")
                alt_names.append("U.S.")
            if str(row[0]) == "239880":
                alt_names.append("C.A.R.")
            
            doc = {
                "geonameid": row[0],
                "name": row[1],
                "asciiname": row[2],
                "alternatenames": alt_names,
                "coordinates": coords,
                "feature_class" : row[6],
                "feature_code" : row[7],
                "country_code" : row[8],
                "admin1_code" : row[10],
                "admin2_code" : row[11],
                "admin3_code" : row[12],
                "admin4_code" : row[13],
                "population": row[14],
                "modification_date": row[18],
            }
            yield {
                "_index": INDEX_NAME,
                "_id": row[0],
                "_source": doc
            }
        except Exception as e:
            print(e, row)


if __name__ == "__main__":
    es = Elasticsearch("http://localhost:9200")
    if not es.indices.exists(INDEX_NAME):
        es.indices.create(index=INDEX_NAME, body=INDEX_SETTINGS)
    if len(sys.argv) != 2:
        print(f"Invalid number of arguments. Script takes 1 argument but {len(sys.argv)-1} were provided.")
        exit()
    file = sys.argv[1]
    
    reader = csv.reader(file, delimiter="\t")
    actions = parse_geonames_data(reader)
    helpers.bulk(es, actions, chunk_size=500)
    es.indices.refresh(index=INDEX_NAME)
