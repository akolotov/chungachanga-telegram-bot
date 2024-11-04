import os
import logging
from elevenlabs import VoiceSettings
from elevenlabs.client import ElevenLabs
from dotenv import load_dotenv
from typing import Optional, Tuple, Dict, List
import requests

# Configure logging
logger = logging.getLogger(__name__)

SAFETY_FACTOR = 1.5  # Coefficient to multiply text length for safety

load_dotenv()
api_keys_str = os.getenv("ELEVENLABS_API_KEY", "")

class ElevenLabsError(Exception):
    """Custom exception for ElevenLabs API errors."""
    pass

class InsufficientCreditsError(ElevenLabsError):
    """Exception raised when there are insufficient credits across all API keys."""
    pass

class TextToSpeech:
    """A class to handle text-to-speech conversion using ElevenLabs API with multiple API keys."""

    def __init__(self):
        self.api_keys = self._load_api_keys()
        if not self.api_keys:
            raise ElevenLabsError("No ElevenLabs API keys found. Please set the ELEVENLABS_API_KEY environment variable.")
        
        logger.info(f"Initialized with {len(self.api_keys)} API keys")
        # Daniel, onwK4e9ZLuTAKqWW03F9
        # Sarah, EXAVITQu4vr4xnSDxMaL
        # Laura, FGY2WhTYpPnrIDTdsKH5
        # Will, bIHbv24MWmeRgasZH58o
        self.voice_ids = {
            "female": "EXAVITQu4vr4xnSDxMaL",  # Sarah voice id
            "male": "bIHbv24MWmeRgasZH58o"     # Will voice id
        }
        self.token_safety_factor = SAFETY_FACTOR

    def _load_api_keys(self) -> List[str]:
        """Load API keys from environment variable."""
        return [key.strip() for key in api_keys_str.split(",") if key.strip()]

    def get_credit_usage(self, api_key: str) -> Tuple[int, int]:
        """
        Requests the current amount of used credits for a specific API key.

        Args:
            api_key (str): The API key to check.

        Returns:
            Tuple[int, int]: A tuple containing (remaining_characters, next_reset_timestamp)

        Raises:
            ElevenLabsError: If there's an error during the API request.
        """
        url = "https://api.elevenlabs.io/v1/user/subscription"
        headers = {"xi-api-key": api_key}

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            logger.info(f"Credit usage data: {data}")

            character_count = data.get('character_count', 0)
            character_limit = data.get('character_limit', 0)
            next_reset = data.get('next_character_count_reset_unix', 0)

            remaining_characters = character_limit - character_count

            return remaining_characters, next_reset

        except requests.RequestException as e:
            logger.error(f"Error fetching credit usage: {str(e)}")
            raise ElevenLabsError(f"Error fetching credit usage: {str(e)}")

    def select_api_key(self, text_length: int) -> Tuple[str, ElevenLabs, int]:
        """
        Selects an appropriate API key based on the required text length.

        Args:
            text_length (int): The length of the text to be converted.

        Returns:
            Tuple[str, ElevenLabs, int]: A tuple containing the selected API key, its corresponding client, and the remaining characters.

        Raises:
            InsufficientCreditsError: If no API key has sufficient credits.
        """
        required_tokens = int(text_length * self.token_safety_factor)

        for api_key in self.api_keys:
            remaining_characters, _ = self.get_credit_usage(api_key)
            if remaining_characters >= required_tokens:
                logger.info(f"Selected API key {api_key[:8]}... with {remaining_characters} characters remaining")
                client = ElevenLabs(api_key=api_key)
                return api_key, client, remaining_characters

        logger.error("No API key with sufficient credits found")
        raise InsufficientCreditsError("Insufficient credits across all API keys.")

    def text_to_speech_file(self, text: str, voice: str, output_path: str) -> Optional[Dict[str, any]]:
        """
        Converts text to speech and saves it as an MP3 file at the specified path.

        Args:
            text (str): The text to convert to speech.
            voice (str): The voice to use ('male' or 'female').
            output_path (str): The path where the audio file should be saved.

        Returns:
            Optional[Dict[str, any]]: A dictionary containing the path of the saved audio file,
                                      remaining characters, next reset timestamp, and used tokens,
                                      or None if conversion failed.

        Raises:
            ElevenLabsError: If there's an error during the text-to-speech conversion.
            InsufficientCreditsError: If there are insufficient credits across all API keys.
        """
        try:
            chosen_voice_id = self.voice_ids.get(voice.lower())
            if not chosen_voice_id:
                logger.error(f"Invalid voice option: {voice}")
                raise ElevenLabsError(f"Invalid voice option: {voice}. Choose 'male' or 'female'.")

            api_key, client, remaining_characters_before = self.select_api_key(len(text))

            logger.info("Making API request to ElevenLabs")
            response = client.text_to_speech.convert(
                voice_id=chosen_voice_id,
                output_format="mp3_22050_32",
                text=text,
                previous_text="Escucha la noticia del día.",
                next_text="Eso es todo por ahora.",
                model_id="eleven_multilingual_v2",
                voice_settings=VoiceSettings(
                    stability=0.32,
                    similarity_boost=0.75,
                    style=0.0,
                    use_speaker_boost=True,
                ),
            )

            # Ensure the directory exists
            output_dir = os.path.dirname(output_path)
            os.makedirs(output_dir, exist_ok=True)

            logger.info(f"Saving audio file to {output_path}")
            with open(output_path, "wb") as f:
                for chunk in response:
                    if chunk:
                        f.write(chunk)

            # Get credit usage after conversion
            remaining_characters, next_reset = self.get_credit_usage(api_key)

            # Calculate used tokens
            used_tokens = remaining_characters_before - remaining_characters
            
            logger.info(f"Text-to-speech conversion complete. Used {used_tokens} tokens")
            return {
                "audio_path": output_path,
                "remaining_characters": remaining_characters,
                "next_reset_timestamp": next_reset,
                "used_tokens": used_tokens
            }

        except InsufficientCreditsError as e:
            logger.error(f"Insufficient credits error: {str(e)}")
            raise e
        except Exception as e:
            logger.error(f"Error during text-to-speech conversion: {str(e)}")
            raise ElevenLabsError(f"Error during text-to-speech conversion: {str(e)}")

