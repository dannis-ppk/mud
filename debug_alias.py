import csv
import os

def check_commands():
    path = "d:/dev/projects/MUD_the_age/data/commands.csv"
    print(f"Checking {path}...")
    
    aliases = {}
    
    with open(path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            cmd = row['command']
            print(f"Row cmd repr: {repr(cmd)}")
            
            # Simulate loading logic
            als = row['aliases'].split(';') if row['aliases'] else []
            for a in als:
                aliases[a.strip()] = cmd

    print("\nAlias Map:")
    for k, v in aliases.items():
        if k in ['sp', 'p a']:
            print(f"'{k}' -> {repr(v)}")

    # Simulate process_command Logic
    user_input = "sp rat"
    print(f"\nSimulating input: '{user_input}'")
    
    target_cmd = user_input
    sorted_aliases = sorted(aliases.keys(), key=len, reverse=True)
    
    matched = False
    for alias in sorted_aliases:
        if user_input == alias or user_input.startswith(alias + " "):
            replacement = aliases[alias]
            args = user_input[len(alias):]
            target_cmd = replacement + args
            print(f"Matched alias '{alias}'. Replacement='{replacement}'. Args='{args}'")
            print(f"Target Cmd: {repr(target_cmd)}")
            matched = True
            break
            
    if not matched:
        print("No alias match.")
        
    cmd = target_cmd.strip()
    print(f"Normalized Cmd: {repr(cmd)}")
    
    if cmd.startswith('skill '):
        # Simulate handle_skill call
        call_args = cmd.split(' ', 1)[1]
        print(f"Calling handle_skill with: {repr(call_args)}")
        
        # Simulate handle_skill logic
        # Sanitize
        s_args = call_args.replace('\xa0', ' ').replace('\t', ' ')
        print(f"Sanitized args: {repr(s_args)}")
        
        parts = s_args.strip().split(' ', 1)
        print(f"Parts: {parts}")
        
        skill_key = parts[0].lower()
        target_name = parts[1] if len(parts) > 1 else None
        
        print(f"Skill Key: {repr(skill_key)}")
        print(f"Target: {repr(target_name)}")
        
        if skill_key == "power":
            print("SUCCESS: Skill key matches 'power'")
        else:
            print("FAILURE: Skill key does not match 'power'")

if __name__ == "__main__":
    check_commands()
