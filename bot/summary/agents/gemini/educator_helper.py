from typing import List
import unicodedata
from difflib import SequenceMatcher
import jellyfish
from cyrtranslit import to_latin
from ...models import EducatingVocabularyItem, VocabularyItem
import logging

logger = logging.getLogger(__name__)

def _normalize_string(s: str) -> str:
    """Remove accents and convert to lowercase."""
    return ''.join(
        c for c in unicodedata.normalize('NFD', s.lower())
        if unicodedata.category(c) != 'Mn'
    )

def _is_similar_basic(s1: str, s2: str, threshold: float = 0.65) -> bool:
    """Check similarity using SequenceMatcher."""
    s1_norm = _normalize_string(s1)
    s2_norm = _normalize_string(s2)
    similarity = SequenceMatcher(None, s1_norm, s2_norm).ratio()
    return similarity >= threshold

def _is_similar_jellyfish(s1: str, s2: str, threshold: float = 0.65) -> bool:
    s1_norm = _normalize_string(s1)
    s2_norm = _normalize_string(s2)
    similarity = jellyfish.jaro_winkler_similarity(s1_norm, s2_norm)
    return similarity >= threshold

def filter_vocabulary(vocabulary: List[EducatingVocabularyItem], similarity_threshold: float = 0.65) -> List[VocabularyItem]:
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