import os

file_path = r"c:\Users\vsoha\Desktop\Work\urbanfix\311\client\src\components\Dashboard.jsx"

if not os.path.exists(file_path):
    print("File not found")
else:
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    print(f"Total lines: {len(lines)}")
    # Find "export default function Dashboard" and the next 40 lines
    found = False
    for i, line in enumerate(lines):
        if "export default function Dashboard" in line:
            found = True
            print(f"Found on line {i+1}:")
            for j in range(i, min(i + 50, len(lines))):
                print(f"{j+1}: {lines[j].rstrip()}")
            break
