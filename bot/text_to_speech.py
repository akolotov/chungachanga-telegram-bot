import os
from pathlib import Path
from elevenlabs import VoiceSettings
from elevenlabs.client import ElevenLabs
from dotenv import load_dotenv
from typing import Optional

class ElevenLabsError(Exception):
    """Custom exception for ElevenLabs API errors."""
    pass

class TextToSpeech:
    """A class to handle text-to-speech conversion using ElevenLabs API."""

    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv("ELEVENLABS_API_KEY")
        if not self.api_key:
            raise ElevenLabsError("ElevenLabs API key not found. Please set the ELEVENLABS_API_KEY environment variable.")
        
        self.client = ElevenLabs(api_key=self.api_key)
        self.voice_ids = {
            "female": "FGY2WhTYpPnrIDTdsKH5",  # Laura voice id
            "male": "bIHbv24MWmeRgasZH58o"     # Will voice id
        }

    def text_to_speech_file(self, text: str, voice: str, output_path: str) -> Optional[str]:
        """
        Converts text to speech and saves it as an MP3 file at the specified path.

        Args:
            text (str): The text to convert to speech.
            voice (str): The voice to use ('male' or 'female').
            output_path (str): The path where the audio file should be saved.

        Returns:
            Optional[str]: The path of the saved audio file, or None if conversion failed.

        Raises:
            ElevenLabsError: If there's an error during the text-to-speech conversion.
        """
        try:
            chosen_voice_id = self.voice_ids.get(voice.lower())
            if not chosen_voice_id:
                raise ElevenLabsError(f"Invalid voice option: {voice}. Choose 'male' or 'female'.")

            response = self.client.text_to_speech.convert(
                voice_id=chosen_voice_id,
                output_format="mp3_22050_32",
                text=text,
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

            with open(output_path, "wb") as f:
                for chunk in response:
                    if chunk:
                        f.write(chunk)

            return output_path

        except Exception as e:
            raise ElevenLabsError(f"Error during text-to-speech conversion: {str(e)}")

def convert_text_to_speech(text: str, voice: str, output_path: str) -> Optional[str]:
    """
    Converts text to speech using the TextToSpeech class and saves it to the specified path.

    Args:
        text (str): The text to convert to speech.
        voice (str): The voice to use ('male' or 'female').
        output_path (str): The path where the audio file should be saved.

    Returns:
        Optional[str]: The path of the saved audio file, or None if conversion failed.
    """
    tts = TextToSpeech()
    try:
        return tts.text_to_speech_file(text, voice, output_path)
    except ElevenLabsError as e:
        print(f"An error occurred during text-to-speech conversion: {e}")
        return None

if __name__ == "__main__":
    # Example usage
    sample_text = "El Conassif amplió el plazo de intervención a Desyfin. Esta financiera tiene ahora hasta el 13 de octubre. La ley permite extender hasta 30 días más por casos complejos."
    output_file = "data/voice_note.mp3"
    audio_file_path = convert_text_to_speech(sample_text, "female", output_file)
    if audio_file_path:
        print(f"Audio file saved at: {audio_file_path}")
    else:
        print("Failed to convert text to speech.")