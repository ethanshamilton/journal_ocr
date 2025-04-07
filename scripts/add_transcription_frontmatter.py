# will add `transcription: "True"` to all .md notes in a directory
import os
import yaml

def add_frontmatter_to_md(file_path):
    with open(file_path, 'r') as f:
        content = f.read()

    if content.startswith("---"):
        # extract and parse existing frontmatter
        parts = content.split("---")
        frontmatter_raw = parts[1]
        body = "---".join(parts[2:])

        try:
            frontmatter = yaml.safe_load(frontmatter_raw)
        except yaml.YAMLError:
            print(f"Failed to parse frontmatter in {file_path}")

        # skip if already marked
        if frontmatter.get("transcription") == "True":
            print(f"{file_path} already transcribed...")
            return
        
        frontmatter["transcription"] = "True"
    else:
        frontmatter = {"transcription": "True"}
        body = content
    
    new_content = f"---\n{yaml.dump(frontmatter)}---\n{body.lstrip()}"
    with open(file_path, 'w') as f:
        f.write(new_content)
    print(f"Updated {file_path}")

def update_directory(directory):
    for root, _, files in os.walk(directory):
        for filename in files:
            if filename.lower().endswith(".md"):
                full_path = os.path.join(root, filename)
                add_frontmatter_to_md(full_path)

target_dir = '/Users/hamiltones/Documents/Journal/Daily Pages'
update_directory(target_dir)
