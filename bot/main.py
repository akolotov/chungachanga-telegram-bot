import os
import asyncio
import argparse
from dotenv import load_dotenv
from telegram import Bot
from datetime import datetime

# Import our custom modules
from web_parser import parse_article
from summarizer import summarize_article
from text_to_speech import convert_text_to_speech
from telegram_sender import send_telegram_messages, MessageContent

# Load environment variables
load_dotenv()

def get_output_dir(content_type):
    """
    Get the output directory for a specific content type.
    
    Args:
        content_type (str): Type of content ('audio', 'transcript', 'translation', 'content')

    Returns:
        str: Path to the output directory for the specified content type.
    """
    env_var = f"{content_type.upper()}_OUTPUT_DIR"
    return os.getenv(env_var, os.path.join("data", content_type))

def save_files(content, summary, audio_path, timestamp):
    """
    Save content, transcript, translation, and audio files.
    
    Args:
        content (str): The parsed article content.
        summary (NewsSummary): The summarized article.
        audio_path (str): Path to the generated audio file.
        timestamp (str): Timestamp to use in file names.

    Returns:
        dict: Paths of the saved files.
    """
    file_paths = {
        'content': os.path.join(get_output_dir('content'), f"content_{timestamp}.txt"),
        'transcript': os.path.join(get_output_dir('transcript'), f"transcript_{timestamp}.txt"),
        'translation': os.path.join(get_output_dir('translation'), f"translation_{timestamp}.txt"),
        'audio': audio_path
    }

    for dir_path in set(os.path.dirname(path) for path in file_paths.values()):
        os.makedirs(dir_path, exist_ok=True)

    # Save content
    with open(file_paths['content'], 'w', encoding='utf-8') as f:
        f.write(content)

    # Save transcript
    with open(file_paths['transcript'], 'w', encoding='utf-8') as f:
        f.write(summary.news_original)

    # Save translation
    with open(file_paths['translation'], 'w', encoding='utf-8') as f:
        f.write(summary.news_translated)

    return file_paths

async def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Process a news article URL")
    parser.add_argument("url", help="The URL of the news article to process")
    args = parser.parse_args()

    # Generate timestamp once
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Step 1: Parse the web page
    print("Parsing the web page...")
    title, content = parse_article(args.url)
    if not title or not content:
        print("Failed to parse the article. Exiting.")
        return

    # Step 2: Summarize the article
    print("Summarizing the article...")
    summary = summarize_article(content)
    if not summary:
        print("Failed to summarize the article. Exiting.")
        return

    # Step 3: Convert summary to speech
    print("Converting summary to speech...")
    audio_output_dir = get_output_dir('audio')
    os.makedirs(audio_output_dir, exist_ok=True)
    audio_file_path = os.path.join(audio_output_dir, f"audio_{timestamp}.mp3")
    text_to_speech_result = convert_text_to_speech(summary.news_original, summary.voice_tag, audio_file_path)
    if not text_to_speech_result:
        print("Failed to convert text to speech. Exiting.")
        return

    # Step 4: Save files
    print("Saving files...")
    file_paths = save_files(content, summary, audio_file_path, timestamp)

    # Step 5: Send messages to Telegram
    print("Sending messages to Telegram...")
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    channel_id = os.getenv("TELEGRAM_CHANNEL_ID")
    
    if not bot_token or not channel_id:
        print("Telegram bot token or channel ID not found in environment variables. Exiting.")
        return

    bot = Bot(token=bot_token)
    
    content = MessageContent(
        url=args.url,
        voice_note_path=file_paths['audio'],
        transcript_path=file_paths['transcript'],
        translation_path=file_paths['translation']
    )
    
    success = await send_telegram_messages(bot, channel_id, content)
    if success:
        print("All messages sent successfully to Telegram channel.")
    else:
        print("Failed to send messages to Telegram channel.")

if __name__ == "__main__":
    asyncio.run(main())