import logging
import re
import unicodedata
from typing import Dict, List, Optional, Tuple

import jellyfish

from .cache_db import CacheDB
from .models import NewsStory, TranscriptionWord

logger = logging.getLogger(__name__)

def _clean_text(text: str) -> str:
    """Remove punctuation and convert to lowercase."""
    return re.sub(r'[.,!?¿¡:;]', '', text.lower())

def _normalize_string(s: str) -> str:
    """Normalize a string by removing accents and converting to lowercase."""
    return ''.join(
        c for c in unicodedata.normalize('NFD', s.lower())
        if unicodedata.category(c) != 'Mn'
    )

def _similarity_jellyfish(s1: str, s2: str) -> float:
    """Compare two strings for similarity using Jaro-Winkler distance.
    
    Returns:
        float: A value between 0 and 1, where 1 means the strings are identical
        and 0 means they are completely different.
    """
    s1_norm = _normalize_string(s1)
    s2_norm = _normalize_string(s2)
    return jellyfish.jaro_winkler_similarity(s1_norm, s2_norm)

def _find_best_matching_sequence(target_text: str, timeline: List[TranscriptionWord], sequence_length: int, 
                               join_with_space: bool = False, debug: bool = False) -> Tuple[int, float]:
    """Find the best matching sequence in timeline for given text.
    
    Args:
        target_text (str): The text sequence to search for in the timeline
        timeline (List[TranscriptionWord]): List of transcribed words with timestamps
        sequence_length (int): Length of sequence to compare at a time
        join_with_space (bool, optional): Whether to join words from timeline with space. Defaults to False.
        debug (bool, optional): Whether to log debug information. Defaults to False.
        
    Returns:
        Tuple[int, float]: A tuple containing:
            - Index of the best matching sequence start position (-1 if no match)
            - Similarity score between 0 and 1, where 1 is exact match
    """
    best_match = (-1, 0.0)  # (start_index, similarity)
    
    # If timeline is shorter than sequence_length, adjust sequence_length
    if len(timeline) < sequence_length:
        sequence_length = len(timeline)
    
    # Try each possible sequence in timeline
    for i in range(len(timeline) - sequence_length + 1):
        # Compose sequence text
        sequence_words = [item.word for item in timeline[i:i + sequence_length]]
        sequence_text = ' '.join(sequence_words) if join_with_space else ''.join(sequence_words)
        cleaned_sequence_text = _clean_text(sequence_text)
        
        # Compare with target using Jaro-Winkler similarity
        similarity = _similarity_jellyfish(target_text, cleaned_sequence_text)
                
        # Update best match if similarity is higher
        if similarity > best_match[1]:
            best_match = (i, similarity)
            if debug:
                logger.info(f"Target: '{target_text}'; Sequence: '{cleaned_sequence_text}'; Similarity: {similarity:.2f}")

    return best_match

def _find_best_match_with_both_methods(chunk_words: List[str], timeline: List[TranscriptionWord], 
                                     chunk_size: int, debug: bool = False) -> Tuple[int, float]:
    """Try matching chunk both with and without spaces and return the best result.
    
    Args:
        chunk_words (List[str]): List of words to match
        timeline (List[TranscriptionWord]): Timeline to search in
        chunk_size (int): Size of the chunk to match
        debug (bool, optional): Whether to log debug info. Defaults to False.
        
    Returns:
        Tuple[int, float]: Best matching index and similarity score
    """
    # Try with spaces
    chunk_with_spaces = ' '.join(chunk_words)
    idx_spaces, sim_spaces = _find_best_matching_sequence(
        chunk_with_spaces, timeline, chunk_size, join_with_space=True, debug=debug
    )
    
    # Try without spaces
    chunk_no_spaces = ''.join(chunk_words)
    idx_no_spaces, sim_no_spaces = _find_best_matching_sequence(
        chunk_no_spaces, timeline, chunk_size, join_with_space=False, debug=debug
    )
    
    # Use the better match
    idx = idx_spaces if sim_spaces >= sim_no_spaces else idx_no_spaces
    similarity = max(sim_spaces, sim_no_spaces)
            
    return idx, similarity

