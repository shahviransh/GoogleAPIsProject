import os
from google.cloud import vision, storage
from google.cloud import translate_v3 as translate
import vertexai
from vertexai.generative_models import GenerativeModel
from PIL import Image
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
image_prefix = os.getenv("IMAGE_PREFIX")
missing_num = 3
dir_path = "Gao Wu, Swallowed Star"


def batch_extract_text_from_images(image_uris):
    """Extract text from multiple images using Google Cloud Vision API."""
    # Initialize Vision API client
    client = vision.ImageAnnotatorClient()

    # Create Vision API image objects using GCS URIs
    requests = [
        vision.AnnotateImageRequest(
            image=vision.Image(source=vision.ImageSource(image_uri=uri)),
            features=[vision.Feature(type_=vision.Feature.Type.TEXT_DETECTION)]
        )
        for uri in image_uris
    ]

    # Perform batch text detection
    response = client.batch_annotate_images(requests=requests)

    # Extract detected text for each image
    results = [
        res.text_annotations[0].description.strip() if res.text_annotations else None
        for res in response.responses
    ]

    return results


def upload_to_gcs(bucket_name, image_paths):
    """Upload files to Google Cloud Storage."""

    client = storage.Client()
    bucket = client.bucket(bucket_name)
    link_gs = []

    for image in image_paths:
        blob_name = os.path.split(image)[1]
        blob = bucket.blob(blob_name)
        link_gs.append(f"gs://{bucket_name}/{blob_name}")
        if blob.exists():
            print(f"Skipping {image}, already exists in {bucket_name}/{blob_name}")
            continue
        blob.upload_from_filename(image)
        print(f"File {image} uploaded to {blob_name}.")

    return link_gs


def translate_text(text, target_language="en"):
    """Translate text using Google Cloud Translation API."""
    try:
        client = translate.TranslationServiceClient()
        parent = f"projects/{PROJECT_ID}/locations/global"
        translated_lines = client.translate_text(
            contents=[text],
            target_language_code=target_language,
            parent=parent,
        )
        return translated_lines.translations[0].translated_text
    except Exception as e:
        print(f"Error translating text: {e}")
        return None


def save_text_to_file(text, output_path):
    """Save text to a text file."""
    try:
        with open(output_path, "w", encoding="utf-8") as file:
            file.write(text)
        print(f"Text saved to {output_path}")
    except Exception as e:
        print(f"Error saving text to file: {e}")


def generate_dynamic_html(file_paths, output_dir):
    """Generate an HTML file to dynamically display one text file at a time."""
    html_path = os.path.join(output_dir, "index.html")
    try:
        with open(html_path, "w", encoding="utf-8") as html_file:
            html_file.write("<html><head><title>Novel Viewer</title>")
            html_file.write("<style>")
            html_file.write(
                """
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
            """
            )
            html_file.write("</style>")
            html_file.write("<script>")
            html_file.write(
                f"""
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
            """
            )
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


def format_text_with_gemini(translated_text):
    """Formats translated text using the Gemini API."""

    project_id = PROJECT_ID
    location = "us-central1"

    # Initialize the Vertex AI client
    vertexai.init(project=project_id, location=location)

    model = GenerativeModel("gemini-1.5-pro-002")

    # Create a Gemini model instance
    response = model.generate_content(
        [
            f"""
            Please format this text as a novel, ensuring correct quotation marks, and newlines.

            {translated_text}
            """
        ]
    )

    return response.text


def process_images_to_texts(image_paths, output_dir):
    """Process multiple images, save extracted text, and create navigation."""
    text_dir = os.path.join(output_dir, "ExtractedTexts")
    os.makedirs(text_dir, exist_ok=True)

    saved_files = []

    raw_dir = [
        os.path.join(dir_path, "RawTexts", f"Page_{i + 1}.txt") for i in range(0, image_dir_len)
    ]

    # Check if the raw text file exists
    if not os.path.exists(raw_dir[0]):
        # Cloud Vision API has a limit of 16 images per request
        extracted_texts = []
        for i in range(0, len(image_paths), 16):
            temp = batch_extract_text_from_images(
                image_paths[i : i + 16]
            )
            extracted_texts.extend(temp)

        for j, extracted_text in enumerate(extracted_texts):
            save_text_to_file(
                extracted_text, os.path.join(dir_path, "RawTexts", f"Page_{j + 1}.txt")
            )
    else:
        extracted_texts = [
            open(file, "r", encoding="utf-8").read() for file in raw_dir
        ]

    for i, image_path in enumerate(image_paths):
        output_path = os.path.join(text_dir, f"Page_{i + 1}.txt")

        # Check if the text has already been extracted
        if os.path.exists(output_path):
            saved_files.append(output_path)
            continue

        # Extract text
        extracted_text = extracted_texts[i]
        if not extracted_text:
            print(f"No text extracted from {image_path}.")
            continue

        # Translate text
        translated_text = translate_text(extracted_text, target_language="en")
        if not translated_text:
            print(f"Translation failed for text from {image_path}.")
            continue

        # Format the translated text using Gemini
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


image_dir_len = getLengthOfImages(os.path.join(dir_path, "Images GIF"))

if __name__ == "__main__":

    image_paths = [
        os.path.join(dir_path, "Images GIF", f"{image_prefix} ({i}).gif")
        for i in range(0, image_dir_len+missing_num)
        if os.path.exists(
            os.path.join(dir_path, "Images GIF", f"{image_prefix} ({i}).gif")
        )
    ]

    image_paths = upload_to_gcs(
        f"{dir_path.lower().replace(', ', '-').replace(' ','-')}-images-gif",
        image_paths,
    )

    process_images_to_texts(image_paths, dir_path)
