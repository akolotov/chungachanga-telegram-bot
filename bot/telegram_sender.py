import os
import asyncio
from dataclasses import dataclass
from typing import List, Optional
from telegram import Bot, InputFile
from telegram.constants import ParseMode
from telegram.error import TelegramError
from telegram.helpers import escape_markdown
from dotenv import load_dotenv
from helper import format_vocabulary, trim_message
from settings import settings

@dataclass
class MessageContent:
    """
    A class to hold the content to be sent to Telegram.
    
    Attributes:
        url (str): The URL of the original article.
        voice_note_path (str): Path to the voice note file.
        transcript_path (str): Path to the transcript file.
        translation_path (str): Path to the translation file.
        vocabulary (Optional[List[VocabularyItem]]): List of vocabulary items.
    """
    url: str
    voice_note_path: str
    transcript_path: str
    translation_path: str
    vocabulary: Optional[List] = None

class TelegramSenderError(Exception):
    """Custom exception for Telegram sending errors."""
    pass

class TelegramSender:
    """A class to handle sending messages to Telegram channels."""

    def __init__(self, bot: Bot, channel_id: str):
        """
        Initialize the TelegramSender with a bot object and channel ID.

        Args:
            bot (telegram.Bot): An initialized Telegram Bot object.
            channel_id (str): The ID of the Telegram channel.
        """
        self.bot = bot
        self.channel_id = channel_id

    async def send_messages(self, content: MessageContent) -> bool:
        """
        Send a batch of messages to the Telegram channel.

        Args:
            content (MessageContent): An object containing paths to the content to be sent.

        Returns:
            bool: True if all messages were sent successfully, False otherwise.

        Raises:
            TelegramSenderError: If there's an error sending any of the messages or accessing the files.
        """
        try:
            # Check if all files are accessible
            if content.voice_note_path:
                with open(content.voice_note_path, 'rb'):
                    pass
            with open(content.transcript_path, 'r', encoding='utf-8'):
                pass
            with open(content.translation_path, 'r', encoding='utf-8'):
                pass

            # If all files are accessible, proceed with sending

            # Send transcript with URL
            with open(content.transcript_path, 'r', encoding='utf-8') as transcript:
                transcript_text = transcript.read()
                escaped_transcript = escape_markdown(transcript_text, version=2)
                escaped_url = escape_markdown(content.url, version=2)
                await self.bot.send_message(
                    chat_id=self.channel_id,
                    text=f"{escaped_url}\n\n" \
                         f"*Español:*\n||{escaped_transcript}||",
                    parse_mode=ParseMode.MARKDOWN_V2,
                    disable_web_page_preview=True
                )

            # Send translation
            with open(content.translation_path, 'r', encoding='utf-8') as translation:
                translation_text = translation.read()
                escaped_translation = escape_markdown(translation_text, version=2)
                await self.bot.send_message(
                    chat_id=self.channel_id,
                    text=f"*Ruso:*\n||{escaped_translation}||",
                    parse_mode=ParseMode.MARKDOWN_V2
                )

            # Send vocabulary if available
            if content.vocabulary:
                formatted_vocabulary = format_vocabulary(content.vocabulary)
                vocabulary_message = f"Palabras para entender el audio:\n{formatted_vocabulary}"
                
                await self.bot.send_message(
                    chat_id=self.channel_id,
                    text=trim_message(vocabulary_message),
                    parse_mode=ParseMode.MARKDOWN_V2
                )

            # Send voice note if path is provided and file exists
            if content.voice_note_path and os.path.exists(content.voice_note_path):
                with open(content.voice_note_path, 'rb') as voice_note:
                    await self.bot.send_voice(chat_id=self.channel_id, voice=InputFile(voice_note))

            return True

        except IOError as e:
            raise TelegramSenderError(f"Error accessing file: {str(e)}")
        except TelegramError as e:
            raise TelegramSenderError(f"Error sending messages to Telegram: {str(e)}")

async def send_telegram_messages(bot: Bot, channel_id: str, content: MessageContent) -> bool:
    """
    Send a batch of messages to a Telegram channel using the TelegramSender class.

    Args:
        bot (telegram.Bot): An initialized Telegram Bot object.
        channel_id (str): The ID of the Telegram channel.
        content (MessageContent): An object containing paths to the content to be sent.

    Returns:
        bool: True if all messages were sent successfully, False otherwise.
    """
    sender = TelegramSender(bot, channel_id)
    try:
        return await sender.send_messages(content)
    except TelegramSenderError as e:
        print(f"An error occurred while sending messages to Telegram: {e}")
        return False

if __name__ == "__main__":
    # Load environment variables from .env file
    load_dotenv()

    # Example usage
    from telegram import Bot
        
    if not settings.telegram_bot_token or not settings.telegram_channel_id:
        raise ValueError("TELEGRAM_BOT_TOKEN and TELEGRAM_CHANNEL_ID must be set in the .env file")
    
    # Initialize the bot object
    bot = Bot(token=settings.telegram_bot_token)
    
    content = MessageContent(
        url="https://example.com/article",
        voice_note_path="data/voice_note.mp3",
        transcript_path="data/transcript.txt",
        translation_path="data/translation.txt"
    )
    
    async def main():
        success = await send_telegram_messages(bot, settings.telegram_channel_id, content)
        if success:
            print("All messages sent successfully to Telegram channel.")
        else:
            print("Failed to send messages to Telegram channel.")

    # Run the async main function
    asyncio.run(main())