import os
import src.navigation as navigation

SAMPLE_DATA_FOLDER = "data/sample_data"

def test_crawl_journal_entries():
    """ Test the `crawl_journal_entries() function using sample data. """
    journal_files = navigation.crawl_journal_entries(SAMPLE_DATA_FOLDER)

    # verify files found
    assert len(journal_files) > 0

    for source_file, md_file in journal_files['to_transcribe']:
        # verify source file exists
        assert os.path.exists(source_file)
        # verify markdown files exist or were created
        assert os.path.exists(md_file)
        assert md_file.endswith('.md')
        # validate naming on markdown files
        md_filename = os.path.basename(md_file)
        assert ' ' not in md_filename
        # verify markdown content
        with open(md_file) as f:
            content = f.read()
            assert '![[' in content
            assert os.path.basename(source_file) in content
