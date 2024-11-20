import os
from google.cloud import vision
from google.cloud import translate_v3 as translate
from google.cloud import aiplatform
from google.cloud.aiplatform import gapic
from PIL import Image
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT")
image_prefix = os.getenv("IMAGE_PREFIX")

def extract_text_from_image(image_path):
    """Extract text from an image using Google Cloud Vision API."""
    try:
        # Initialize Vision API client
        client = vision.ImageAnnotatorClient()

        # Read the image file
        with open(image_path, 'rb') as image_file:
            content = image_file.read()

        # Create Vision API image object
        image = vision.Image(content=content)

        # Perform text detection
        response = client.text_detection(image=image)
        texts = response.text_annotations

        if response.error.message:
            raise Exception(f'Vision API Error: {response.error.message}')

        # Return detected text (full description)
        return texts[0].description.strip() if texts else None
    except Exception as e:
        print(f"Error extracting text: {e}")
        return None

def translate_text(text, target_language='en'):
    """Translate text using Google Cloud Translation API."""
    try:
        client = translate.TranslationServiceClient()
        lines = text.split('\n')  # Split by newlines
        parent = f"projects/{PROJECT_ID}/locations/global"
        translated_lines = client.translate_text(contents=[line for line in lines], target_language_code=target_language, parent=parent)
        return '\n'.join([x.translated_text for x in translated_lines.translations])
    except Exception as e:
        print(f"Error translating text: {e}")
        return None

def save_text_to_file(text, output_path):
    """Save text to a text file."""
    try:
        with open(output_path, 'w', encoding='utf-8') as file:
            file.write(text)
        print(f"Text saved to {output_path}")
    except Exception as e:
        print(f"Error saving text to file: {e}")

def generate_dynamic_html(file_paths, output_dir):
    """Generate an HTML file to dynamically display one text file at a time."""
    html_path = os.path.join(output_dir, "index.html")
    try:
        with open(html_path, 'w', encoding='utf-8') as html_file:
            html_file.write("<html><head><title>Novel Viewer</title>")
            html_file.write("<style>")
            html_file.write("""
                body {
                    font-family: Roboto, Arial, sans-serif;
                    margin: 2em auto;
                    max-width: 800px;
                    background-color: #fdf6e3;
                    color: #333;
                }
                .navigation {
                    display: flex;
                    justify-content: space-between;
                    margin-top: 2em;
                }
                .navigation button {
                    padding: 0.5em 1em;
                    background-color: #007BFF;
                    color: white;
                    border: none;
                    border-radius: 5px;
                    cursor: pointer;
                }
                .navigation button:hover {
                    background-color: #0056b3;
                }
                #content {
                    white-space: pre-wrap;
                    line-height: 2;
                }
            """)
            html_file.write("</style>")
            html_file.write("<script>")
            html_file.write(f"""
                let files = {file_paths};
                let currentIndex = 0;

                function loadFile(index) {{
                    if (index < 0 || index >= files.length) return;
                    fetch(files[index])
                        .then(response => response.text())
                        .then(data => {{
                            const formattedData = data.replace(/\\n\\n/g, '<br><br>').replace(/\\n/g, '<br>');
                            document.getElementById('content').innerHTML = formattedData;
                            currentIndex = index;
                            document.getElementById('pageNumber').innerText = 'Page ' + (346 + index);
                            document.getElementById('pageNumber2').innerText = 'Page ' + (346 + index);
                            localStorage.setItem('currentIndex', currentIndex);
                        }})
                        .catch(err => {{
                            console.error('Failed to load file:', err);
                        }});
                }}

                function nextPage() {{
                    if (currentIndex < files.length - 1) {{
                        loadFile(currentIndex + 1);
                        window.scrollTo(0, 0);
                    }}
                }}

                function prevPage() {{
                    if (currentIndex > 0) {{
                        loadFile(currentIndex - 1);
                        window.scrollTo(0, 0);
                    }}
                }}

                window.onload = () => {{
                    const savedIndex = localStorage.getItem('currentIndex');
                    if (savedIndex !== null) {{
                        loadFile(parseInt(savedIndex, 10));
                    }} else {{
                        loadFile(479 - 346); // Default page
                    }}

                    window.addEventListener("keydown", (event) => {{
                        if (event.key === "ArrowLeft") {{
                            prevPage();
                        }} else if (event.key === "ArrowRight") {{
                            nextPage();
                        }}
                    }});
                }};
            """)
            html_file.write("</script>")
            html_file.write("</head><body>")
            html_file.write("<h1>Novel Viewer</h1>")
            html_file.write("<span id='pageNumber'></span>")
            html_file.write("<div id='content'></div>")
            html_file.write("<div class='navigation'>")
            html_file.write("<button onclick='prevPage()'>Previous</button>")
            html_file.write("<span id='pageNumber2'></span>")
            html_file.write("<button onclick='nextPage()'>Next</button>")
            html_file.write("</div>")
            html_file.write("</body></html>")
        return html_path
    except Exception as e:
        print(f"Error generating dynamic HTML navigation: {e}")
        return None

