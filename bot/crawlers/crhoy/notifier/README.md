# News Notifier

## Overview

The News Notifier is a core component of the crawler system. Its primary responsibility is to monitor the database for news articles that have been downloaded, analyzed, and categorized by the downloader component, and then send notifications about these articles to a configured Telegram channel. The notifier sends concise summaries of news articles that are relevant to Costa Rica, organized by smart categories.

## Architecture & Components

The notifier is organized into several modules, each with a clearly defined responsibility:

- **Main Bot (`bot.py`)**  
  The entry point of the notifier. It sets up graceful shutdown signal handlers, initializes the database connection, and implements the main control loop that schedules and executes notification routines at configured trigger times.

- **Recent News Processor (`recent_news.py`)**  
  Implements the core notification flow:
  - Deletes old sent news records
  - Gets list of already sent news IDs
  - Retrieves news articles that need to be sent
  - Processes each news article by retrieving its summary in the configured language
  - Formats and sends messages to Telegram
  - Updates the database to track which news have been sent

- **Telegram Sender (`telegram.py`)**  
  Responsible for:
  - Formatting news data into properly structured Telegram messages
  - Sending messages to the configured Telegram channel
  - Handling retries for failed message sends
  - Properly escaping special characters for Markdown formatting

- **Database Operations (`db.py`)**  
  Provides specialized database functions for the notifier:
  - Deleting old sent news records
  - Retrieving IDs of already sent news
  - Getting news articles that need to be sent
  - Retrieving summary filenames for news articles

- **Data Types (`types.py`)**  
  Defines data structures used by the notifier:
  - `NewsMessageData`: Contains all the information needed to format and send a news message

In addition to these modules, the notifier leverages shared code and components:

- **Models (`models.py`)**  
  Defines the database schema for all crawler components, including tables for storing news content, categories, summaries, and notification status.

- **Database Management (`common/db.py`)**  
  Provides session and connection management for the PostgreSQL database that stores news metadata, content, and analysis results.

- **Settings (`settings.py`)**  
  Centralizes configuration including trigger times, Telegram bot tokens, channel IDs, and message delays.

- **Utilities (`utils.py`)**  
  Provides helper functions for time management, particularly for determining trigger times and intervals.

## Database Organization

The notifier interacts with several database tables to manage news notifications:

### Primary Tables

- **CRHoyNews**:  
  Stores individual news entries with:
  - Unique ID from the source
  - URL to the original article
  - Timestamp of publication
  - Filename where the content is stored

- **CRHoyNotifierNews**:  
  Tracks articles for notification purposes:
  - News ID reference
  - Timestamp for ordering notifications
  - Relationship to Costa Rica (directly, indirectly, or not applicable)
  - Smart category assignment
  - Flags indicating if the article should be skipped or had processing failures

- **CRHoySummary**:  
  Stores summary information for processed articles:
  - News ID reference
  - Language code (e.g., 'en', 'ru', 'es')
  - Path to the summary file

- **CRHoySentNews**:  
  Tracks which news articles have been sent to the Telegram channel:
  - News ID reference
  - Timestamp of the news article
  
  This table is periodically cleaned up to only keep recent records, as older records are no longer needed once the notification window has passed.

This database structure enables:

- Tracking which articles have been sent to avoid duplicate notifications
- Filtering articles by smart categories for targeted notifications
- Retrieving summaries in the configured language for notification messages
- Managing the notification workflow across multiple trigger times

## Notification Flow

The notifier follows a well-defined flow for processing and sending news:

1. **Trigger Time Management**
   - The notifier operates on a schedule defined by `notifier_trigger_times` in settings
   - For each trigger time, it processes news articles published since the previous trigger time
   - A shifted window is used to ensure no news is missed due to processing delays

2. **News Selection**
   - The notifier selects news articles that:
     - Have been analyzed by the downloader
     - Are not marked as skipped or failed
     - Have not been sent before (not in the `crhoy_sent_news` table)
     - Have a timestamp within the current notification window

3. **Message Formatting**
   - For each selected news article:
     - The summary in the configured language is retrieved from the file specified in the database
     - The message is formatted according to a specific template:

       ```plaintext
       {summary}

       _YYYY/MM/DD HH:MM_  # Italic timestamp in Costa Rica timezone
               
       {url}
       #{category}  # or #{parent_category} #{child_category} for hierarchical categories
       ```

4. **Message Sending**
   - Messages are sent to the configured Telegram channel
   - The system implements retry logic for failed sends
   - A delay is enforced between messages to avoid rate limiting

5. **Database Update**
   - After successful sending, the news ID is recorded in the `crhoy_sent_news` table
   - At the beginning of each notification cycle, old records are cleaned up from this table