def convert_text_to_speech(text: str, voice: str, output_path: str) -> Optional[Dict[str, any]]:
    """
    Converts text to speech using the TextToSpeech class and saves it to the specified path.

    Args:
        text (str): The text to convert to speech.
        voice (str): The voice to use ('male' or 'female').
        output_path (str): The path where the audio file should be saved.

    Returns:
        Optional[Dict[str, any]]: A dictionary containing the path of the saved audio file,
                                  remaining characters, next reset timestamp, and used tokens,
                                  or None if conversion failed.
    """
    logger.info(f"Starting text-to-speech conversion for voice: {voice}")
    tts = TextToSpeech()
    try:
        return tts.text_to_speech_file(text, voice, output_path)
    except (ElevenLabsError, InsufficientCreditsError) as e:
        return None

if __name__ == "__main__":
    # Example usage
    sample_text = "El Conassif amplió el plazo de intervención a Desyfin. Esta financiera tiene ahora hasta el 13 de octubre. La ley permite extender hasta 30 días más por casos complejos."
    output_file = "data/voice_note.mp3"
    result = convert_text_to_speech(sample_text, "female", output_file)
    if result:
        print(f"Audio file saved at: {result['audio_path']}")
        print(f"Remaining characters: {result['remaining_characters']}")
        print(f"Next reset timestamp: {result['next_reset_timestamp']}")
        print(f"Used tokens: {result['used_tokens']}")
    else:
        print("Failed to convert text to speech.")