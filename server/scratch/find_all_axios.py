import os
import re

client_src = r"c:\Users\vsoha\Desktop\Work\urbanfix\311\client\src"

for root, dirs, files in os.walk(client_src):
    for file in files:
        if file.endswith(".jsx") or file.endswith(".js"):
            file_path = os.path.join(root, file)
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            
            lines = content.splitlines()
            for idx, line in enumerate(lines, start=1):
                if "axios" in line.lower() or "fetch(" in line.lower():
                    print(f"{file} (Line {idx}): {line.strip()}")
