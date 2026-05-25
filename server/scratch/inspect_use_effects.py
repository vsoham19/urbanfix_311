import os

file_path = r"c:\Users\vsoha\Desktop\Work\urbanfix\311\client\src\components\Dashboard.jsx"

if not os.path.exists(file_path):
    print("File not found")
else:
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    print(f"Total lines: {len(lines)}")
    
    # We want to view lines around 73, 284, 320, 339
    targets = [73, 284, 320, 339]
    for target in targets:
        print(f"\n--- useEffect starting at line {target} ---")
        for i in range(target - 1, min(target + 25, len(lines))):
            print(f"{i+1}: {lines[i].rstrip()}")
