# Norwegian Language Geoparsing

This project implements a geoparser designed to be used on Norwegian language text.
The geoparser is designed to process entire PDF files, but should also work on smaller texts.

## Installation

It is recommended that any installation is done in a virtual environment.

### Geoparser

```console
git clone https://github.com/oleespe/Master-Thesis
pip install -r requirements.txt
```

### Pytesseract

If you want to use pytesseract to parse Norwegian language PDF files, the following packages need to also be installed.

```console
sudo apt-get install python3-pil tesseract-ocr libtesseract-dev tesseract-ocr-eng tesseract-ocr-script-latn tesseract-ocr-nor
apt install libgl1-mesa-glx
apt-get install poppler-utils
```

### SpaCy

The following command is used to download the Norwegian language model used with SpaCy.
It needs to be installed for the NER step to function.

```console
python -m spacy download nb_core_news_lg
```

### Elasticsearch and Geographical Datasets

Elasticsearch needs to be installed and running for the geoparser to function.
The current version used here is 7.15, but any 7.x version should be fine.
Instructions on how to set up Elasticsearch can be found through the following link: <https://www.elastic.co/guide/en/elasticsearch/reference/7.15/install-elasticsearch.html>.

### Geographical Datasets

The geoparser uses two geographical datasets, GeoNames and Stedsnavn, to draw toponym candidates from.
These need to both be downloaded and indexed with Elasticsearch.

**GeoNames:**

GeoNames contains toponym entries from all over the world.
To index GeoNames, the file `allCountries.txt` needs to be downloaded and put in the `data/` folder.
`allCountries.txt` contains all approximately 11 million entries in GeoNames.
The files `admin1CodesASCII.txt` and `admin2Codes.txt` also need to be downloaded and put in the same folder, as they are used in the geoparsing algorithm.
The commands below describe how to do this.

```console
mkdir data

wget -P data https://download.geonames.org/export/dump/allCountries.zip
unzip data/allCountries.zip -d data
rm data/allCountries.zip

wget -P data https://download.geonames.org/export/dump/admin1CodesASCII.txt
wget -P data https://download.geonames.org/export/dump/admin2Codes.txt
```

**Stedsnavn:**

The Stedsnavn dataset is a Norway only dataset, i.e., containing only entries for Norwegian toponyms.
It needs to be downloaded manually using the following link: <https://kartkatalog.geonorge.no/metadata/stedsnavn-komplett-ssr/e1c50348-962d-4047-8325-bdc265c853ed>.
Beware that the site is in Norwegian, but can be changed to English using the menu.
To actually download the dataset, first click download and then _Go to download_ via the cloud icon.
You will then be taken to another site, where you simply click all the default options where relevant, and then the download button.
Similarly to GeoNames, the downloaded file needs to be unzipped and placed in the `data/` folder.

**Indexing:**

The indexing process itself is done using the following commands.
Keep in mind that the scripts use the file paths of the dataset files as arguments.
If these are moved or renamed, the argument needs to changed as well.

```console
python es/geonames_indexer.py data/allCountries.txt
python es/stedsnavn_indexer.py data/Basisdata_0000_Norge_4258_stedsnavn_GML.gml
```

## Example Usage

There are two main ways of using the geoparser.
The first is to used the main `geoparse()` functions with any text input as shown below.

```py
results = geoparse("Jeg kommer fra Ølensvåg i Rogaland")
print_results(results["results"])

entity_name: Ølensvåg
candidates: {
 {
 name: Ølensvåg
 dataset: geonames
 id: 8591275
 country_code: NO
 coordinates: 59.59784,5.73911
 score: 2.319202922022118
 }
}

entity_name: Rogaland
candidates: {
 {
 name: Rogaland Fylke
 dataset: geonames
 id: 3141558
 country_code: NO
 coordinates: 59.09608,6.20442
 score: 3.049605544218437
 }
}
```

Another way of using the geoparser is to use `geoparse_pdf()`, which takes the filepath of a pdf file as input.
Furthermore, this function uses one of two different pdf parser: `ocr_parse()` or `pypdf2_parse()`.
The results from this function uses the same format as the base `geoparse()` function.

```py
results = geoparse_pdf(file_path, pdf_parser=ocr_parse, is_wikipedia=True)
```

## Output

The output of the geoparser follows the following format.

```py
results = {
    "inferred_countries": {"NO": 0.6, "US": 0.2, "SE": 0.2}, # Inferred countries of relevance
    "inferred_admin1": {"NO": {"21": 0.5, "18": 0.25} "UK": {"ENG": 0.25}}, # inferred first order administrative divisions of relevance
    "results": {"entity_name": "Norge", "label": "GPE_LOC", "start_char": 35, "end_char": 40, "candidates": [<list of candidates>]}
}
```

The results from the geoparser can be converted into a csv file with the following code.
For each result, it stores the location name, id, coordinates, and dataset it was retrieved from.

```py
write_csv_results(<path to csv file>, results["results"])
```
