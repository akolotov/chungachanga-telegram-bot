# CRHoy News Reconstructor

A module for processing transcribed CRHoy news videos into separate, well-formatted news stories. It uses a pipeline of LLM-powered components to extract, filter, and correct news stories from video transcriptions.

## Entry Point

The main entry point is the `get_stories_from_transctiption(video_id, cache_db, force)` function which:

- Takes a YouTube video ID and cache database instance
- Returns a list of processed news stories or None if processing fails
- Optionally forces reprocessing with the `force` parameter

## Cache Database Dependency

The module expects the cache database to already contain video transcription data (`TranscriptionData` defined in `crhoy/models.py`) in the `transcription` field for the given video ID, where `text` field contains the raw transcription.

Each component updates specific parts of the `analysis` field in the cache:

1. **Extractor**
   - Updates `analysis.all_sequences` with:
     - Extracted intro text
     - List of separated news stories
     - Outro text

2. **Localizer**
   - Updates `analysis.raw_local_news` with filtered Costa Rica related stories

3. **Corrector**
   - Updates `analysis.final_local_news` with corrected story texts

## Components

The reconstructor consists of three main components, each powered by Google's Gemini LLM:

### 1. Extractor

- Purpose: Splits transcribed text into logical segments
- Input: Raw video transcription from `transcription.text` field in the cache database
- Output: list of news stories
- Key features:
  - Identifies natural breaks between stories
  - Preserves original Spanish text

### 2. Localizer

- Purpose: Filters stories related to Costa Rica
- Input: List of extracted news stories from `analysis.all_sequences.stories` field in the cache database
- Output: List of stories relevant to Costa Rica
- Key features:
  - Identifies both direct and indirect relations to Costa Rica

### 3. Corrector

- Purpose: Improves text quality
- Input: List of Costa Rica related stories from `analysis.raw_local_news` field in the cache database
- Output: List of corrected stories
- Key features:
  - Fixes spelling of names, places, and organizations
  - Adds necessary punctuation
  - Preserves original meaning and context

## Pipeline Flow

The pipeline processes transcriptions in 3 steps:

1. Extract individual stories from the raw transcription
2. Filter stories related to Costa Rica
3. Correct and polish the final text

Each step builds on the previous one to transform raw transcribed text into clean, localized news stories.

As well as each steps:

- Checks cache before processing
- Stores results in cache after processing
- Can be forced to reprocess with `force=True`

## Usage Example

```python
from bot.llm import initialize
from bot.yt_parsers.crhoy.reconstructor import get_stories_from_transctiption
from bot.yt_parsers.crhoy.cache_db import CacheDB

# Initialize Google's Gemini API
initialize()

# Initialize cache DB
cache_db = CacheDB("path/to/cache.db")

# Process video
stories = get_stories_from_transctiption(
    video_id="youtube_video_id",
    cache_db=cache_db,
    force=False  # Set to True to ignore cache
)

if stories:
    for story in stories:
        print(f"- {story}")
```
