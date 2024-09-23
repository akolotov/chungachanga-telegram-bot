import os
import logging
import asyncio
from collections import defaultdict
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot, InputFile
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.helpers import escape_markdown
from telegram.constants import ParseMode
from telegram.error import TelegramError
from datetime import datetime, timezone

# Import our custom modules
from web_parser import parse_article
from summarizer import summarize_article
from text_to_speech import convert_text_to_speech
from content_db import ContentDB, VocabularyItem
from helper import format_vocabulary, trim_message

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
DISCUSSION_GROUP_ID = os.getenv("TELEGRAM_DISCUSSION_GROUP_ID")
OPERATORS = os.getenv("TELEGRAM_OPERATORS", "").split(",")
DISABLE_VOICE_NOTES = os.getenv("DISABLE_VOICE_NOTES", "false").lower() == "true"

# Initialize ContentDB
content_db = ContentDB(os.getenv("CONTENT_DB", os.path.join("data", "content_db.json")))

@dataclass
class OperatorMessageContext:
    url: str
    voice_note_path: str
    transcript_path: str
    translation_path: str
    vocabulary: Optional[List[VocabularyItem]] = None
    operator_chat_id: int = None
    operator_message_id: int = None
    job_name: str = None

# Dictionary to store the current OperatorMessageContext for each operator
operator_contexts: Dict[int, OperatorMessageContext] = {}
channel_messages: Dict[int, Dict[int, Any]] = defaultdict(dict)

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
        'audio': audio_path if audio_path else ""
    }

    for key, path in file_paths.items():
        if path:
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
    user_id = update.effective_user.id
    if str(user_id) not in OPERATORS:
        return
    await update.message.reply_text('Welcome! Send me a URL to process.')

async def process_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process the URL sent by the operator."""
    user_id = update.effective_user.id
    
    if str(user_id) not in OPERATORS:
        return

    url = update.message.text

    # Check if content already exists in the database
    existing_content = content_db.get_content(url)
    if existing_content:
        logger.info(f"Content for {url} already exists.")
        await update.message.reply_text("Content for this URL already exists. Retrieving...")
        file_paths = existing_content
        text_to_speech_result = None
        vocabulary = existing_content.get("vocabulary")
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

        vocabulary = summary.vocabulary

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
                audio_file_path = ""
                await update.message.reply_text("Failed to convert text to speech. Continuing without voice note.")

        # Step 4: Save files
        logger.info(f"Saving files with timestamp {timestamp}.")
        file_paths = save_files(content, summary, audio_file_path, timestamp)

        # Add content to the database
        logger.info(f"Updating the content DB.")
        content_db.add_content(url, file_paths, vocabulary)

    # Step 5: Send files to operator
    # Send vocabulary
    if vocabulary:
        formatted_vocabulary = format_vocabulary(vocabulary)
        vocabulary_message = f"Useful for understanding vocabulary:\n\n{formatted_vocabulary}"
        
        await update.message.reply_text(
            trim_message(vocabulary_message),
            parse_mode=ParseMode.MARKDOWN_V2
        )

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
    operator_contexts[user_id] = OperatorMessageContext(
        url=url,
        voice_note_path=file_paths['audio'],
        transcript_path=file_paths['transcript'],
        translation_path=file_paths['translation'],
        vocabulary=vocabulary,
        operator_chat_id=update.effective_chat.id
    )

    # Create inline keyboard for confirmation
    keyboard = [
        [
            InlineKeyboardButton("Yes", callback_data='confirm_yes'),
            InlineKeyboardButton("No", callback_data='confirm_no')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    message = await update.message.reply_text("Is this content OK to send to the channel?", reply_markup=reply_markup)
    operator_contexts[user_id].operator_message_id = message.message_id

async def handle_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the operator's confirmation to send content to the channel."""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    
    if str(user_id) not in OPERATORS:
        return

    if user_id not in operator_contexts or operator_contexts[user_id] is None:
        await query.edit_message_text("No content to send. Please process a URL first.")
        return

    if query.data == 'confirm_yes':
        bot = context.bot
        operator_context = operator_contexts[user_id]

        logger.info(f"Handling the confirmation for the context {operator_context.url}.")
        
        try:
            # Send voice note if path is provided and file exists
            if operator_context.voice_note_path and os.path.exists(operator_context.voice_note_path):
            # Send voice note with vocabulary as caption
                with open(operator_context.voice_note_path, 'rb') as voice_note:
                    if operator_context.vocabulary:
                        formatted_vocabulary = format_vocabulary(operator_context.vocabulary)
                        vocabulary_message = f"Palabras para entender el audio:\n{formatted_vocabulary}"
                        
                        message = await bot.send_voice(
                            chat_id=CHANNEL_ID,
                            voice=InputFile(voice_note),
                            caption=trim_message(vocabulary_message),
                            parse_mode=ParseMode.MARKDOWN_V2
                        )
                    else:
                        message = await bot.send_voice(
                            chat_id=CHANNEL_ID,
                            voice=InputFile(voice_note)
                        )

                    logger.info(f"Voice note sent to the channel.")
            else:
                # Send vocabulary if available
                if operator_context.vocabulary:
                    formatted_vocabulary = format_vocabulary(operator_context.vocabulary)
                    vocabulary_message = f"Palabras para entender la noticia:\n{formatted_vocabulary}"
                else:
                    vocabulary_message = "DEBUG: No vocabulary available."
                    
                message = await bot.send_message(
                    chat_id=CHANNEL_ID,
                    text=trim_message(vocabulary_message),
                    parse_mode=ParseMode.MARKDOWN_V2
                )

                logger.info(f"Only vocabulary sent to the channel.")
            
            # Store message content for later use
            channel_messages[user_id][message.message_id] = operator_context
            
            # Schedule job to clear message data
            job_name = f'clear_{user_id}_{message.message_id}'
            operator_context.job_name = job_name
            context.job_queue.run_once(clear_message_data, 60, data={'user_id': user_id, 'message_id': message.message_id}, name=job_name)
            
            await query.edit_message_text("Voice note sent to the channel. Waiting for it to appear in the discussion group...")
        except TelegramError as e:
            logger.error(f"Failed to send message to channel: {e}")
            await query.edit_message_text("Failed to send content to the channel.")
    else:
        await query.edit_message_text("Content not sent to the channel.")

    # Clear the content for this operator
    operator_contexts[user_id] = None

    await query.message.reply_text("Send me another URL to process.")

