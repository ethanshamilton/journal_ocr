# navigation.py
# this file contains all the functions for traversing the journal and
# ensuring data standardization.
import os
import re
import yaml
import shutil
import hashlib
import logging
from pathlib import Path
from typing import Literal
from collections import Counter

from core.models import UnprocessedDocs

page_template = """
#day
### Page
![[{filename}]]
"""

def crawl_journal_entries(root_dir:str="Daily Pages") -> UnprocessedDocs:
    """ Recursively crawl through journal directories and identifies entries that need to be transcribed or embedded. """
    to_transcribe = []
    to_embed = []

    def is_journal_entry(filename):
        """ Checks if the file is a journal entry, which are either PDF or image files. """
        valid_extensions = {'.pdf', '.png', '.jpg', '.jpeg'}
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
    return UnprocessedDocs(to_transcribe=to_transcribe, to_embed=to_embed)

def duplicate_folder(source_folder:str, target_folder:str) -> None:
    """ Delete target folder if it exists, then copy source folder to target folder. """
    # check if target folder exists and remove it
    if os.path.exists(target_folder):
        shutil.rmtree(target_folder)

    # copy source folder to target location
    shutil.copytree(source_folder, target_folder)

def _parse_frontmatter(content: str) -> dict:
    """Parse YAML frontmatter from markdown content. Returns empty dict if none."""
    lines = content.split("\n")
    if not lines or lines[0].strip() != "---":
        return {}
    yaml_lines = []
    for line in lines[1:]:
        if line.strip() == "---":
            break
        yaml_lines.append(line)
    try:
        return yaml.safe_load("\n".join(yaml_lines)) or {}
    except yaml.YAMLError:
        return {}

def strip_frontmatter(content: str) -> str:
    """Return markdown body with YAML frontmatter stripped."""
    if not content.startswith("---"):
        return content
    end = content.find("---", 3)
    if end == -1:
        return content
    return content[end + 3:].lstrip("\n")

def compute_content_hash(body: str) -> str:
    """SHA-256 hash of content body (frontmatter excluded)."""
    return hashlib.sha256(body.encode("utf-8")).hexdigest()

def crawl_evergreen_entries(root_dir: str) -> list[str]:
    """Find evergreen .md files that need (re-)embedding based on content hash."""
    to_embed = []

    if not os.path.exists(root_dir):
        logging.info(f"Evergreen directory not found: {root_dir}")
        return to_embed

    for dirpath, _, filenames in os.walk(root_dir):
        for filename in filenames:
            if not filename.endswith(".md"):
                continue
            full_path = os.path.join(dirpath, filename)

            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()

            body = strip_frontmatter(content)
            if not body.strip():
                logging.info(f"Skipping empty evergreen file: {full_path}")
                continue

            new_hash = compute_content_hash(body)
            frontmatter = _parse_frontmatter(content)

            if frontmatter.get("content_hash") != new_hash:
                to_embed.append(full_path)
                logging.info(f"Evergreen file needs embedding: {full_path}")

    logging.info(f"Found {len(to_embed)} evergreen entries to embed.")
    return to_embed

def extract_tags(
    root_dir: str,
    output_format: Literal["string", "frequency"] = "string"
) -> str | dict[str, int]:
    """ Extracts all tags from an Obsidian vault.

    Args:
        root_dir: Path to the vault directory
        output_format: "string" returns space-separated unique tags (default),
                      "frequency" returns dict with tag counts
    """
    vault_path = Path(root_dir)
    tag_pattern = re.compile(r"#([\w/-]+)")

    tag_counter: Counter[str] = Counter()
    for file in vault_path.rglob("*.md"):
        with open(file, "r", encoding="utf-8") as f:
            content = f.read()
            tag_counter.update(tag_pattern.findall(content))

    if output_format == "frequency":
        return dict(tag_counter.most_common())

    return " ".join(sorted(tag_counter.keys()))
