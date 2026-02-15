import json
from pathlib import Path

from core.navigation import extract_tags
from core.settings import settings

def main():
    project_root = Path(__file__).resolve().parent.parent.parent
    backend_path = project_root / "backend" / "tags_export.json"
    ui_path = project_root / "ui" / "public" / "tags.json"

    tags = extract_tags(settings.file_storage.journal_storage_path, output_format="frequency")

    for path in [backend_path, ui_path]:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(tags, f, indent=2)
        print(f"Exported {len(tags)} tags to {path}")

if __name__ == "__main__":
    main()