async def clear_message_data(context: ContextTypes.DEFAULT_TYPE):
    user_id = context.job.data['user_id']
    message_id = context.job.data['message_id']
    if user_id in channel_messages:
        channel_messages[user_id].pop(message_id, None)
        if not channel_messages[user_id]:
            channel_messages.pop(user_id, None)

async def handle_forwarded_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message

    discussion_group = await context.bot.get_chat(DISCUSSION_GROUP_ID)

    logger.info(f"A forwarded message in {discussion_group.id} discovered.")

    if message.chat.id != discussion_group.id:
        return

    channel = await context.bot.get_chat(CHANNEL_ID)

    if (message.forward_origin and 
        message.forward_origin.chat.id == channel.id):

        logger.info(f"The message {message.forward_origin.message_id} was forwarded from the channel.")

        for user_id, user_messages in list(channel_messages.items()):
            for channel_message_id, operator_context in list(user_messages.items()):

                if message.forward_origin.message_id == channel_message_id:
                    await finish_confirmation_handling(context, message.message_id, operator_context)
                    
                    # Remove the processed message data
                    channel_messages[user_id].pop(channel_message_id, None)
                    if not channel_messages[user_id]:
                        channel_messages.pop(user_id, None)
                    
                    # Cancel the job for clearing this message data
                    if operator_context.job_name:
                        current_jobs = context.job_queue.get_jobs_by_name(operator_context.job_name)
                        for job in current_jobs:
                            job.schedule_removal()
                    
                    return

async def finish_confirmation_handling(context: ContextTypes.DEFAULT_TYPE, reply_to_message_id: int, operator_context: OperatorMessageContext):
    try:
        # Send transcription with URL
        with open(operator_context.transcript_path, 'r', encoding='utf-8') as f:
            transcript_text = f.read()
        escaped_transcript = escape_markdown(transcript_text, version=2)
        escaped_url = escape_markdown(operator_context.url, version=2)
        await context.bot.send_message(
            chat_id=DISCUSSION_GROUP_ID,
            text=f"{escaped_url}\n\n*Español:*\n||{escaped_transcript}||",
            reply_to_message_id=reply_to_message_id,
            parse_mode=ParseMode.MARKDOWN_V2,
            disable_web_page_preview=True
        )

        logger.info(f"the transcription was sent to the discussion group.")

        # Add a small delay
        await asyncio.sleep(1)

        # Send translation
        with open(operator_context.translation_path, 'r', encoding='utf-8') as f:
            translation_text = f.read()
        escaped_translation = escape_markdown(translation_text, version=2)
        await context.bot.send_message(
            chat_id=DISCUSSION_GROUP_ID,
            text=f"*Ruso:*\n||{escaped_translation}||",
            reply_to_message_id=reply_to_message_id,
            parse_mode=ParseMode.MARKDOWN_V2
        )

        logger.info(f"the translation was sent to the discussion group.")

        # Update the message in the operator's chat
        if operator_context.operator_chat_id and operator_context.operator_message_id:
            await context.bot.edit_message_text(
                chat_id=operator_context.operator_chat_id,
                message_id=operator_context.operator_message_id,
                text="Transcription and translation added successfully to the discussion group."
            )

    except TelegramError as e:
        logger.error(f"Failed to send comments to discussion group: {e}")
        if operator_context.operator_chat_id and operator_context.operator_message_id:
            await context.bot.edit_message_text(
                chat_id=operator_context.operator_chat_id,
                message_id=operator_context.operator_message_id,
                text="Failed to send comments to discussion group."
            )

def main():
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.ChatType.GROUPS & filters.FORWARDED, handle_forwarded_message))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_url))
    application.add_handler(CallbackQueryHandler(handle_confirmation))

    logger.info(f"Start the bot.")

    application.run_polling()

if __name__ == "__main__":
    main()