## Protection Checks & Error Handling

The notifier implements several safeguards to ensure robust operation:

- **Telegram Connectivity Verification**:  
  Before attempting to send messages, the system checks connectivity to the Telegram API and logs appropriate warnings if the connection is lost.

- **Database Integrity**:  
  Each news article is processed in its own transaction, ensuring that failures in one article don't affect others. Importantly, the database is updated with a new record in the `SentNews` table immediately after a message is successfully sent to Telegram. This tight coupling between sending and database updates helps maintain consistency and minimizes the risk of duplicate notifications if the system restarts unexpectedly. While there is still a small window where a message could be sent but the database update might fail, this approach significantly reduces the likelihood of duplicated notifications.

- **Message Retry Logic**:  
  If sending a message fails, the system will retry up to a configurable number of times before giving up.

- **Graceful Shutdown**:  
  Signal handlers (for SIGTERM and SIGINT) update a shared event, allowing the notifier loop to finish current operations and shut down cleanly.

- **Error Recovery**:  
  The system logs errors during message processing but continues with the next article, ensuring that a single failure doesn't stop the entire notification process.

- **Refined Wait Intervals**:  
  The notifier divides the waiting period between trigger times into smaller chunks defined by `NEWS_NOTIFIER_MAX_INACTIVITY_INTERVAL`. This approach ensures that if the host system enters sleep or hibernation mode, the notifier will not be significantly delayed when the system wakes up. By breaking long waits into smaller intervals (maximum 5 minutes by default), the notifier can quickly resume operation and adjust its schedule after system sleep events, preventing long notification delays that would otherwise occur with a single long sleep interval.

## Time Management

The notifier uses a sophisticated time management system to ensure reliable and timely notifications:

- **Trigger Times**:  
  The system operates based on a list of configured trigger times (e.g., 6:00, 12:00, 16:30) when notifications should be sent.

- **Time Windows**:  
  For each trigger time, the system defines a time window from the previous trigger time to the current one, identifying which news articles should be included.

- **Shifted Windows**:  
  To account for processing delays and ensure no news is missed, the system uses a "shifted" previous time that looks further back than the actual previous trigger time.

- **Sleep Calculation**:  
  Between trigger times, the system calculates the optimal sleep duration to wake up exactly at the next trigger time. However, instead of sleeping for the entire duration at once, it breaks this into smaller intervals limited by `NEWS_NOTIFIER_MAX_INACTIVITY_INTERVAL` (default: 5 minutes). This approach serves as a safeguard against system sleep or hibernation, ensuring the notifier can quickly recover and adjust its schedule when the system resumes operation, rather than remaining delayed until the next scheduled wake-up time.

- **Costa Rica Timezone**:  
  All timestamps are managed in Costa Rica timezone (UTC-6) to match the source of the news articles.

## Environment Variables & Configuration

The notifier relies on several environment variables to configure its operation. These variables can be set in your `.env` file and are managed via Pydantic in `settings.py`.

Key configuration variables include:

- **Trigger Times**  
  - `NEWS_NOTIFIER_TRIGGER_TIMES`: JSON array of times during the day when the notifier will be triggered. Default: `["06:00", "12:00", "16:30"]`
  - `NEWS_NOTIFIER_MAX_INACTIVITY_INTERVAL`: Maximum time in seconds that the notifier can sleep without checking for trigger times. Default: `300` (5 minutes)

- **Telegram Settings**  
  - `NEWS_NOTIFIER_TELEGRAM_BOT_TOKEN`: Telegram Bot Token for the news notifier.
  - `NEWS_NOTIFIER_TELEGRAM_CHANNEL_ID`: Telegram channel ID where the bot will post news summaries.
  - `NEWS_NOTIFIER_TELEGRAM_MAX_RETRIES`: Maximum number of retries for sending messages to Telegram. Default: `3`
  - `NEWS_NOTIFIER_TELEGRAM_MESSAGES_DELAY`: Delay in seconds between sending messages to Telegram to avoid rate limits. Default: `1.0`

- **Database**  
  - `CRHOY_CRAWLER_DATABASE_URL`: PostgreSQL connection URL used by SQLAlchemy to manage news content and notification status.

## Usage

To start the notifier, execute the following command:

```bash
python -m bot.crawlers.crhoy.notifier.bot
```

Ensure that your environment is configured with the necessary variables (e.g., database URL, Telegram bot token, channel ID) as specified in your `.env` file and managed by the settings in `settings.py`.

The notifier will run continuously, sending notifications at the configured trigger times and gracefully handling shutdown requests.
