from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from bot.db.base import BaseDB

from .models import TranscribedSequences, TranscriptionData

class AnalysisData(BaseModel):
    all_sequences: Optional[TranscribedSequences] = None
    raw_local_news: Optional[List[str]] = None
    final_local_news: Optional[List[str]] = None

class VideoData(BaseModel):
    audio: Optional[str] = None  # Path to audio file
    transcription: Optional[TranscriptionData] = None
    analysis: Optional[AnalysisData] = None

class CacheDB(BaseDB[Dict[str, Any]]):
    def __init__(self, db_file: str = "youtube_crhoy_cache.json") -> None:
        super().__init__(db_file)

    def add_video_data(self, video_id: str, data: VideoData) -> None:
        """
        Add or update cached data for a YouTube video.

        :param video_id: YouTube video identifier
        :param data: VideoData object containing the video-related information
        """
        def prepare(content: Dict[str, Any]) -> Dict[str, Any]:
            return data.model_dump(mode='json')

        super().add_content(video_id, data.model_dump(), prepare)

    def get_video_data(self, video_id: str) -> Optional[VideoData]:
        """
        Retrieve cached data for a YouTube video.

        :param video_id: YouTube video identifier
        :return: VideoData object if found, None otherwise
        """
        def parse(stored_content: Dict[str, Any]) -> VideoData:
            return VideoData(**stored_content)

        return super().get_content(video_id, parse)

    def video_exists(self, video_id: str) -> bool:
        """
        Check if a video exists in the cache.

        :param video_id: YouTube video identifier
        :return: True if the video exists in cache, False otherwise
        """
        return self.exists(video_id)

    def get_audio_path(self, video_id: str) -> Optional[str]:
        """
        Get the audio file path for a video.

        :param video_id: YouTube video identifier
        :return: Path to the audio file if exists, None otherwise
        """
        video_data = self.get_video_data(video_id)
        return video_data.audio if video_data else None

    def get_transcription(self, video_id: str) -> Optional[TranscriptionData]:
        """
        Get the transcription data for a video.

        :param video_id: YouTube video identifier
        :return: TranscriptionData if exists, None otherwise
        """
        video_data = self.get_video_data(video_id)
        return video_data.transcription if video_data else None

    def get_analysis(self, video_id: str) -> Optional[AnalysisData]:
        """
        Get the analysis data for a video.

        :param video_id: YouTube video identifier
        :return: AnalysisData if exists, None otherwise
        """
        video_data = self.get_video_data(video_id)
        return video_data.analysis if video_data else None

    def get_sequences(self, video_id: str) -> Optional[TranscribedSequences]:
        """
        Get the sequence data from analysis for a video.

        :param video_id: YouTube video identifier
        :return: TranscribedSequences if exists, None otherwise
        """
        analysis = self.get_analysis(video_id)
        return analysis.all_sequences if analysis else None

    def get_raw_local_news(self, video_id: str) -> Optional[List[str]]:
        """
        Get the raw local news from analysis for a video.

        :param video_id: YouTube video identifier
        :return: List of raw local news if exists, None otherwise
        """
        analysis = self.get_analysis(video_id)
        return analysis.raw_local_news if analysis else None

    def get_final_local_news(self, video_id: str) -> Optional[List[str]]:
        """
        Get the final local news from analysis for a video.

        :param video_id: YouTube video identifier
        :return: List of final local news if exists, None otherwise
        """
        analysis = self.get_analysis(video_id)
        return analysis.final_local_news if analysis else None

    def set_audio_path(self, video_id: str, audio_path: str) -> None:
        """
        Set or update the audio path for a video.

        :param video_id: YouTube video identifier
        :param audio_path: Path to the audio file
        """
        existing_data = self.get_video_data(video_id)
        video_data = VideoData(
            audio=audio_path,
            transcription=existing_data.transcription if existing_data else None,
            analysis=existing_data.analysis if existing_data else None
        )
        self.add_video_data(video_id, video_data)

    def set_transcription(self, video_id: str, transcription: TranscriptionData) -> None:
        """
        Set or update the transcription data for a video.

        :param video_id: YouTube video identifier
        :param transcription: TranscriptionData object
        """
        existing_data = self.get_video_data(video_id)
        video_data = VideoData(
            audio=existing_data.audio if existing_data else None,
            transcription=transcription,
            analysis=existing_data.analysis if existing_data else None
        )
        self.add_video_data(video_id, video_data)

    def set_analysis(self, video_id: str, analysis: AnalysisData) -> None:
        """
        Set or update the analysis data for a video.

        :param video_id: YouTube video identifier
        :param analysis: AnalysisData object
        """
        existing_data = self.get_video_data(video_id)
        video_data = VideoData(
            audio=existing_data.audio if existing_data else None,
            transcription=existing_data.transcription if existing_data else None,
            analysis=analysis
        )
        self.add_video_data(video_id, video_data)

    def set_sequences(self, video_id: str, sequences: TranscribedSequences) -> None:
        """
        Set or update the sequence data in analysis for a video.

        :param video_id: YouTube video identifier
        :param sequences: TranscribedSequences object
        """
        existing_data = self.get_video_data(video_id)
        existing_analysis = existing_data.analysis if existing_data else None
        
        analysis = AnalysisData(
            all_sequences=sequences,
            raw_local_news=existing_analysis.raw_local_news if existing_analysis else [],
            final_local_news=existing_analysis.final_local_news if existing_analysis else []
        )
        
        video_data = VideoData(
            audio=existing_data.audio if existing_data else None,
            transcription=existing_data.transcription if existing_data else None,
            analysis=analysis
        )
        self.add_video_data(video_id, video_data)

    def set_raw_local_news(self, video_id: str, raw_news: List[str]) -> None:
        """
        Set or update the raw local news in analysis for a video.

        :param video_id: YouTube video identifier
        :param raw_news: List of raw local news
        """
        existing_data = self.get_video_data(video_id)
        existing_analysis = existing_data.analysis if existing_data else None
        
        analysis = AnalysisData(
            all_sequences=existing_analysis.all_sequences if existing_analysis else TranscribedSequences(intro="", stories=[], outro=""),
            raw_local_news=raw_news,
            final_local_news=existing_analysis.final_local_news if existing_analysis else []
        )
        
        video_data = VideoData(
            audio=existing_data.audio if existing_data else None,
            transcription=existing_data.transcription if existing_data else None,
            analysis=analysis
        )
        self.add_video_data(video_id, video_data)

    def set_final_local_news(self, video_id: str, final_news: List[str]) -> None:
        """
        Set or update the final local news in analysis for a video.

        :param video_id: YouTube video identifier
        :param final_news: List of final local news
        """
        existing_data = self.get_video_data(video_id)
        existing_analysis = existing_data.analysis if existing_data else None
        
        analysis = AnalysisData(
            all_sequences=existing_analysis.all_sequences if existing_analysis else TranscribedSequences(intro="", stories=[], outro=""),
            raw_local_news=existing_analysis.raw_local_news if existing_analysis else [],
            final_local_news=final_news
        )
        
        video_data = VideoData(
            audio=existing_data.audio if existing_data else None,
            transcription=existing_data.transcription if existing_data else None,
            analysis=analysis
        )
        self.add_video_data(video_id, video_data) 