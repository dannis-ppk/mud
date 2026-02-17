
import os

path = "d:/dev/projects/MUD_the_age/data/skills.csv"

# Read existing content
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# Write back with BOM
with open(path, "w", encoding="utf-8-sig") as f:
    f.write(content)

print(f"Added BOM to {path}")
