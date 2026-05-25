import re

file_path = r"c:\Users\vsoha\Desktop\Work\urbanfix\311\client\src\components\Dashboard.jsx"
with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
    content = f.read()

print("1. Searching for 'AI Executive Planning Insights Briefing' rendering in Dashboard.jsx...")
lines = content.splitlines()
for idx, line in enumerate(lines, start=1):
    if "AI Executive Planning Insights Briefing" in line or "aiBriefing" in line or "Briefing" in line:
        if "div" in line or "className" in line or "bg-" in line or "style" in line:
            print(f"Line {idx:4d}: {line.strip()}")

print("\n2. Searching for 'OLS Regression Scatter & Trendline' rendering in Dashboard.jsx...")
for idx, line in enumerate(lines, start=1):
    if "OLS Regression Scatter" in line or "Scatter & Trendline" in line:
        print(f"Line {idx:4d}: {line.strip()}")
