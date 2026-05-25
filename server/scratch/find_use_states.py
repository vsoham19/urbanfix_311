import os

file_path = r"c:\Users\vsoha\Desktop\Work\urbanfix\311\client\src\components\Dashboard.jsx"

if not os.path.exists(file_path):
    print("File not found")
else:
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    print(f"Total lines: {len(lines)}")
    for i, line in enumerate(lines, start=1):
        if "useState(" in line or "useEffect(" in line or "setIotSewerReadings" in line or "setStructured" in line:
            print(f"{i}: {line.strip()[:120]}")
