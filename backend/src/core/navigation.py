# navigation.py
# this file contains all the functions for traversing the journal and
# ensuring data standardization.
import os
import re
import yaml
import shutil
import logging
from pathlib import Path

page_template = """
#day
### Page
![[{filename}]]
"""

def crawl_journal_entries(root_dir:str="Daily Pages") -> dict[list[tuple[str, str]], list[str]]:
    """ Recursively crawl through journal directories and identifies entries that need to be transcribed or embedded. """
    to_transcribe = []
    to_embed = []

    def is_journal_entry(filename):
        """ Checks if the file is a journal entry, which are either PDF or image files. """
        valid_extensions = {'.pdf', '.png', 'jpg', '.jpeg'}
        return any(filename.lower().endswith(ext) for ext in valid_extensions)

    def get_markdown_path(entry_path):
        """ Generate corresponding markdown file path for a journal entry. """
        directory = os.path.dirname(entry_path)
        filename = os.path.basename(entry_path)
        # Extract just the date part (removes AM/PM and extension)
        date_part = filename.split()[0]
        return os.path.join(directory, f"{date_part}.md")

    def check_frontmatter(md_path: str) -> dict:
        """Returns a dict {transcription: bool, embedding: bool} based on YAML frontmatter."""
        result = {"transcription": False, "embedding": False}
        if not os.path.exists(md_path):
            return result
        with open(md_path, 'r') as f:
            lines = f.readlines()

        if not lines or lines[0].strip() != "---":
            return result

        yaml_lines = []
        for line in lines[1:]:
            if line.strip() == "---":
                break
            yaml_lines.append(line)
        try:
            frontmatter = yaml.safe_load("".join(yaml_lines)) or {}
            if frontmatter.get("transcription") == "True":
                result["transcription"] = True
            if frontmatter.get("embedding") == "True":
                result["embedding"] = True
        except yaml.YAMLError:
            pass
        return result

    def process_directory(current_dir):
        """ Recursively process directories to find journal entries. """
        for item in os.listdir(current_dir):
            full_path = os.path.join(current_dir, item)

            if os.path.isdir(full_path):
                process_directory(full_path)
            elif is_journal_entry(item):
                md_path = get_markdown_path(full_path)
                if not os.path.exists(md_path):
                    with open(md_path, 'w') as f:
                        f.write(page_template.format(filename=item))
                    logging.info(f"Created new markdown file: {md_path}")

                # only add note to list if transcription isn't true in frontmatter
                frontmatter = check_frontmatter(md_path)
                if not frontmatter['transcription']:
                    to_transcribe.append((full_path, md_path))
                    logging.info(f"Added {full_path} to transcribe list")
                if not frontmatter['embedding']:
                    to_embed.append(md_path)
                    logging.info(f"Added {full_path} to embedding list")

    try:
        process_directory(root_dir)
        logging.info(f"Found {len(to_transcribe)} entries to transcribe and {len(to_embed)} entries to embed.")
    except Exception as e:
        logging.error(f"Error: {str(e)}")
        raise
    return { "to_transcribe": to_transcribe, "to_embed": to_embed }

def duplicate_folder(source_folder:str, target_folder:str) -> None:
    """ Delete target folder if it exists, then copy source folder to target folder. """
    # check if target folder exists and remove it
    if os.path.exists(target_folder):
        shutil.rmtree(target_folder)

    # copy source folder to target location
    shutil.copytree(source_folder, target_folder)

def extract_tags(root_dir: str) -> str:
    """ Extracts all tags from an Obsidian vault. """
    vault_path = Path(root_dir)
    tag_pattern = re.compile(r"#([\w/-]+)")

    tags = set()
    for file in vault_path.rglob("*.md"):
        with open(file, "r", encoding="utf-8") as f:
            content = f.read()
            tags.update(tag_pattern.findall(content))

    all_tags = sorted(tags)
    return " ".join(all_tags)
