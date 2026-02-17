import csv

aliases = {}
commands_data = """command,aliases,description,usage
north,n,Move north,n
south,s,Move south,s
east,e,Move east,e
west,w,Move west,w
look,l,Look at surroundings,look
kill,k;attack;a,Attack an enemy,kill <enemy>
skill power,sp;p a,Power Attack (1.5x Dmg),sp <enemy>
"""

def load_commands():
    reader = csv.DictReader(commands_data.splitlines())
    for row in reader:
        cmd = row['command']
        aliases_list = row['aliases'].split(';') if row['aliases'] else []
        for alias in aliases_list:
            if alias:
                aliases[alias.strip()] = cmd
    return aliases

aliases = load_commands()
print(f"Loaded aliases: {aliases}")

def process(cmd):
    target_cmd = cmd
    sorted_aliases = sorted(aliases.keys(), key=len, reverse=True)
    
    match_found = False
    for alias in sorted_aliases:
        # Strict match or Startswith + space
        if cmd == alias or cmd.startswith(alias + " "):
            replacement = aliases[alias]
            args = cmd[len(alias):]
            target_cmd = replacement + args
            match_found = True
            print(f"Match found: '{alias}' -> '{replacement}'")
            print(f"Args preserved: '{args}'")
            break
            
    print(f"Input: '{cmd}' -> Result: '{target_cmd.strip()}'")

process("k rabbit")
process("sp rabbit")
process("p a rabbit")
process("kill rabbit")
