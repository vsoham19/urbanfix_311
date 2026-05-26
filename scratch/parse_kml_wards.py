import xml.etree.ElementTree as ET
import os

kml_path = "ahmedabad_wards_map_2024.kml"
if not os.path.exists(kml_path):
    kml_path = "server/ahmedabad_wards_map_2024.kml"

if os.path.exists(kml_path):
    ns = {'kml': 'http://www.opengis.net/kml/2.2'}
    tree = ET.parse(kml_path)
    kml_root = tree.getroot()
    placemarks = kml_root.findall('.//kml:Placemark', ns)
    print(f"Total Placemarks found: {len(placemarks)}")
    names = []
    for pm in placemarks:
        simple_datas = pm.findall('.//kml:SimpleData', ns)
        for sd in simple_datas:
            if sd.attrib.get('name') == 'sourcewardname':
                names.append(sd.text)
                break
    print("Wards in KML:", sorted(list(set(names))))
else:
    print("KML file not found.")