# def format_text_with_gemini(translated_text):
#     """Formats translated text using the Gemini API."""

#     project_id = PROJECT_ID
#     location = "northamerica-northeast2"  # Replace with your location

#     # Initialize the Vertex AI client
#     aiplatform.init(project=project_id, location=location)

#     # Create a Gemini model instance
#     model = aiplatform.gapic.ModelServiceClient.create_model(
#         parent="projects/{}/locations/{}".format(project_id, location),
#         model={
#             "display_name": "my-gemini-model",
#             "model_type": "generative_text",
#             "model_version": "1.0",
#             "model_parameters": {
#                 "model_name": "text-davinci-003",  # Replace with the desired Gemini model
#                 "temperature": 0.7,  # Adjust for creativity
#                 "max_tokens": 4096,  # Maximum tokens in the output
#             },
#         },
#     )

#     # Define your prompt
#     prompt = f"""
#     Please format this text as a novel, ensuring correct quotation marks, and newlines.

#     {translated_text}
#     """

#     # Create a text generation request
#     request = gapic.types.GenerateTextRequest(
#         model=model.name,
#         prompt=prompt,
#         temperature=0.7,
#         max_output_tokens=4096,
#     )

#     # Send the request and get the response
#     response = aiplatform.gapic.ModelServiceClient.generate_text(request=request)

#     # Extract the formatted text from the response
#     formatted_text = response.candidates[0].content

#     return formatted_text

def process_images_to_texts(image_paths, output_dir):
    """Process multiple images, save extracted text, and create navigation."""
    text_dir = os.path.join(output_dir, "ExtractedTexts")
    os.makedirs(text_dir, exist_ok=True)

    saved_files = []
    for i, image_path in enumerate(image_paths):
        output_path = os.path.join(text_dir, f"Page_{i + 1}.txt")

        # Check if the text has already been extracted
        if os.path.exists(output_path):
            saved_files.append(output_path)
            continue

        # Extract text
        extracted_text = extract_text_from_image(image_path)
        if not extracted_text:
            print(f"No text extracted from {image_path}.")
            continue

        # Translate text
        translated_text = translate_text(extracted_text, target_language='en')
        if not translated_text:
            print(f"Translation failed for text from {image_path}.")
            continue

        # # Format the translated text using Gemini
        # formatted_text = format_text_with_gemini(translated_text)

        # Save the formatted text
        save_text_to_file(translated_text, output_path)
        saved_files.append(output_path)

    if saved_files:
        navigation_html = generate_dynamic_html(saved_files, output_dir)

def getLengthOfImages(path):
    count = 0
    # Get total number of images in the folder
    for _, _, files in os.walk(path):
        count += len(files)
    return count

if __name__ == "__main__":
    # Replace with your list of image paths
    dir_path = 'Gao Wu, Swallowed Star'

    image_paths = [
        f"{dir_path}\\Images GIF\\{image_prefix} ({i}).gif" for i in range(0, getLengthOfImages(os.path.join(dir_path,'Images GIF')))
    ]
    process_images_to_texts(image_paths, dir_path)
