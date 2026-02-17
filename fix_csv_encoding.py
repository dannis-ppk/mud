
import os
import codecs

data_dir = r"d:\dev\projects\MUD_the_age\data"
files = ["items.csv", "enemies.csv", "rooms.csv"]

for filename in files:
    path = os.path.join(data_dir, filename)
    if os.path.exists(path):
        try:
            # Read first to check if already has BOM or encoding
            with open(path, 'rb') as f:
                content = f.read()
            
            # If already has BOM, we can skip or rewrite, safer to rely on decode('utf-8') then encode('utf-8-sig')
            # But let's assume it's UTF-8 (written by my tool) without BOM.
            text = content.decode('utf-8')
            
            # Write back with BOM (utf-8-sig)
            with open(path, 'w', encoding='utf-8-sig', newline='') as f:
                f.write(text)
                
            print(f"Fixed encoding for: {filename}")
        except Exception as e:
            print(f"Error processing {filename}: {e}")
    else:
        print(f"File not found: {filename}")
