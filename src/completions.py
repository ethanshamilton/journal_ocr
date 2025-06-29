# transcribe.py
# functions for image transcription
import os
import yaml
import time
import base64
import logging
import anthropic
from PIL import Image
from io import BytesIO
from google import genai
from openai import OpenAI
from baml_client import b
from dotenv import load_dotenv
from pdf2image import convert_from_path

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
openai_client = OpenAI(api_key=OPENAI_API_KEY)
google_client = genai.Client(api_key=GOOGLE_API_KEY)

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

def get_embedding(text: str) -> list[float]:
    """Runs text transcription through Gemini embedding model, retrying on 429 errors."""
    try:
        response = google_client.models.embed_content(
            model="gemini-embedding-exp-03-07",
            contents=text,
        )
        return response.embeddings[0].values
    except Exception as _:
        print("Rate limited... retrying in 5")
        time.sleep(5)
        get_embedding(text)

def insert_transcription(file_path: str, transcription: str) -> None:
    """
    - Insert or append transcription in markdown file.
    - If transcription section exists, replace its contents.
    - If no transcription section, append transcription to the end of the file.
    - Ensures YAML frontmatter exists with transcription: "True".
    """
    transcription_header = "### Transcription"

    # Ensure YAML frontmatter has transcription: "True"
    update_frontmatter_field(file_path, "transcription", "True")

    with open(file_path, 'r') as f:
        lines = f.readlines()

    # Locate start of content after frontmatter
    content_start = 0
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                content_start = i + 1
                break

    body_lines = lines[content_start:]
    transcription_index = -1
    next_section_index = None

    for i, line in enumerate(body_lines):
        if line.strip() == transcription_header:
            transcription_index = i
        elif transcription_index != -1 and line.strip().startswith("#"):
            next_section_index = i
            break

    # Reconstruct new body with updated transcription
    new_body = []
    if transcription_index != -1:
        new_body.extend(body_lines[:transcription_index + 1])
        new_body.append(f"\n{transcription}\n\n")
        if next_section_index is not None:
            new_body.extend(body_lines[next_section_index:])
    else:
        new_body = body_lines
        if new_body and not new_body[-1].endswith('\n'):
            new_body.append('\n')
        new_body.extend([f"\n{transcription_header}\n{transcription}\n"])

    # Replace everything after frontmatter with new_body
    new_lines = lines[:content_start] + new_body

    with open(file_path, 'w') as f:
        f.writelines(new_lines)

    logging.info(f"Updated transcription in {file_path}")

def intent_classifier(query: str) -> str:
    return b.IntentClassifier(query)

def query_llm(prompt: str, provider: str, model: str):
    """ Query any of the supported LLM providers and models. """
    if provider == "anthropic":
        return anthropic.Anthropic().messages.create(
            model=model,
            max_tokens=1024,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

def transcribe_images(b64str_images:list[str], tags:str) -> str:
    """ Given a list of images, transcribe them with GPT-4o. """
    transcriptions = []
    for image in b64str_images:
        response = openai_client.chat.completions.create(
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

def update_frontmatter_field(file_path: str, field: str, value: str) -> None:
    """Updates (or creates) a field in the YAML frontmatter of a markdown file."""
    with open(file_path, 'r') as f:
        lines = f.readlines()

    frontmatter = {}
    content_start = 0

    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                try:
                    frontmatter = yaml.safe_load("".join(lines[1:i])) or {}
                except yaml.YAMLError:
                    logging.warning(f"Could not parse frontmatter in {file_path}")
                    frontmatter = {}
                content_start = i + 1
                break
    else:
        content_start = 0

    frontmatter[field] = value
    new_lines = ["---\n", yaml.dump(frontmatter), "---\n"]
    new_lines.extend(lines[content_start:])

    with open(file_path, 'w') as f:
        f.writelines(new_lines)

def verify_image(encoded_image:str) -> None:
    """ Verify that a base64 encoded image can be decoded. """
    image_data = base64.b64decode(encoded_image)
    image = Image.open(BytesIO(image_data))
    image.show()
