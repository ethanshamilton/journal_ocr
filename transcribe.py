# transcribe.py
# functions for image transcription
import os
import base64
import logging
from PIL import Image
from io import BytesIO
from openai import OpenAI
from dotenv import load_dotenv
from pdf2image import convert_from_path

load_dotenv()
OPENAI_API_KEY=os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

def encode_image(image, output_format="PNG"):
    """ Encode a PIL Image object to base64 string. """
    buffered = BytesIO()
    image.save(buffered, format=output_format)
    encoded_image = base64.b64encode(buffered.getvalue()).decode('utf-8')
    return encoded_image

def convert_and_encode_pdf(pdf_path, output_format="PNG"):
    """ Convert PDF to images and encode them to base64 strings. """
    images = convert_from_path(pdf_path)
    return [encode_image(image, output_format) for image in images]

def check_image_size(encoded_image, max_size_mb=20):
    """ Ensure image doesn't exceed maximum file size. """
    img_bytes = base64.b64decode(encoded_image)
    size_mb = len(img_bytes) / (1024 * 1024)
    return size_mb <= max_size_mb

def verify_image(encoded_image):
    """ Verify that a base64 encoded image can be decoded. """
    image_data = base64.b64decode(encoded_image)
    image = Image.open(BytesIO(image_data))
    image.show()

def transcribe_images(b64str_images):
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
                            'text': 'Please transcribe this document.'
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
    return transcriptions