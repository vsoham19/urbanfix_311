import os

file_path = r"c:\Users\vsoha\Desktop\Work\urbanfix\311\client\src\components\Dashboard.jsx"

if not os.path.exists(file_path):
    print("File not found")
else:
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    print(f"Total lines: {len(lines)}")
    # Print the first 25 lines of imports
    for i in range(25):
        if i < len(lines):
            print(f"{i+1}: {lines[i].rstrip()}")
