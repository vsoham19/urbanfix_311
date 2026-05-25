import xml.etree.ElementTree as ET
import os

kml_path = r"c:\Users\vsoha\Desktop\Work\urbanfix\311\ahmedabad_wards_map_2024.kml"
ns = {'kml': 'http://www.opengis.net/kml/2.2'}

if not os.path.exists(kml_path):
    print("KML not found at", kml_path)
else:
    tree = ET.parse(kml_path)
    root = tree.getroot()
    
    placemarks = root.findall('.//kml:Placemark', ns)
    print(f"Found {len(placemarks)} placemarks")
    
    parsed = 0
    for i, pm in enumerate(placemarks[:10], start=1):
        ward_name = None
        simple_datas = pm.findall('.//kml:SimpleData', ns)
        for sd in simple_datas:
            if sd.attrib.get('name') == 'sourcewardname':
                ward_name = sd.text
                break
        
        coord_nodes = pm.findall('.//kml:coordinates', ns)
        coord_lens = [len(cn.text.strip().split()) for cn in coord_nodes]
        print(f"Placemark {i}: Name={ward_name}, Coordinates sets={len(coord_nodes)}, Points in sets={coord_lens}")