def _find_segment_timestamps(timeline: List[TranscriptionWord], segments: List[Dict], 
                           chunk_ratio: float = 0.5, 
                           similarity_threshold: float = 0.9) -> List[NewsStory]:
    """Find start and end timestamps for segments using text similarity.
    
    Args:
        timeline (List[TranscriptionWord]): List of transcribed words with their start/end timestamps
        segments (List[Dict]): List of text segments to find timestamps for. Each dict must have 'id' and 'text' keys
        chunk_ratio (float, optional): Ratio of segment words to use for matching. Defaults to 0.5
        similarity_threshold (float, optional): Minimum similarity score to consider a match valid. Defaults to 0.9
        
    Returns:
        List[NewsStory]: List of NewsStory objects containing:
            - id: Original segment ID
            - text: Original segment text
            - start: Start timestamp in seconds, or None if no match found
            - end: End timestamp in seconds, or None if no match found 
            - start_similarity: Similarity score for start chunk match
            - end_similarity: Similarity score for end chunk match
    """
    results = []
    
    for segment in segments:
        logger.info(f"Identifying bounds for segment '{segment['text'][:20]}...{segment['text'][-20:]}' in the transcription")

        # Clean segment text and split into words
        cleaned_text = _clean_text(segment['text'])
        segment_words = [w for w in cleaned_text.split() if w]
        chunk_size = max(3, int(len(segment_words) * chunk_ratio))
        
        # Find start position
        start_idx, start_similarity = _find_best_match_with_both_methods(
            segment_words[:chunk_size], timeline, chunk_size
        )
        
        # Find end position
        end_idx, end_similarity = _find_best_match_with_both_methods(
            segment_words[-chunk_size:], timeline[start_idx:], chunk_size
        )

        # Adjust end_idx to account for sliced timeline
        end_idx = end_idx + start_idx if end_idx != -1 else -1        
        
        # Only include results that meet similarity threshold
        if (start_similarity >= similarity_threshold and 
            end_similarity >= similarity_threshold and 
            start_idx != -1 and end_idx != -1):
            
            story = NewsStory(
                id=segment['id'],
                text=segment['text'],
                start=timeline[start_idx].start if start_idx == 0 else (
                    timeline[start_idx].start - (timeline[start_idx].start - timeline[start_idx - 1].end) / 3
                ),
                end=timeline[end_idx + chunk_size - 1].end,
                start_similarity=start_similarity,
                end_similarity=end_similarity
            )
        else:
            logger.warning(f"Could not find reliable bounds")
            story = NewsStory(
                id=segment['id'],
                text=segment['text'],
                start=None,
                end=None,
                start_similarity=start_similarity,
                end_similarity=end_similarity
            )
        
        results.append(story)
    
    return results

def find_story_timestamps(video_id: str, cache_db: CacheDB, similarity_threshold: float = 0.9) -> Optional[List[NewsStory]]:
    """
    Find timestamps for news stories in a video using text similarity.
    
    Args:
        video_id (str): YouTube video ID
        cache_db (CacheDB): Cache database instance
        similarity_threshold (float): Minimum similarity threshold for timestamp matching
        
    Returns:
        Optional[List[NewsStory]]: List of stories with their timestamps if successful, None otherwise
    """
    # Check if required data exists in cache
    transcription = cache_db.get_transcription(video_id)
    if not transcription:
        logger.error(f"No transcription found for video {video_id}")
        return None

    final_news = cache_db.get_final_local_news(video_id)
    if not final_news:
        logger.error(f"No final local news found for video {video_id}")
        return None
    
    logger.info(f"Identifying time marks for {len(final_news)} news stories")

    # Prepare segments with IDs
    segments = [
        {
            "id": f"{i+1:03d}",
            "text": story
        } for i, story in enumerate(final_news)
    ]

    # Find timestamps for segments
    return _find_segment_timestamps(
        transcription.words, 
        segments,
        similarity_threshold=similarity_threshold
    )

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )

    import os
    from bot.settings import settings
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

    # Initialize cache DB
    cache_db = CacheDB(settings.yt_crhoy_cache_db)

    stories = find_story_timestamps(video_id, cache_db)
    if stories:
        print("\nFound timestamps for stories:")
        for story in stories:
            print(f"\nStory '{story.text[:16]}...':")
            if story.start is not None and story.end is not None:
                print(f"Start: {story.start:.2f}s (similarity: {story.start_similarity:.2f})")
                print(f"End: {story.end:.2f}s (similarity: {story.end_similarity:.2f})")
            else:
                print("No reliable timestamps found")
                print(f"Start similarity: {story.start_similarity:.2f}")
                print(f"End similarity: {story.end_similarity:.2f}")
    else:
        print("No timestamp data available.")
