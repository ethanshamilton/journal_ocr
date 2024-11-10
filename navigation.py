# navigation.py
# this file contains all the functions for traversing the journal and
# ensuring data standardization. 
import os
import logging

page_template = """
#day
### Page
![[{filename}]]
"""

def crawl_journal_entries(root_dir:str="Daily Pages"):
    """ Recursively crawl through journal directories and identifies entries that need to be transcribed. """
    journal_files = []

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
                
                journal_files.append((full_path, md_path))
                logging.info(f"Found journal entry: {full_path}")
    
    try:
        process_directory(root_dir)
        logging.info(f"Found {len(journal_files)} entries to process.")
    except Exception as e:
        logging.error(f"Error: {str(e)}")
        raise
    return journal_files
