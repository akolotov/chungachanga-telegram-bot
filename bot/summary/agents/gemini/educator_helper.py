from typing import List
import unicodedata
from difflib import SequenceMatcher
import jellyfish
from cyrtranslit import to_latin
import logging

from ...models import EducatingVocabularyItem, VocabularyItem

logger = logging.getLogger(__name__)

def _normalize_string(s: str) -> str:
    """Normalize a string by removing accents and converting to lowercase.
    
    Args:
        s (str): The input string to normalize.
    
    Returns:
        str: The normalized string with accents removed and converted to lowercase.
    """
    return ''.join(
        c for c in unicodedata.normalize('NFD', s.lower())
        if unicodedata.category(c) != 'Mn'
    )

def _is_similar_basic(s1: str, s2: str, threshold: float = 0.65) -> bool:
    """Compare two strings for similarity using SequenceMatcher.
    
    Args:
        s1 (str): First string to compare.
        s2 (str): Second string to compare.
        threshold (float, optional): Minimum similarity ratio to consider strings similar. Defaults to 0.65.
    
    Returns:
        bool: True if strings are similar above the threshold, False otherwise.
    """
    s1_norm = _normalize_string(s1)
    s2_norm = _normalize_string(s2)
    similarity = SequenceMatcher(None, s1_norm, s2_norm).ratio()
    return similarity >= threshold

def _is_similar_jellyfish(s1: str, s2: str, threshold: float = 0.65) -> bool:
    """Compare two strings for similarity using Jaro-Winkler distance.
    
    Args:
        s1 (str): First string to compare.
        s2 (str): Second string to compare.
        threshold (float, optional): Minimum similarity ratio to consider strings similar. Defaults to 0.65.
    
    Returns:
        bool: True if strings are similar above the threshold, False otherwise.
    """
    s1_norm = _normalize_string(s1)
    s2_norm = _normalize_string(s2)
    similarity = jellyfish.jaro_winkler_similarity(s1_norm, s2_norm)
    return similarity >= threshold

def filter_vocabulary(vocabulary: List[EducatingVocabularyItem], similarity_threshold: float = 0.65) -> List[VocabularyItem]:
    """Filter and prioritize vocabulary items based on similarity, CEFR level, and importance.
    
    This function performs several operations:
    1. Transliterates Russian translations and synonyms to Latin script
    2. Checks for similarity between original words and their transliterations
    3. Filters out words that are too similar to their translations
    4. Prioritizes words based on CEFR level (C2 to A1) and importance (high to low)
    5. Returns up to 3 most relevant vocabulary items
    
    Args:
        vocabulary (List[EducatingVocabularyItem]): List of vocabulary items to filter.
        similarity_threshold (float, optional): Threshold for word similarity comparison. Defaults to 0.65.
    
    Returns:
        List[VocabularyItem]: Filtered list of up to 3 vocabulary items, prioritized by level and importance.
    """
    vocabulary_items = {}

    for word in vocabulary:
        transliterations = [to_latin(word.translation, 'ru')]
        for synonym in word.synonyms:
            transliterations.append(to_latin(synonym, 'ru'))
        
        similar = False
        for transliteration in transliterations:
            is_similar_basic  = _is_similar_basic(word.word, transliteration, similarity_threshold)
            is_similar_jellyfish = _is_similar_jellyfish(word.word, transliteration, similarity_threshold)
            if is_similar_basic or is_similar_jellyfish:
                logger.info(f"Word '{word.word}' is similar to '{word.translation}' ({transliteration})")
                similar = True
                break

        if not similar:
            if word.level not in vocabulary_items:
                vocabulary_items[word.level] = {}
            if word.importance not in vocabulary_items[word.level]:
                vocabulary_items[word.level][word.importance] = []
            logger.info(f"Adding word '{word.word}' with importance '{word.importance}' and level '{word.level}' to candidates vocabulary")
            vocabulary_items[word.level][word.importance].append({"word": word.word.lower(), "translation": word.translation.lower()})

    results = []
    cefr_levels = ['C2', 'C1', 'B2', 'B1', 'A2', 'A1']
    importance_levels = ['high', 'medium', 'low']
    
    # Iterate through CEFR and importance levels in priority order
    for level in cefr_levels:
        if level in vocabulary_items:
            for importance in importance_levels:
                if importance in vocabulary_items[level]:
                    # Add all items from this importance/level combination
                    for item in vocabulary_items[level][importance]:
                        results.append(VocabularyItem(word=item["word"], translation=item["translation"]))
                        if len(results) >= 3:  # Stop once we have 3 items
                            break
                if len(results) >= 3:  # Stop once we have 3 items
                    break
        if len(results) >= 3:  # Stop once we have 3 items
            break
    
    return results