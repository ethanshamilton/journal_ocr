# personalities.py
# Load and classify personality prompts from markdown files
import logging
from pathlib import Path

from pydantic import BaseModel

from core.navigation import _parse_frontmatter, strip_frontmatter
from core.settings import settings

logger = logging.getLogger(__name__)


class Personality(BaseModel):
    title: str
    description: str
    prompt: str


def load_personalities(directory: str | None = None) -> list[Personality]:
    """Load personality definitions from markdown files in the given directory.

    Each file should have YAML frontmatter with a `description` field,
    and the body is the personality prompt. The filename (sans .md) is the title.
    """
    dir_path = Path(directory or settings.file_storage.personality_storage_path)
    personalities: list[Personality] = []

    if not dir_path.exists():
        logger.info(f"Personality directory not found: {dir_path}")
        return personalities

    for md_file in sorted(dir_path.glob("*.md")):
        try:
            content = md_file.read_text(encoding="utf-8")
            frontmatter = _parse_frontmatter(content)
            body = strip_frontmatter(content).strip()

            description = frontmatter.get("description", "")
            if not description:
                logger.warning(f"Personality file {md_file.name} missing description in frontmatter, skipping")
                continue
            if not body:
                logger.warning(f"Personality file {md_file.name} has no prompt body, skipping")
                continue

            personalities.append(Personality(
                title=md_file.stem,
                description=description,
                prompt=body,
            ))
        except Exception as e:
            logger.error(f"Error loading personality file {md_file.name}: {e}")

    logger.info(f"Loaded {len(personalities)} personalities from {dir_path}")
    return personalities
