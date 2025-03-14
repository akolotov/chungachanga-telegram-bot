# CRHoy News Downloader

## Overview

The CRHoy News Downloader is a core component of the CRHoy crawler system. Its primary responsibility is to download full news article content for news entries that have been identified by the synchronizer, process this content, and prepare it for notification by analyzing, categorizing, and summarizing the articles using AI/LLM agents.

## Architecture & Components

The downloader is organized into several modules, each with a clearly defined responsibility:

- **Main (`main.py`)**  
  The entry point of the downloader. It sets up graceful shutdown signal handlers, initializes the database connection, and starts the scheduler loop.

- **Scheduler (`scheduler.py`)**  
  Implements the main loop that continuously:
  - Checks for internet connectivity and CRHoy website availability.
  - Initializes the LLM engine and smart categories if needed.
  - Invokes the processor to download and process news articles.
  - Waits until the next check interval before repeating.

- **Processor (`processor.py`)**  
  Responsible for:
  - Identifying unprocessed news entries in the database.
  - Downloading and parsing news content from the CRHoy website.
  - Saving the content as markdown files.
  - Updating the database with download status.
  - Triggering the news analyzer for successfully downloaded articles.

- **News Analyzer (`news_analyzer.py`)**  
  Manages the analysis of downloaded news articles:
  - Uses LLM agents to categorize articles into smart categories.
  - Generates concise summaries in English with Russian translations.
  - Saves summaries to text files.
  - Updates the database with categorization and summary information.
  - Determines which articles should be notified based on relevance and categories.

In addition to these modules, the downloader leverages shared code and components:

- **Models (`models.py`)**  
  Defines the database schema for all crawler components, including tables for storing news content, categories, summaries, and notification status.

- **Agent (`agent/`)**  
  A collection of AI/LLM-based agent components that handle text analysis tasks such as categorization and summary generation in multiple languages.

- **Web Parser (`crhoy.py`)**  
  Provides functions to parse the HTML structure of CRHoy news articles and convert the content to markdown format.

- **Database Management (`common/db.py`)**  
  Provides session and connection management for the PostgreSQL database that stores news metadata, content, and analysis results.

- **Settings (`settings.py`)**  
  Centralizes configuration including data directories, database URLs, API settings, download intervals, and AI model parameters.

## Database Organization

The downloader interacts with several database tables to manage news content and analysis:

### Primary Tables

- **CRHoyNews**:  
  Stores individual news entries with:
  - Unique ID from CRHoy
  - URL to the original article
  - Timestamp of publication
  - Filename where the content is stored
  - Status flags (skipped, failed) for tracking download attempts

- **CRHoyNewsCategories**:  
  Maps news articles to their original CRHoy website categories. Used to determine if articles should be skipped based on ignored categories.

- **CRHoySmartCategories**:  
  Stores AI-generated categorization of news articles with:
  - Category name
  - Description of what the category represents
  - Flag indicating if articles in this category should be ignored
  
  The table includes a special `__unknown__` category that serves as a fallback when news analysis fails, ensuring that even failed analyses can be properly recorded in the database.

- **CRHoySummary**:  
  Stores summary information for processed articles:
  - News ID reference
  - Language code ('en' for English, 'ru' for Russian)
  - Path to the summary file

- **CRHoyNotifierNews**:  
  Tracks articles for notification purposes:
  - News ID reference
  - Timestamp for ordering notifications
  - Relationship to Costa Rica (relevant, not relevant, etc.)
  - Smart category assignment
  - Flags indicating if the article should be skipped or had processing failures

This database structure enables:
- Tracking which articles have been downloaded and processed
- Filtering articles by smart categories for targeted notifications
- Maintaining summaries in multiple languages
- Tracking processing status and failures for monitoring

## Protection Checks & Error Handling

The downloader implements several safeguards to ensure robust operation:

- **Connectivity Verification**:  
  Before attempting to download news, the system checks:
  - **Internet connectivity** via `check_internet_connection` in `common/api_client.py`.
  - **Website availability** via `check_website_availability` to ensure CRHoy is accessible.

- **Database Integrity**:  
  Each news article is processed in its own transaction, ensuring that failures in one article don't affect others. Importantly, in `process_news_chunk`, the download status is committed in a separate transaction from the analysis, so even if the analysis fails, the article's download status is preserved in the database.

- **Category Filtering**:  
  The system implements a two-stage filtering approach:
  1. **Download filtering**: In `process_news_chunk` of `processor.py`, articles in categories specified in `settings.ignore_categories` are automatically marked as skipped without downloading their content.
  2. **Analysis filtering**: In `analyze_news` of `news_analyzer.py`, even after downloading, articles may be filtered from notification based on their smart category. The `ignore` field in the `CRHoySmartCategories` table determines if articles in certain categories should skip advanced analysis and notification.

- **Graceful Shutdown**:  
  Signal handlers (for SIGTERM and SIGINT) update a shared state flag, allowing the scheduler loop to finish current operations and shut down cleanly.

- **Error Recovery**:  
  The system tracks failed downloads and analyses, allowing for later retry while preventing the same errors from repeatedly occurring. When analysis fails, the news is still recorded in `CRHoyNotifierNews` with the special `__unknown__` category and the `failed` flag set to `True`.

