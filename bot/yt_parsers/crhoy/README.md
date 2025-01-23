# CRHoy News Parser

A module for processing CRHoy.com news videos from YouTube. It extracts audio, transcribes it, and processes the transcription to obtain separate, well-formatted news stories.

## Entry Point

The main entry point is the `transcribe_and_split(url, output_dir)` function which:

- Takes a YouTube URL and output directory path
- Downloads the audio, transcribes it, and processes the transcription to obtain separate, well-formatted news stories which are saved in the output directory
- Returns a list of `CapturedNewsStory` objects or None if processing fails
- Each story contains:
  - Text content
  - Audio file path
  - YouTube URL with timestamp

## Pipeline Flow

```plaintext
Extract YouTube Audio → Transcribe Audio → Reconstruct Stories → Split Audio
```

Each step:

- Checks cache before processing
- Stores results in cache after processing

## Components

The parser consists of several key components:

### 1. YouTube Audio Extractor

- Purpose: Downloads and extracts audio from YouTube videos
- Input: YouTube video URL
- Output: Path to extracted MP3 file
- Cache dependency: Updates `audio` field with file path
- Uses: yt-dlp library for reliable YouTube downloads

### 2. Audio Transcriber

- Purpose: Converts audio to text
- Input: Audio file path from cache `audio` field
- Output: `TranscriptionData` with text and word-level timing
- Cache dependency: Updates `transcription` field
- Uses: OpenAI Whisper API for Spanish transcription

### 3. News Reconstructor

- Purpose: Processes transcribed text into separate news stories
- Input: Raw transcription from cache `transcription.text` field
- Output: List of processed news stories
- Uses: Google's Gemini LLM-powered components
- Cache dependency: Updates `analysis` field with extracted, filtered, and corrected stories
- Components:
  - Extractor: Splits text into separate stories
  - Localizer: Filters Costa Rica related stories
  - Corrector: Improves text quality

### 4. Audio Splitter

- Purpose: Creates audio segments for each story
- Input:
  - Original audio file from cache `audio` field
  - Story texts from cache `analysis.final_local_news`
  - Word timing from cache `transcription.words`
- Output: Individual MP3 files for each story
- Key features:
  - Uses text similarity matching to find precise story boundaries
  - Cuts original audio based on identified timestamps
  - Preserves audio quality during splitting

## Cache System

The module uses a JSON-based cache system (`CacheDB`) that:

- Stores all video-related data in a structured format
- Provides specific getters/setters for each data type
- Simplifies data access with video ID as the key
- Maintains data consistency across processing steps

Each video entry contains:

```plaintext
VideoData:
  audio:                                          # Path to audio file
  transcription: TranscriptionData                # Video transcription
    text:                                         # Raw transcription
    word_level_timing: List[TranscriptionWord]    # Word-level timing
  analysis: AnalysisData                          # Processing results
    all_sequences: TranscribedSequences           # Sequences of words logically coupled
      intro: str                                  # Introductory text
      stories: List[str]                          # List of news stories
      outro: str                                  # Outro text
    raw_local_news: List[str]                     # Filtered stories
    final_local_news: List[str]                   # Corrected stories
```

## Usage Example

The module provides a simple interface to process CRHoy news videos:

```python
from bot.llm import initialize
from bot.yt_parsers.crhoy import transcribe_and_split

# Initialize Google's Gemini API
initialize()

# Process video and get stories
stories = transcribe_and_split(
    url="https://www.youtube.com/watch?v=VIDEO_ID",
    output_dir="path/to/output"
)

# Work with extracted stories
if stories:
    for story in stories:
        print(f"\nStory ID: {story.id}")
        print(f"Text: {story.text[:100]}...")
        print(f"Audio file: {story.audio}")
        print(f"Source URL: {story.url}")
```

Each returned story contains:

- `id`: Unique story identifier
- `text`: Full story content
- `audio`: Path to the story's audio file
- `url`: YouTube URL with timestamp
