import os
import json
import logging
from elevenlabs import VoiceSettings
from elevenlabs.client import ElevenLabs
from typing import Optional, Tuple, Dict, List
import requests
from settings import settings, ElevenLabsRotateMethod

# Configure logging
logger = logging.getLogger(__name__)

SAFETY_FACTOR = 1.5  # Coefficient to multiply text length for safety
DEFAULT_STATE_DIR = "data/state"
DEFAULT_STATE_FILE = "tts.json"

class ElevenLabsError(Exception):
    """Custom exception for ElevenLabs API errors."""
    pass

class InsufficientCreditsError(ElevenLabsError):
    """Exception raised when there are insufficient credits across all API keys."""
    pass

class APIKeys:
    """A class to handle API keys for ElevenLabs."""

    def __init__(self, state_dir: str, state_file: str):
        self._api_keys = self._load_api_keys()

        self._rotate_method = settings.elevenlabs_rotate_method
        
        self._state_path = os.path.join(state_dir, state_file)

        self._last_used_key = self._load_last_used_key()

    def _load_api_keys(self) -> Dict[str, str]:
        """
        Load API keys from environment variable and create a circular linked list structure.
        Returns a dict where each key points to the next key in rotation.
        """
        keys = settings.get_elevenlabs_api_keys()
        if not keys:
            raise ElevenLabsError("No ElevenLabs API keys found. Please set the ELEVENLABS_API_KEY environment variable.")
            
        # Create circular linked list as a dictionary
        api_keys = {}
        for i in range(len(keys)):
            api_keys[keys[i]] = keys[(i + 1) % len(keys)]
            
        logger.info(f"Created circular key chain with {len(api_keys)} keys")
        return api_keys

    def _load_last_used_key(self) -> Dict:
        """Load the state from file or create default if it doesn't exist."""
        os.makedirs(os.path.dirname(self._state_path), exist_ok=True)
        
        if os.path.exists(self._state_path):
            try:
                with open(self._state_path, 'r') as f:
                    state = json.load(f)
                    last_key = state.get("last_key")
                    logger.info(f"The previous key was {last_key[:8]}...")
                    # Validate that the last_key exists in our api_keys
                    if last_key not in self._api_keys:
                        logger.warning("Stored last_key not found in current API keys, choosing a new one")
                        last_key = self._rotate_key()
                    return last_key
            except json.JSONDecodeError:
                logger.warning("Failed to load state file, creating new state")
        
        # Default - start with the first key
        return self._rotate_key()

    def _save_state(self):
        """Save the state to file."""
        state = {"last_key": self._last_used_key}
        try:
            with open(self._state_path, 'w') as f:
                json.dump(state, f)
        except Exception as e:
            logger.error(f"Failed to save state: {e}")

    def _update_last_used_key(self, key: str):
        """Update the state with the new key and save it to file."""
        self._last_used_key = key
        self._save_state()

    def _rotate_key(self) -> str:
        """Get the next API key in the rotation."""
        current_key = None if not hasattr(self, '_last_used_key') else self._last_used_key
        if not current_key or current_key not in self._api_keys:
            # If current key is invalid, start with the first key
            next_key = next(iter(self._api_keys)) if self._api_keys else None
        else:
            next_key = self._api_keys[current_key]
        
        # Update state
        self._update_last_used_key(next_key)
        
        return next_key
    
    def get_initial_key(self) -> str:
        if self._rotate_method == ElevenLabsRotateMethod.BASIC:
            return self._last_used_key
        else:  # ElevenLabsRotateMethod.ROUND_ROBIN
            return self._rotate_key()
        
    def get_next_key(self) -> str:
        return self._rotate_key()

