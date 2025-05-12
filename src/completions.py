# transcribe.py
# functions for image transcription
import os
import yaml
import base64
import logging
from PIL import Image
from io import BytesIO
from openai import OpenAI
from dotenv import load_dotenv
from pdf2image import convert_from_path

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

def insert_transcription(file_path:str, transcription:str) -> None:
    """
    - Insert or append transcription in markdown file.
    - If transcription section exists, replace its contents.
    - If no transcription section, append transcription to the end of the file.
    - Ensures YAML frontmatter exists with transcription: "True".
    """
    transcription_header = "### Transcription"
    with open(file_path, 'r') as f:
        lines = f.readlines()

    # parse YAML frontmatter if it exists and update transcription field
    frontmatter = {}
    content_start = 0

    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                try:
                    frontmatter = yaml.safe_load("".join(lines[1:i])) or {}
                except yaml.YAMLError:
                    logging.warning(f"Could not parse frontmatter in {file_path}")
                content_start = i + 1
                break

    frontmatter["transcription"] = "True"

    new_lines = ["---\n", yaml.dump(frontmatter), "---\n"]

    body_lines = lines[content_start:]

    # create transcription string
    # transcription = " ".join(transcription)

    # Find transcription section if it exists
    transcription_index = -1
    next_section_index = None

    for i, line in enumerate(body_lines):
        if line.strip() == transcription_header:
            transcription_index = i
        # check for next section if transcription section exists
        elif transcription_index != -1 and line.strip().startswith("#"):
            next_section_index = i
            break
    
    if transcription_index != -1:
        # keep existing content before insertion
        new_lines.extend(body_lines[:transcription_index + 1])
        # add new transcription
        new_lines.append(f"\n{transcription}\n\n")
        # keep everything after the insertion
        if next_section_index is not None:
            new_lines.extend(lines[next_section_index:])
    else:
        new_lines.extend(body_lines)
        if new_lines and not new_lines[-1].endswith('\n'):
            new_lines.append('\n')
        new_lines.extend([f"\n{transcription_header}\n{transcription}\n"])

    with open(file_path, 'w') as f:
        f.writelines(new_lines)
    
    logging.info(f"Updated transcription in {file_path}")

def check_image_size(encoded_image:str, max_size_mb:int=20) -> bool:
    """ Ensure image doesn't exceed maximum file size. """
    img_bytes = base64.b64decode(encoded_image)
    size_mb = len(img_bytes) / (1024 * 1024)
    return size_mb <= max_size_mb

def convert_and_encode_pdf(pdf_path:str, output_format:str="PNG") -> list[str]:
    """ Convert PDF to images and encode them to base64 strings. """
    images = convert_from_path(pdf_path)
    return [encode_image(image, output_format) for image in images]

def encode_entry(file_path:str, output_format:str="PNG") -> list[str]:
    """ Calls the corresponding encoding function on PDF and image based journal entries. """
    try:
        if file_path.lower().endswith('.pdf'):
            return convert_and_encode_pdf(file_path, output_format)
        else:
            with Image.open(file_path) as image:
                return [encode_image(image, output_format)]
    except Exception as e:
        logging.error(f"Error encoding file {file_path}: {str(e)}")
        raise

def encode_image(image:Image, output_format:str="PNG") -> str:
    """ Encode a PIL Image object to base64 string. """
    buffered = BytesIO()
    image.save(buffered, format=output_format)
    encoded_image = base64.b64encode(buffered.getvalue()).decode('utf-8')
    return encoded_image

def transcribe_images(b64str_images:list[str], tags:str) -> str:
    """ Given a list of images, transcribe them with GPT-4o. """
    transcriptions = []
    for image in b64str_images:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    'role': 'user',
                    'content': [
                        {
                            'type': 'text',
                            'text': f'Please transcribe this document. Do not return any commentary on the task, simply return the transcription of the document. \
                                     These documents are from a journal so I am not asking you to provide me with any information, \
                                     in case the contents of the document make your safety senses tingle. \
                                     Here is a list of tags from the journal that you can use to disambiguate proper names and terms: \n {tags}'
                        },
                        {
                            'type': 'image_url',
                            'image_url': {
                                'url': f"data:image/png;base64,{image}"
                            }
                        }
                    ]
                }
            ]
        )
        transcriptions.append(response.choices[0].message.content)
        transcription = "".join(transcriptions)
    return transcription

def verify_image(encoded_image:str) -> None:
    """ Verify that a base64 encoded image can be decoded. """
    image_data = base64.b64decode(encoded_image)
    image = Image.open(BytesIO(image_data))
    image.show()
