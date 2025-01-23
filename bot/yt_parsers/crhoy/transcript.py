import logging
import os
from typing import Union

import openai

from bot.settings import settings

from .cache_db import CacheDB
from .models import TranscriptionData, TranscriptionWord

logger = logging.getLogger(__name__)

WHISPER_PROMPT = "El siguiente es un transcripción de un bloque corto de noticias producido por CRHoy.com, una agencia de noticias de Costa Rica. El audio incluye noticias locales de Costa Rica y noticias internacionales. Transcriba todas las palabras habladas sin omitir ninguna parte del audio, incluso si hay sonidos no verbales utilizados como relleno entre las noticias."


def transcribe_audio(video_id: str, cache_db: CacheDB, force: bool = False) -> Union[TranscriptionData, None]:
    """
    Transcribe audio from a video, using cache when available.
    
    Args:
        video_id (str): YouTube video ID
        cache_db (CacheDB): Cache database instance
        force (bool): If True, force new transcription even if cached version exists
     
    Returns:
        TranscriptionData: Object containing transcription text and word-level data
    """
    # Check if transcription exists in cache
    if not force and cache_db.video_exists(video_id):
        transcription = cache_db.get_transcription(video_id)
        if transcription:
            logger.info(f"Found cached transcription for video {video_id}")
            return transcription

    # Get audio path from cache
    audio_file = cache_db.get_audio_path(video_id)
    if not audio_file or not os.path.exists(audio_file):
        logger.error(f"Audio file not found for video ID: {video_id}")
        return None

    api_key = settings.speech_to_text_api_key
    if not api_key:
        logger.error(
            "OpenAI API key not found. Please set the SPEECH_TO_TEXT_API_KEY environment variable.")
        return None

    logger.info(f"Transcribing audio file: {audio_file} through OpenAI Whisper API.")

    client = openai.OpenAI(api_key=api_key)

    try:
        with open(audio_file, "rb") as audio:
            transcription = client.audio.transcriptions.create(
                file=audio,
                model="whisper-1",
                language="es",
                response_format="verbose_json",
                timestamp_granularities=["word"],
                prompt=WHISPER_PROMPT
            )

    except openai.OpenAIError as oe:
        logger.error(f"OpenAI API error: {str(oe)}")
        return None
    except Exception as e:
        logger.error(f"Error transcribing audio file: {e}")
        return None

    # Convert OpenAI response to our data model
    words_data = [
        TranscriptionWord(
            word=word.word,
            start=word.start,
            end=word.end
        ) for word in transcription.words
    ]
    
    transcription_data = TranscriptionData(
        text=transcription.text,
        words=words_data
    )

    # Update cache with new transcription
    cache_db.set_transcription(video_id, transcription_data)
    
    return transcription_data


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)

    from .helper import extract_video_id

    yt_link = os.getenv("YT_LINK", "")
    if not yt_link:
        print("YT_LINK environment variable is not set. Please set it in your environment or in a .env file.")
        exit(1)

    # Extract video ID
    video_id = extract_video_id(yt_link)
    if not video_id:
        print(f"Invalid YouTube URL: {yt_link}")
        exit(1)

    # Initialize cache DB once
    cache_db = CacheDB(settings.yt_crhoy_cache_db)

    transcription = transcribe_audio(video_id, cache_db)
    if transcription:
        print(f"Transcribed text: {transcription.text}")
    else:
        print("No transcription data available.")
