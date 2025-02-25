# CRHoy Metadata Synchronizer

## Overview

The CRHoy Metadata Synchronizer is a core component of the CRHoy crawler system. Its primary role is to keep the news metadata up-to-date in the database, ensuring that every day's metadata is retrieved, stored, and, if missing, subsequently filled via gap detection and processing.

## Architecture & Components

The synchronizer is organized into several modules, each with a clearly defined responsibility:

- **Main (`main.py`)**  
  The entry point of the synchronizer. It sets up graceful shutdown signal handlers, initializes the database connection, and starts the scheduler loop.

- **Scheduler (`scheduler.py`)**  
  Implements the main loop that continuously:
  - Checks for internet connectivity and CRHoy API availability.
  - Verifies if metadata exists for the current date.
  - Identifies **day switches** and creates records for **gaps** in metadata.
  - Invokes the updater to process new metadata.
  - Processes the earliest detected gaps to backfill missing dates.
  - Waits until the next check interval using refined waiting intervals.

- **Updater (`updater.py`)**  
  Responsible for:
  - Fetching metadata from the CRHoy API.
  - Saving the fetched metadata as JSON files using the file manager.
  - Preparing database updates by adding new news entries and linking them to their respective categories.
  - Marking the corresponding dates as processed in the database.

- **Gap Handler (`gap_handler.py`)**  
  Manages the detection and processing of **gaps** in the metadata:
  - Uses the settings (e.g., `days_chunk_size`) to compute gaps when metadata is missing.
  - Iterates through each date in a gap, attempting to process and update missing metadata.
  - Removes the gap record from the database upon complete successful processing.

In addition to these modules, the synchronizer leverages shared code from the **common** package:

- **Database Management (`common/db.py`)**  
  Provides session and connection management (using SQLAlchemy) and maintains key tables such as `CRHoyMetadata` and `MissedCRHoyMetadata` to support metadata tracking and gap detection.

- **API Client (`common/api_client.py`)**  
  Offers functions to check for:
  - Internet connectivity via `check_internet_connection`.
  - API availability via `check_api_availability`.
  
  It also handles fetching metadata from CRHoy with retries and error handling.

- **File Manager (`common/file_manager.py`)**  
  Handles directory creation and the saving/loading of JSON metadata files into an organized directory structure.

- **Logger (`common/logger.py`) and Shared State (`common/state.py`)**  
  Provide consistent logging across components and a global shared state that supports graceful shutdown procedures.

- **Settings (`settings.py`)**  
  Centralizes configuration including data directories, database URLs, API request timeouts, update intervals, and chunk sizes. The synchronizer uses these environmental settings extensively to control its behavior.

## Environment Variables & Configuration

The synchronizer, along with shared components in the **common** package, relies on several environment variables to configure its operation. These variables can be set in your `.env` file and are managed via Pydantic in `settings.py`.

For example:

- **Data & File Storage**  
  - `CRHOY_CRAWLER_DATA_DIR`: Base directory where metadata and news content are stored.

- **Scheduler & Updater**  
  - `CRHOY_CRAWLER_FIRST_DAY`: The first day from which metadata synchronization starts.
  - `CRHOY_CRAWLER_CHECK_UPDATES_INTERVAL`: Interval (in seconds) between metadata update checks.
  - `CRHOY_CRAWLER_DAYS_CHUNK_SIZE`: Number of days processed in one metadata update iteration.

- **Database**  
  - `CRHOY_CRAWLER_DATABASE_URL`: PostgreSQL connection URL used by SQLAlchemy to manage metadata and gap records.

- **HTTP Client Settings**  
  - `CRHOY_CRAWLER_REQUEST_TIMEOUT`: Timeout for HTTP requests made to the CRHoy API.
  - `CRHOY_CRAWLER_MAX_RETRIES`: Maximum number of retries for failed HTTP requests.

## Database Organization

The synchronizer interacts with the database through SQLAlchemy, managing several key tables:

### Metadata Tracking Tables

- **CRHoyMetadata**:  
  Records metadata for each processed day along with the path to the locally saved JSON file. This ensures that a given date is marked as "processed".

- **MissedCRHoyMetadata**:  
  Tracks **gaps** in metadata processing using PostgreSQL's daterange type. A gap represents a continuous range of dates for which metadata is missing. This allows the system to efficiently detect and schedule processing for historical or skipped dates.

### News Content Tables

- **CRHoyNews**:  
  Stores individual news entries with their:
  - Unique ID from CRHoy
  - URL to the original article
  - Timestamp of publication
  - Filename where the content will be stored (populated later by the downloader)
  - Status flags (skipped, failed) for tracking download attempts

- **CRHoyCategoriesCatalog**:  
  Maintains a catalog of all unique category paths (e.g., "deportes/futbol") encountered in the news metadata. This table serves as a reference for categorizing news articles and ensures category consistency across the system.

- **CRHoyNewsCategories**:  
  Creates many-to-many relationships between news articles and their categories. Each record links a news article ID to a category path, allowing articles to be associated with multiple categories and facilitating efficient category-based queries.

