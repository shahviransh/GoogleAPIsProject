import os
from googleapiclient.discovery import build
from google.cloud import speech, storage, videointelligence
from pydub import AudioSegment
import subprocess
from nltk.tokenize import sent_tokenize
import nltk
from dotenv import load_dotenv

nltk.download("punkt")
nltk.download("punkt_tab")

# Load the environment variables
load_dotenv()

# YouTube API setup
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)


# Google Cloud Storage setup
def upload_to_gcs(bucket_name, source_file_name, destination_blob_name):
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_filename(source_file_name)
    print(f"File {source_file_name} uploaded to {destination_blob_name}.")
    return f"gs://{bucket_name}/{destination_blob_name}"


# Fetch details of YouTube videos
def fetch_video_details(video_ids):
    request = youtube.videos().list(part="snippet", id=",".join(video_ids))
    response = request.execute()
    return [
        {"title": item["snippet"]["title"], "video_id": item["id"]}
        for item in response.get("items", [])
    ]


# Download video using youtube-dl
def download_video(video_url, output_path):
    try:
        if not os.path.exists("Videos"):
            os.makedirs("Videos")
        command = ["yt-dlp", video_url, "-o", output_path]
        subprocess.run(command, check=True)
        return output_path.replace("%(title)s", "*").replace(".%(ext)s", "*.mkv")
    except Exception as e:
        print(f"Error downloading video: {e}")
        return None


# Convert video to audio for transcription
def extract_audio(video_path, audio_path):
    try:
        video = AudioSegment.from_file(video_path)
        mono_audio = video.set_channels(1).set_sample_width(2)
        mono_audio.export(audio_path, format="wav")
        return audio_path
    except Exception as e:
        print(f"Error extracting audio: {e}")
        return None


# Transcribe audio using Google Speech-to-Text API
def transcribe_audio(gcs_uri):
    client = speech.SpeechClient()
    audio = speech.RecognitionAudio(uri=gcs_uri)
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16, language_code="en-US"
    )
    operation = client.long_running_recognize(config=config, audio=audio)
    print("Waiting for operation to complete...")
    response = operation.result(timeout=300)

    transcription = " ".join(
        [result.alternatives[0].transcript for result in response.results]
    )
    return transcription


# Analyze video using Google Video Intelligence API
def analyze_video(gcs_uri):
    client = videointelligence.VideoIntelligenceServiceClient()

    # Specify the features to analyze
    features = [
        videointelligence.Feature.OBJECT_TRACKING,
        videointelligence.Feature.LABEL_DETECTION,
    ]

    # Start video annotation
    operation = client.annotate_video(
        request={"features": features, "input_uri": gcs_uri}
    )
    print("Analyzing video... This may take a while.")
    results = operation.result(timeout=600)

    # Process the annotation results
    annotations = {
        "labels": [],
        "objects": [],
    }

    # Extract label annotations
    for label in results.annotation_results[0].segment_label_annotations:
        annotations["labels"].append(
            {
                "description": label.entity.description,
                "start_time": label.segments[
                    0
                ].segment.start_time_offset.total_seconds(),
                "end_time": label.segments[0].segment.end_time_offset.total_seconds(),
            }
        )

    # Extract object annotations
    for obj in results.annotation_results[0].object_annotations:
        annotations["objects"].append(
            {
                "entity": obj.entity.description,
                "start_time": obj.segment.start_time_offset.total_seconds(),
                "end_time": obj.segment.end_time_offset.total_seconds(),
            }
        )

    return annotations


# Combine transcription and video analysis
def combine_results(transcription, video_analysis):
    sentences = sent_tokenize(transcription)
    steps = []
    for label in video_analysis["labels"]:
        step = {
            "action": label["description"],
            "start_time": label["start_time"],
            "end_time": label["end_time"],
        }
        relevant_sentences = [
            s for s in sentences if label["description"].lower() in s.lower()
        ]
        step["description"] = (
            relevant_sentences[:1]
            if relevant_sentences
            else "No relevant description found."
        )
        steps.append(step)

    return steps


# Main function
def main():
    # Replace with actual video IDs
    video_ids = [os.getenv(f"YOUTUBE_ID_{i}") for i in range(1, 4)]
    video_details = fetch_video_details(video_ids)

    print("Fetched video details:")
    for video in video_details:
        print(f"{video['title']}")

    for video in video_details:
        video_url = f"https://www.youtube.com/watch?v={video['video_id']}"
        output_dir = "Videos"
        video_path = f"{output_dir}/{video['video_id']}.mkv"
        audio_path = f"{output_dir}/{video['video_id']}.wav"

        print(f"Downloading video: {video['title']}")
        downloaded_path = download_video(video_url, video_path)

        if downloaded_path:
            print(f"Extracting audio from video: {video['title']}")
            extracted_audio = extract_audio(downloaded_path, audio_path)

            print(f"Uploading audio to Google Cloud Storage: {video['title']}")
            gcs_uri_audio = upload_to_gcs(
                "bucket-for-video-analysis-viransh",
                extracted_audio,
                f"{video['video_id']}.wav",
            )

            print(f"Transcribing audio: {video['title']}")
            transcription = transcribe_audio(gcs_uri_audio)

            print(f"Uploading Video to Google Cloud Storage: {video['title']}")
            gcs_uri_video = upload_to_gcs(
                "bucket-for-video-analysis-viransh",
                downloaded_path,
                f"{video['video_id']}.mkv",
            )

            print(f"Analyzing video: {video['title']}")
            video_analysis = analyze_video(gcs_uri_video)

            print(f"Combining results for: {video['title']}")
            steps = combine_results(transcription, video_analysis)

            # Write the steps to a file
            with open(f"Steps/{video['title']}.txt", "w") as f:
                f.write(f"Steps for '{video['title']}':\n")
                for step in steps:
                    f.write(
                        f"- Action: {step['action']} (Time: {step['start_time']}s to {step['end_time']}s)\n"
                    )
                    f.write(f"  Description: {step['description']}\n")


if __name__ == "__main__":
    main()
