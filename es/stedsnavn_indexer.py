from elasticsearch import Elasticsearch, helpers
import xml.etree.ElementTree as et
import sys


INDEX_NAME = "stedsnavn"
INDEX_SETTINGS = {
    "mappings": {
        "properties": {
            "stedsnavnid": {"type": "keyword"},
            "name": {"type": "text"},
            "name_object_main_group": {"type": "text"},
            "name_object_group": {"type": "text"},
            "name_object_type": {"type": "text"},
            "alternatenames": {"type": "text", "norms": False, "similarity": "boolean"},
            "coordinates": {"type": "geo_point"},
        }
    }
}

NS = {
    "wfs": "{http://www.opengis.net/wfs/2.0}",
    "app": "{http://skjema.geonorge.no/SOSI/produktspesifikasjon/Stedsnavn/5.0}",
    "gml": "{http://www.opengis.net/gml/3.2}"
}

def parse_stedsnavn_data(reader):
    i = 0
    for _, element in reader:
        try:
            # Ignore any line except the root place element
            if element.tag != NS["app"] + "Sted":
                continue

            i += 1
            if i % 10000 == 0:
                total = 1056214 # The total in question was from data taken in march 2024
                print(f"Indexing element: {i}/{total}", end="\r")


            id = element.attrib[NS["gml"] + "id"][5:]

            # Find names
            names = []
            placename_list = element.findall(".//" + NS["app"] + "Stedsnavn")
            if len(placename_list) == 0:
                raise Exception(f"Failed to get placename data for entry: {id}")
            for placename in placename_list:
                way_of_writing_list = placename.findall(".//" + NS["app"] + "Skrivemåte")
                if len(way_of_writing_list) == 0:
                    raise Exception(f"Failed to get \"way of writing\" data for entry: {id}")
                for way_of_writing in way_of_writing_list:
                    name = way_of_writing.find(NS["app"] + "langnavn").text
                    priority = True if way_of_writing.find(NS["app"] + "prioritertSkrivemåte").text == "true" else False
                    names.append({
                        "name": name,
                        "priority": priority
                    })

            entry_name = ""
            alternate_names = []
            for name in names:
                if name["name"] in alternate_names: continue
                if not entry_name and (name["priority"] or len(names) == 1): entry_name = name["name"]
                else: alternate_names.append(name["name"])
            
            # Need this, because sometimes no name is set to have priority true
            if not entry_name:
                entry_name = alternate_names[0]
                alternate_names = alternate_names[1:]

            # Administrative divisions
            admin_codes = [] # [(admin1_code, admin2_code), ...]
            admin_names = [] # [(admin1_name, admin2_name), ...] Index in admin_codes matches admin_names
            admins_list = element.findall(".//" + NS["app"] + "Kommune")
            for admin in admins_list:
                admin1_code = admin.findall(".//" + NS["app"] + "fylkesnummer")
                if len(admin1_code) > 1:
                    raise Exception(f"Found more than one admin1 code for Kommune in entry: {id}")
                admin1_name = admin.findall(".//" + NS["app"] + "fylkesnavn")
                if len(admin1_name) > 1:
                    raise Exception(f"Found more than one admin1 name for Kommune in entry: {id}")
                admin2_code = admin.findall(".//" + NS["app"] + "kommunenummer")
                if len(admin2_code) > 1:
                    raise Exception(f"Found more than one admin2 code for Kommune in entry: {id}")
                admin2_name = admin.findall(".//" + NS["app"] + "kommunenavn")
                if len(admin2_name) > 1:
                    raise Exception(f"Found more than one admin2 navn for Kommune in entry: {id}")
                admin_codes.append((admin1_code[0].text, admin2_code[0].text))
                admin_names.append((admin1_name[0].text, admin2_name[0].text))


            # Find coordinates
            coordinates = ""
            position_element = element.find(NS["app"] + "posisjon")
            if position_element is None:
                raise Exception(f"Failed to get position data for entry: {id}")
            type = list(position_element)[0].tag
            if type == NS["gml"] + "Point":
                coordinates = ",".join(position_element.find(".//" + NS["gml"] + "pos").text.split())
            elif type == NS["gml"] + "MultiPoint":
                positions = position_element.findall(".//" + NS["gml"] + "pos")
                coordinates = ",".join(positions[0].text.split())
            elif type == NS["gml"] + "LineString":
                # Seems to represent things such as road and tunnel segments
                # For now we will simply select the first set of coordinates in the position list,
                # as it seems like this indicates the start of the place in question
                pos_list = position_element.find(".//" + NS["gml"] + "posList")
                coordinates = ",".join(pos_list.text.split()[:2])
            elif type == NS["gml"] + "MultiCurve":
                # Seems to be primarily used for roads?
                # Just select the starting position in one of the position lists for now.
                pos_list = position_element.find(".//" + NS["gml"] + "posList")
                coordinates = ",".join(pos_list.text.split()[:2])
            elif type == NS["gml"] + "Polygon":
                # Seems to concern geographical areas, such as seas.
                # TODO: This just selects an element on the polygon atm.
                # A better solution would find the centroid of the polygon, and use that as a reference point.
                pos_list = position_element.find(".//" + NS["gml"] + "posList")
                coordinates = ",".join(pos_list.text.split()[:2])
            else:
                raise Exception(f"No handle for position type: {type}")
            
            name_object_main_group = element.find(NS["app"] + "navneobjekthovedgruppe")
            name_object_group = element.find(NS["app"] + "navneobjektgruppe")
            name_object_type = element.find(NS["app"] + "navneobjekttype")
            if name_object_main_group is None or name_object_group is None or name_object_type is None:
                raise Exception(f"Failed to get type data for entry: {id}")
            
            element.clear() # Free up memory
            yield {
                "_index": INDEX_NAME,
                "_id": id,
                "_source": {
                    "stedsnavnid": id,
                    "name": entry_name,
                    "name_object_main_group": name_object_main_group.text,
                    "name_object_group": name_object_group.text,
                    "name_object_type": name_object_type.text,
                    "admin_codes": admin_codes,
                    "admin_names": admin_names,
                    "alternatenames": alternate_names,
                    "coordinates": coordinates
                }
            }
        except Exception as e:
            print("\n"+ e)

if __name__ == "__main__":
    es = Elasticsearch("http://localhost:9200")
    if not es.indices.exists(INDEX_NAME):
        es.indices.create(index=INDEX_NAME, body=INDEX_SETTINGS)
    if len(sys.argv) != 2:
        print(f"Invalid number of arguments. Script takes 1 argument but {len(sys.argv)-1} were provided.")
        exit()
    file = open(sys.argv[1], "rt", encoding="utf-8")

    reader = iter(et.iterparse(file, events=("end",)))
    actions = parse_stedsnavn_data(reader)
    helpers.bulk(es, actions, chunk_size=500)
    es.indices.refresh(index=INDEX_NAME)