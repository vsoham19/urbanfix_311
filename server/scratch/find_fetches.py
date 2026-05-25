import os

file_path = r"c:\Users\vsoha\Desktop\Work\urbanfix\311\client\src\components\Dashboard.jsx"

if not os.path.exists(file_path):
    print("File not found")
else:
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    print(f"Total lines: {len(lines)}")
    for i, line in enumerate(lines, start=1):
        if "axios" in line or "fetch" in line or "http" in line or "localhost:8000" in line or "127.0.0.1" in line:
            print(f"{i}: {line.strip()[:120]}")
