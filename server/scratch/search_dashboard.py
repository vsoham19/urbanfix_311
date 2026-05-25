import os
import re

server_dir = r"c:\Users\vsoha\Desktop\Work\urbanfix\311\server"
found = False

for root, dirs, files in os.walk(server_dir):
    if "scratch" in root or "__pycache__" in root or "venv" in root:
        continue
    for file in files:
        if file.endswith(".py"):
            file_path = os.path.join(root, file)
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            if "restaurant" in content.lower():
                found = True
                print(f"Found in {file}:")
                for idx, line in enumerate(content.splitlines(), start=1):
                    if "restaurant" in line.lower():
                        print(f"  Line {idx}: {line.strip()}")

if not found:
    print("[SUCCESS] Zero occurrences of 'restaurant' in the server directory (excluding scratch)!")
