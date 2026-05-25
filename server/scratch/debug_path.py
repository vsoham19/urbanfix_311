import os

# Simulate the path resolution from routes/iot.py
current_dir = os.path.dirname(os.path.abspath(__file__))
print(f"Script dir (__file__): {current_dir}")

# If running from server/ dir, simulate what routes/iot.py sees
routes_dir = os.path.join(current_dir, "routes")
server_dir = os.path.dirname(routes_dir)  # This is server/
root_dir = os.path.dirname(server_dir)    # This is 311/
kml_path = os.path.join(root_dir, "ahmedabad_wards_map_2024.kml")
print(f"Routes dir: {routes_dir}")
print(f"Server dir: {server_dir}")
print(f"Root dir: {root_dir}")
print(f"KML path: {kml_path}")
print(f"KML exists: {os.path.exists(kml_path)}")

# Now simulate from the ACTUAL routes/iot.py __file__
iot_file = os.path.join(current_dir, "routes", "iot.py")
iot_dir = os.path.dirname(os.path.abspath(iot_file))
srv_dir = os.path.dirname(iot_dir)
rt_dir = os.path.dirname(srv_dir)
kml2 = os.path.join(rt_dir, "ahmedabad_wards_map_2024.kml")
print(f"\nActual iot.py path: {iot_file}")
print(f"iot dir: {iot_dir}")
print(f"server dir: {srv_dir}")
print(f"root dir: {rt_dir}")
print(f"KML path: {kml2}")
print(f"KML exists: {os.path.exists(kml2)}")
