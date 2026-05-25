file_path = r"c:\Users\vsoha\Desktop\Work\urbanfix\311\client\src\components\Dashboard.jsx"
with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
    content = f.read()

lines = content.splitlines()
print("Searching for predictorLabels in Dashboard.jsx...")
for idx, line in enumerate(lines, start=1):
    if "predictorLabels" in line:
        print(f"Line {idx:4d}: {line.strip()}")
