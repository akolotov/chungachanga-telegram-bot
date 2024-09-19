import os
import logging
from dotenv import load_dotenv
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from datetime import datetime, timezone

# Import our custom modules
from web_parser import parse_article
from summarizer import summarize_article
from text_to_speech import convert_text_to_speech
from telegram_sender import send_telegram_messages, MessageContent
from content_db import ContentDB

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Silence specific loggers
logging.getLogger("httpx").setLevel(logging.WARNING)

# Load environment variables
load_dotenv()

# Get environment variables
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")
OPERATORS = os.getenv("TELEGRAM_OPERATORS", "").split(",")
DISABLE_VOICE_NOTES = os.getenv("DISABLE_VOICE_NOTES", "false").lower() == "true"

# Initialize ContentDB
content_db = ContentDB(os.getenv("CONTENT_DB", os.path.join("data", "content_db.json")))

# Dictionary to store the current MessageContent for each operator
operator_content = {}

def get_output_dir(content_type):
    """Get the output directory for a specific content type."""
    env_var = f"{content_type.upper()}_OUTPUT_DIR"
    return os.getenv(env_var, os.path.join("data", content_type))

def save_files(content, summary, audio_path, timestamp):
    """Save content, transcript, translation, and audio files."""
    file_paths = {
        'content': os.path.join(get_output_dir('content'), f"content_{timestamp}.txt"),
        'transcript': os.path.join(get_output_dir('transcript'), f"transcript_{timestamp}.txt"),
        'translation': os.path.join(get_output_dir('translation'), f"translation_{timestamp}.txt"),
        'audio': audio_path if audio_path else ""  # Set to empty string if no audio path
    }

    # Create directories only for non-empty paths
    for key, path in file_paths.items():
        if path:  # Only create directory if path is not empty
            dir_path = os.path.dirname(path)
            os.makedirs(dir_path, exist_ok=True)

    with open(file_paths['content'], 'w', encoding='utf-8') as f:
        f.write(content)
    with open(file_paths['transcript'], 'w', encoding='utf-8') as f:
        f.write(summary.news_original)
    with open(file_paths['translation'], 'w', encoding='utf-8') as f:
        f.write(summary.news_translated)

    return file_paths

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    if str(update.effective_user.id) not in OPERATORS:
        return
    await update.message.reply_text('Welcome! Send me a URL to process.')

async def process_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process the URL sent by the operator."""
    user_id = str(update.effective_user.id)
    
    if user_id not in OPERATORS:
        return

    url = update.message.text

    # Check if content already exists in the database
    existing_content = content_db.get_content(url)
    if existing_content:
        logger.info(f"Content for {url} already exists.")
        await update.message.reply_text("Content for this URL already exists. Retrieving...")
        file_paths = existing_content
        text_to_speech_result = None
    else:
        await update.message.reply_text("Processing the URL...")
        timestamp = update.message.date.strftime("%Y%m%d_%H%M%S")

        # Step 1: Parse the web page
        logger.info(f"Requesting the article from {url}.")
        title, content = parse_article(url)
        if not title or not content:
            await update.message.reply_text("Failed to parse the article. Please try another URL.")
            return

        # Step 2: Summarize the article
        logger.info(f"Handling the article with OpenAI.")
        summary = summarize_article(content)
        if not summary:
            await update.message.reply_text("Failed to summarize the article. Please try another URL.")
            return

        # Step 3: Convert summary to speech (if enabled)
        audio_file_path = ""
        text_to_speech_result = None
        if not DISABLE_VOICE_NOTES:
            audio_output_dir = get_output_dir('audio')
            os.makedirs(audio_output_dir, exist_ok=True)
            audio_file_path = os.path.join(audio_output_dir, f"audio_{timestamp}.mp3")
            logger.info(f"Sending a request to ElevenLabs to create a voice note.")
            text_to_speech_result = convert_text_to_speech(summary.news_original, summary.voice_tag, audio_file_path)
            if not text_to_speech_result:
                await update.message.reply_text("Failed to convert text to speech. Continuing without voice note.")

        # Step 4: Save files
        logger.info(f"Saving files with timestamp {timestamp}.")
        file_paths = save_files(content, summary, audio_file_path, timestamp)

        # Add content to the database
        logger.info(f"Updating the content DB.")
        content_db.add_content(url, file_paths)

    # Step 5: Send files to operator
    if file_paths['audio'] and os.path.exists(file_paths['audio']):
        with open(file_paths['audio'], 'rb') as audio:
            if text_to_speech_result:
                # Format the reset date
                reset_date = datetime.fromtimestamp(text_to_speech_result['next_reset_timestamp'], tz=timezone.utc).strftime("%Y-%m-%d")
                
                caption = (f"Used tokens: {text_to_speech_result['used_tokens']}\n"
                           f"Remaining characters: {text_to_speech_result['remaining_characters']}\n"
                           f"Next reset date: {reset_date}")
                
                await update.message.reply_voice(audio, caption=caption)
            else:
                await update.message.reply_voice(audio)
    elif DISABLE_VOICE_NOTES:
        await update.message.reply_text("Voice note generation is disabled.")
    else:
        await update.message.reply_text("Voice note is not available for this content.")
    
    with open(file_paths['transcript'], 'r', encoding='utf-8') as f:
        transcript = f.read()
        transcript_length = len(transcript)
        await update.message.reply_text(
            f"Transcript (length: {transcript_length} characters):\n\n{transcript}"
        )
    
    with open(file_paths['translation'], 'r', encoding='utf-8') as f:
        await update.message.reply_text(f"Translation:\n\n{f.read()}")

    # Store current content for this specific operator
    operator_content[user_id] = MessageContent(
        url=url,
        voice_note_path=file_paths['audio'],
        transcript_path=file_paths['transcript'],
        translation_path=file_paths['translation']
    )

    # Create inline keyboard for confirmation
    keyboard = [
        [
            InlineKeyboardButton("Yes", callback_data='confirm_yes'),
            InlineKeyboardButton("No", callback_data='confirm_no')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text("Is this content OK to send to the channel?", reply_markup=reply_markup)

async def handle_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the operator's confirmation to send content to the channel."""
    query = update.callback_query
    await query.answer()

    user_id = str(query.from_user.id)
    
    if user_id not in OPERATORS:
        return

    if user_id not in operator_content or operator_content[user_id] is None:
        await query.edit_message_text("No content to send. Please process a URL first.")
        return

    if query.data == 'confirm_yes':
        bot = context.bot
        logger.info(f"Sending content for content with URL: {operator_content[user_id].url} to the channel.")
        success = await send_telegram_messages(bot, CHANNEL_ID, operator_content[user_id])
        if success:
            await query.edit_message_text("Content sent to the channel successfully.")
        else:
            await query.edit_message_text("Failed to send content to the channel.")
    else:
        await query.edit_message_text("Content not sent to the channel.")

    # Clear the content for this operator
    operator_content[user_id] = None
    await query.message.reply_text("Send me another URL to process.")

def main():
    """Start the bot."""
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_url))
    application.add_handler(CallbackQueryHandler(handle_confirmation))

    logger.info(f"Start the bot.")

    application.run_polling()

if __name__ == "__main__":
    main()