class TTSClient:
    """A class to handle text-to-speech conversion using ElevenLabs API with multiple API keys."""

    def __init__(self, state_dir: str, state_file: str):
        self._api_keys = APIKeys(state_dir, state_file)

    def _get_credit_usage(self, api_key: str) -> Tuple[int, int]:
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
            logger.info(f"Checking credit usage for API key {api_key[:8]}...")
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()

            character_count = data.get('character_count', 0)
            character_limit = data.get('character_limit', 0)
            next_reset = data.get('next_character_count_reset_unix', 0)

            remaining_characters = character_limit - character_count

            return remaining_characters, next_reset

        except requests.RequestException as e:
            logger.error(f"Error fetching credit usage: {str(e)}")
            raise ElevenLabsError(f"Error fetching credit usage: {str(e)}")        

class TextToSpeech:
    """A class to handle text-to-speech conversion using ElevenLabs API with multiple API keys."""

    def __init__(self, state_dir: str = DEFAULT_STATE_DIR, state_file: str = DEFAULT_STATE_FILE):
        self._api_keys = APIKeys(state_dir, state_file)
        
        # Daniel, onwK4e9ZLuTAKqWW03F9
        # Sarah, EXAVITQu4vr4xnSDxMaL
        # Laura, FGY2WhTYpPnrIDTdsKH5
        # Will, bIHbv24MWmeRgasZH58o
        self.voice_ids = {
            "female": "EXAVITQu4vr4xnSDxMaL",  # Sarah voice id
            "male": "bIHbv24MWmeRgasZH58o"     # Will voice id
        }
        self.token_safety_factor = SAFETY_FACTOR

    def _get_credit_usage(self, api_key: str) -> Tuple[int, int]:
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
            logger.info(f"Checking credit usage for API key {api_key[:8]}...")
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()

            character_count = data.get('character_count', 0)
            character_limit = data.get('character_limit', 0)
            next_reset = data.get('next_character_count_reset_unix', 0)

            remaining_characters = character_limit - character_count

            return remaining_characters, next_reset

        except requests.RequestException as e:
            logger.error(f"Error fetching credit usage: {str(e)}")
            raise ElevenLabsError(f"Error fetching credit usage: {str(e)}")

    def _get_available_client(self, text_length: int) -> Tuple[ElevenLabs, int]:
        """
        Selects an API client based on the rotation method:
        - `ElevenLabsRotateMethod.ROUND_ROBIN`: Rotates through all keys in sequence
        - `ElevenLabsRotateMethod.BASIC`: Uses the current key until it runs out of tokens

        Args:
            text_length (int): The length of the text to be converted.

        Returns:
            Tuple[ElevenLabs, int]: A tuple containing the selected client and remaining characters.

        Raises:
            InsufficientCreditsError: If no API key has sufficient credits.
        """
        required_tokens = int(text_length * self.token_safety_factor)
        keys_tried = set()

        if self.rotate_method == ElevenLabsRotateMethod.BASIC:
            current_key = self.state.get("last_key")
        else:  # ElevenLabsRotateMethod.ROUND_ROBIN
            current_key = self._get_next_key()

        while len(keys_tried) < len(self.api_keys):
            keys_tried.add(current_key)
            
            try:
                remaining_characters, _ = self._get_credit_usage(current_key)
                if remaining_characters >= required_tokens:
                    logger.info(f"Selected API key {current_key[:8]}... with {remaining_characters} characters remaining")                        
                    client = ElevenLabs(api_key=current_key)
                    return client, remaining_characters
                else:
                    logger.warning(f"API key {current_key[:8]}... has only {remaining_characters} characters remaining")
            except ElevenLabsError as e:
                logger.warning(f"Error checking API key {current_key[:8]}...: {e}")
            
            # Move to next key based on rotation method
            if self.rotate_method == ElevenLabsRotateMethod.BASIC:
                # Only move to next key if current one fails
                current_key = self.api_keys[current_key]
                self._update_key_state(current_key)
            else:  # ElevenLabsRotateMethod.ROUND_ROBIN
                current_key = self._get_next_key()

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

            client, remaining_characters_before = self._get_available_client(len(text))

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
                apply_text_normalization="on"
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
            remaining_characters, next_reset = self._get_credit_usage(client.api_key)

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