- **Age Verification**:  
  The analyzer checks if news is too old before processing, focusing resources on more recent content unless forced to analyze older articles.

- **Refined Wait Intervals**:  
  The downloader divides the configured waiting period (e.g., `CRHOY_CRAWLER_DOWNLOAD_INTERVAL`) into smaller time slices of maximum 1 second each. This approach ensures that if the host system sleeps or hibernates, the process will not be affected by a long uninterrupted sleep. It also allows the system to check for shutdown requests more frequently, enabling responsive termination.

## Files Stored

The downloader creates and manages several types of files:

- **News Content Files**:  
  Markdown files containing the full text of news articles, stored in a directory structure organized by date:
  - `data/crhoy/news/YYYY-MM-DD/HH-MM-{id}.md`

- **Summary Files**:
  Text files containing article summaries in English and Russian, stored alongside the content files:
  - `data/crhoy/news/YYYY-MM-DD/HH-MM-{id}-sum.en.txt`, English summary
  - `data/crhoy/news/YYYY-MM-DD/HH-MM-{id}-sum.ru.txt`, Russian translation

- **LLM Response Files** (optional):  
  If `keep_raw_engine_responses` is enabled in settings, the system stores raw responses from the LLM engine for debugging:
  - `data/crhoy/llm/responses/...`

## Code Flow

The downloader follows this processing flow:

1. **Initialization & Setup**
   - Signal handlers are registered for graceful shutdown
   - Database connection is established
   - LLM engine is initialized
   - Smart categories are initialized if the table is empty (populating it with a predefined set of initial categories from `agent/prompts/category.py`)

2. **Main Processing Loop**
   - **Connectivity Check**: Verifies internet and website availability
   - **News Selection**: Implements a two-tier prioritization strategy:
     - First prioritizes recent unprocessed news (within current notification window), ordered chronologically (oldest first)
     - Then selects older unprocessed news in reverse chronological order (newest first) if capacity remains
     - This ensures timely processing of recent news while gradually catching up with backlog
   - **Processing Chunk**: Processes up to `downloads_chunk_size` articles per iteration

3. **For Each News Article**
   - **Category Check**: Verifies if the article belongs to an ignored category
   - **Content Download**: Fetches the article HTML using the web parser
   - **Content Parsing**: Extracts title and body text, converts to markdown
   - **Content Storage**: Saves the markdown content to a file
   - **Status Update**: Updates the database with download status

4. **News Analysis** (for successfully downloaded articles)
   - **Age Check**: Verifies if the article is recent enough to analyze
   - **Category Analysis**: Uses the LLM agents to categorize the article
   - **Relevance Check**: Determines if the article is relevant based on categorization
   - **Summary Generation**: For relevant articles, generates:
     - A concise English summary
     - A Russian translation of the summary
   - **Summary Storage**: Saves summaries to files
   - **Database Update**: Records categorization and summary information

5. **Sleep & Repeat**
   - The system waits for the configured interval (`download_interval`)
   - Uses refined wait intervals (small sleep chunks of max 1 second) to handle system sleep/hibernate gracefully
   - Checks for shutdown requests between each small sleep interval
   - Repeats the process for the next batch of articles

## AI/LLM Agent Integration

The downloader leverages AI language models to perform content analysis tasks including:

1. **Categorization**: Assigning articles to semantic categories based on content analysis
2. **Summarization**: Creating concise summaries of articles in multiple languages (English and Russian)

These capabilities are implemented through a flexible agent framework that can be extended with additional analysis capabilities without requiring significant changes to the core downloader architecture.

## Environment Variables & Configuration

The downloader, along with shared components in the **common** package, relies on several environment variables to configure its operation. These variables can be set in your `.env` file and are managed via Pydantic in `settings.py`.

Key configuration variables include:

- **Data & File Storage**  
  - `CRHOY_CRAWLER_DATA_DIR`: Base directory where news content and summaries are stored. Default: `data/crhoy`

- **Database**  
  - `CRHOY_CRAWLER_DATABASE_URL`: PostgreSQL connection URL used by SQLAlchemy to manage news content and analysis results.

- **Downloader Settings**  
  - `CRHOY_CRAWLER_DOWNLOAD_INTERVAL`: Interval (in seconds) between news download attempts. Default: `60`
  - `CRHOY_CRAWLER_DOWNLOADS_CHUNK_SIZE`: Number of news articles to download in one iteration. Default: `10`
  - `CRHOY_CRAWLER_IGNORE_CATEGORIES`: Comma-separated list of categories to ignore (not download).

- **HTTP Client Settings**  
  - `CRHOY_CRAWLER_REQUEST_TIMEOUT`: Timeout in seconds for HTTP requests made to the CRHoy website. Default: `30.0`
  - `CRHOY_CRAWLER_MAX_RETRIES`: Maximum number of retries for failed HTTP requests. Default: `3`

- **AI/LLM Agent Settings**  
  - `AGENT_ENGINE`: LLM engine to use for agent operations. Default: `GEMINI`
  - `AGENT_ENGINE_API_KEY`: API key for the LLM engine.

## Usage

To start the downloader, execute the following command:

```bash
python -m bot.crawlers.crhoy.downloader.main
```

Ensure that your environment is configured with the necessary variables (e.g., database URL, data directories, LLM API keys) as specified in your `.env` file and managed by the settings in `settings.py`.
