# Norwegian Language Geoparsing

This project implements a geoparser designed specifically for the Norwegian language.

## Installation

Actual geoparser:

```console
git clone https://github.com/oleespe/Master-Thesis
pip install -r requirements.txt
```

Pytesseract:

<https://pypi.org/project/pytesseract/>
<https://github.com/tesseract-ocr/tesseract>

SpaCy:

```console
python -m spacy download nb_core_news_lg
```

Elasticsearch and Geographical Datasets:

<https://www.elastic.co/guide/en/elasticsearch/reference/7.15/install-elasticsearch.html>

```console
mkdir data

wget -P data https://download.geonames.org/export/dump/allCountries.zip
unzip data/allCountries.zip -d data
rm data/allCountries.zip

wget -P data https://download.geonames.org/export/dump/admin1CodesASCII.txt
wget -P data https://download.geonames.org/export/dump/admin2Codes.txt
```

<https://kartkatalog.geonorge.no/metadata/stedsnavn-komplett-ssr/e1c50348-962d-4047-8325-bdc265c853ed>

```console
python es/geonames_indexer.py
python es/stedsnavn_indexer.py
```
