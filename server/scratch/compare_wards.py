import xml.etree.ElementTree as ET
import os
import sys

# Load KML Wards
kml_path = r"c:\Users\vsoha\Desktop\Work\urbanfix\311\ahmedabad_wards_map_2024.kml"
ns = {'kml': 'http://www.opengis.net/kml/2.2'}

tree = ET.parse(kml_path)
root = tree.getroot()

kml_wards = set()
placemarks = root.findall('.//kml:Placemark', ns)
for pm in placemarks:
    simple_datas = pm.findall('.//kml:SimpleData', ns)
    for sd in simple_datas:
        if sd.attrib.get('name') == 'sourcewardname':
            kml_wards.add(sd.text)
            break

# Add routes path to pythonpath
sys.path.append(r"c:\Users\vsoha\Desktop\Work\urbanfix\311\server")
from generators.iot_sewer_data import AHMEDABAD_SEWER_WARDS

generator_wards = set(w["ward"] for w in AHMEDABAD_SEWER_WARDS)

print("KML count:", len(kml_wards))
print("Generator count:", len(generator_wards))

missing_in_kml = generator_wards - kml_wards
missing_in_gen = kml_wards - generator_wards

print("\nMissing in KML (defined in generator but not in KML):")
print(sorted(list(missing_in_kml)))

print("\nMissing in Generator (defined in KML but not in generator):")
print(sorted(list(missing_in_gen)))

# Try matching by lowering case and stripping spaces
def norm(name):
    return name.lower().replace("-", "").replace(" ", "")

norm_kml = {norm(w): w for w in kml_wards}
norm_gen = {norm(w): w for w in generator_wards}

print("\nUnmatched after normalization:")
print("In generator but not in KML:", sorted([w for w in generator_wards if norm(w) not in norm_kml]))
print("In KML but not in generator:", sorted([w for w in kml_wards if norm(w) not in norm_gen]))
