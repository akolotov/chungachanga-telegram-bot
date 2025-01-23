import logging
import os

from bot.llm import initialize

from .main import transcribe_and_split
from .helper import ensure_video_cache_dir, extract_video_id

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)

    # Initialize Google AI API
    initialize()

    # Get YouTube URL from environment
    yt_link = os.getenv("YT_LINK", "")
    if not yt_link:
        print("YT_LINK environment variable is not set. Please set it in your environment or in a .env file.")
        exit(1)

    # Extract video ID and ensure output directory exists
    video_id = extract_video_id(yt_link)
    if not video_id:
        print(f"Invalid YouTube URL: {yt_link}")
        exit(1)

    # Get output directory
    output_dir = ensure_video_cache_dir(video_id)

    # Process video and get captured stories
    captured_stories = transcribe_and_split(yt_link, output_dir)
    
    if captured_stories:
        print(f"\nSuccessfully processed {len(captured_stories)} stories:")
        for story in captured_stories:
            print(f"\nText: '{story.text}'")
            print(f"Audio file: {story.audio}")
            print(f"YouTube URL: {story.url}")
    else:
        print("No stories were processed successfully.")
