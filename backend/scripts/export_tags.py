import json

from core.navigation import extract_tags
from core.settings import settings

def main():
    tags = extract_tags(settings.file_storage.journal_storage_path, output_format="frequency")
    with open("tags_export.json", "w") as f:
        json.dump(tags, f, indent=2)
    print(f"Exported {len(tags)} tags to tags_export.json")

if __name__ == "__main__":
    main()
