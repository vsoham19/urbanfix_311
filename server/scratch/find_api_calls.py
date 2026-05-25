import re

file_path = r"c:\Users\vsoha\Desktop\Work\urbanfix\311\client\src\components\Dashboard.jsx"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

print("Searching for predictive/run or related fetches in Dashboard.jsx...")
lines = content.splitlines()
for idx, line in enumerate(lines, start=1):
    if "predictive" in line.lower() or "fetch(" in line.lower() or "axios" in line.lower():
        print(f"Line {idx:4d}: {line.strip()}")