When processing metadata for a date, the synchronizer:

1. Identifies new news entries not yet in the database
2. Adds any new category paths to the catalog
3. Creates the news entries in `CRHoyNews`
4. Establishes category relationships in `CRHoyNewsCategories`
5. Records the processed date in `CRHoyMetadata`

This database structure enables:

- Efficient tracking of processed dates and gaps
- Complete categorization of news articles
- Support for the downloader component to identify which articles need to be fetched
- Quick filtering and searching of news by categories

## Gap & Day Switch Explained

### Day Switch

A **day switch** occurs when the system transitions from one day to the next. At this point, the synchronizer checks if there is metadata available for the new day:

- If no metadata is found, this signals a day switch.
- The system then creates a gap record, marking the beginning of a period where metadata might have been missed.

### Gap

A **gap** is a recorded interval (or range of dates) during which metadata was not fetched or processed. It can occur due to:

- A missed **day switch** (e.g., the crawler starts processing in the middle of a day and misses the start of a new day).
- Temporary issues such as network downtime, API unavailability, or system sleep/hibernation.

These gap records, stored in the `MissedCRHoyMetadata` table, are continuously monitored and processed by the Gap Handler to backfill missing metadata.

## Protection Checks & Error Handling

The synchronizer incorporates several mechanisms to ensure robust operation:

- **Connectivity Verification**:  
  Before any API call, the system checks:
  - **Internet connectivity** via `check_internet_connection`.
  - **API availability** via `check_api_availability`.

- **Database Integrity**:  
  All updates, including gap processing, occur within SQLAlchemy sessions. Each transaction is committed only after successful completion; otherwise, a rollback is performed to prevent inconsistent states.

- **Graceful Shutdown**:  
  Signal handlers (for SIGTERM and SIGINT) update a shared state flag, allowing the scheduler loop to finish current operations and shut down cleanly.

- **Refined Wait Intervals**:  
  The synchronizer divides the configured waiting period (e.g., `CRHOY_CRAWLER_CHECK_UPDATES_INTERVAL`) into smaller time slices. This approach ensures that if the host system sleeps or hibernates, the process will not be affected by a long uninterrupted sleep, and will be able to recheck its state more responsively.

- **Detailed Logging**:  
  All operations, errors, and state changes are logged using the common logger. This provides a detailed audit trail and facilitates troubleshooting.

## Files Stored

- **Metadata JSON Files**:  
  These files are stored in the directory specified by `CRHOY_CRAWLER_DATA_DIR` (typically under `data/crhoy/metadata/`), organized hierarchically by year, month, and day.

- **Gap Records in the Database**:  
  Temporary records in the `MissedCRHoyMetadata` table indicate date ranges that require metadata updates due to missed or failed processing.

## Code Flow Summary

1. **Startup**  
   - `main.py` initializes signal handlers for graceful shutdown.
   - The database connection is established using `init_db()` from `common/db.py`.
   - The scheduler loop is launched.

2. **Main Loop in the Scheduler**  
   - **Connectivity Check**: Verifies both network and API status.
   - **Day Switch Handling**: Detects when a new day begins and verifies if metadata is missing, thus marking the start of a gap.
   - **Current Date Processing**: Updates metadata for the current date.
   - **Gap Processing**: Processes any recorded gap by retrieving and updating historical metadata.
   - **Refined Wait Mechanism**: The scheduler waits until the next check interval by dividing the sleep time into smaller chunks. This minimizes the impact of host system sleep or hibernation on the timing of operations.

3. **Metadata Update with the Updater Module**  
   The `process_metadata_for_date` function handles metadata updates in a single transaction:
   - Fetches metadata from the CRHoy API for the target date (if not provided).
   - Saves the metadata JSON file to disk (if not already saved).
   - Identifies which news IDs from the metadata are new to the database.
   - If no new news is found:
     - Simply marks the date as processed in `CRHoyMetadata`.
   - If new news is found:
     - Prepares news entries with their timestamps and URLs.
     - Extracts and builds category paths from the metadata.
     - Checks which categories are new against `CRHoyCategoriesCatalog`.
     - In a single transaction:
       - Adds new categories to `CRHoyCategoriesCatalog`.
       - Creates news entries in `CRHoyNews`.
       - Establishes category relationships in `CRHoyNewsCategories`.
       - Marks the date as processed in `CRHoyMetadata`.
   - All database operations are wrapped in error handling to ensure consistency.

4. **Graceful Termination**  
   - The synchronizer monitors a shared shutdown flag.
   - Upon receiving a stop signal, the process completes any in-progress tasks and then exits gracefully, recording a final shutdown log.

## Usage

To start the synchronizer, execute the following command:

```bash
python -m bot.crawlers.crhoy.synchronizer.main
```

Ensure that your environment is configured with the necessary variables (e.g., database URL, data directories, notifier settings) as specified in your `.env` file and managed by Pydantic in `settings.py`.
