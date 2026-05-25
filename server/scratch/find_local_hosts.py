import re

file_path = r"c:\Users\vsoha\Desktop\Work\urbanfix\311\client\src\components\Dashboard.jsx"
with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
    content = f.read()

# Find any line that contains axios.get or axios.post or fetch
print("Listing all API call lines in Dashboard.jsx:")
for idx, line in enumerate(content.splitlines(), start=1):
    if "axios." in line or "fetch(" in line:
        print(f"Line {idx:4d}: {line.strip()}")
