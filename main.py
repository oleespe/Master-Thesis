from elasticsearch import Elasticsearch
import spacy
import PyPDF2
import pandas as pd

nlp = spacy.load("nb_core_news_lg")

# filename = "Temaanalyse om dødsulykker i tunnel[671].pdf"
# filename = "kjoretoybranner_norske_vegtunneler_til_2021_nævestad_2[670].pdf"
# filename = "varsom_snoeskred_rapport2023_32[678].pdf"
filename = "Karolinernes_dødsmarsj.pdf"

with open("sample_data/" + filename, "rb") as file:
    pdfReader = PyPDF2.PdfReader(file)
    df = pd.DataFrame([], columns=["name", "label"])

    for page in pdfReader.pages:
        page_text = page.extract_text()
        doc = nlp(page_text)
        places = [[ent.text.strip(), ent.label_] for ent in doc.ents if ent.label_ in ["GPE", "LOC", "GPE_LOC", "GPE_ORG"]]
        for place in places:
            name = place[0]

            # Check for names that are obviously not places
            if not name.isalpha() or name.isspace() or name.islower():
                continue
            
            # Check if place has already been added
            if name in df["name"].tolist():
                continue 
            
            df.loc[len(df.index)] = place


es = Elasticsearch("http://localhost:9200")
for _, row in df.iterrows():
    print(row["name"])
    search = es.search(index="geonames", query={"match": {"name": row["name"]}})
    for result in search["hits"]["hits"]:
        print(result["_source"])
    print()
