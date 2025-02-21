"""Main entry point for the notifier bot."""

import asyncio
import signal
from datetime import datetime, timezone
from typing import Optional

from telegram import Bot

from ..common.logger import get_component_logger
from ..common.utils import get_trigger_time_info
from ..common.db import init_db
from ..settings import settings
from ..common.constants import COSTA_RICA_TIMEZONE
from .recent_news import process_recent_news


logger = get_component_logger("notifier.main")


class NotifierBot:
    """Main notifier bot class that handles scheduling and execution of routines."""
    
    def __init__(self):
        """Initialize the bot."""
        if not settings.notifier_telegram_bot_token:
            raise ValueError("Telegram bot token not configured")
            
        self._shutdown_event = asyncio.Event()
        self._bot = Bot(token=settings.notifier_telegram_bot_token)
        self._telegram_connection_lost = False
        
        # Initialize with a very old date to ensure first run processes news
        self._previous_run = datetime(1970, 1, 1, tzinfo=COSTA_RICA_TIMEZONE)
        
    async def _execute_routine(self, current_time: datetime) -> None:
        """Execute a single routine at the specified time.
        
        Args:
            current_time: Time for which to execute the routine
        """
        try:
            logger.info("Starting routine for %s", current_time.isoformat())
            await process_recent_news(bot=self._bot, current_time=current_time)
            logger.info("Completed routine for %s", current_time.isoformat())
            
        except Exception as e:
            logger.error(
                "Error in routine for %s: %s",
                current_time.isoformat(), str(e),
                exc_info=True
            )
    
    async def run(self) -> None:
        """Run the bot until shutdown is requested."""
        logger.info("Starting notifier bot")
        
        try:
            # Initialize database
            init_db(settings.database_url)
            
            # Main control loop
            while not self._shutdown_event.is_set():
                current_time = datetime.now(COSTA_RICA_TIMEZONE)
                trigger_info = get_trigger_time_info(current_time)
                
                if trigger_info.current >= self._previous_run:
                    # Check Telegram connectivity before proceeding
                    try:
                        await self._bot.get_me()
                        if self._telegram_connection_lost:
                            logger.info("Telegram connection restored")
                            self._telegram_connection_lost = False
                    except Exception as e:
                        if not self._telegram_connection_lost:
                            logger.error("Failed to connect to Telegram: %s", str(e))
                            self._telegram_connection_lost = True
                    else:
                        # Time to execute a routine
                        self._previous_run = current_time
                        await self._execute_routine(current_time)
                        logger.info(
                            "Next trigger scheduled for %s",
                            trigger_info.next.isoformat()
                        )

                # Calculate sleep duration
                time_to_next = (trigger_info.next - current_time).total_seconds()
                max_sleep = settings.notifier_max_inactivity_interval
                sleep_duration = min(max_sleep, max(0, time_to_next))
                
                logger.debug(
                    "Waiting %.1f seconds (next trigger at %s)",
                    int(sleep_duration),
                    trigger_info.next.isoformat()
                )
                
                try:
                    # Wait for either sleep_duration or shutdown
                    await asyncio.wait_for(
                        self._shutdown_event.wait(),
                        timeout=sleep_duration
                    )
                except asyncio.TimeoutError:
                    # Normal timeout, continue loop
                    pass
            
            logger.info("Shutdown requested, stopping bot")
            
        except Exception as e:
            logger.error("Fatal error in bot: %s", str(e), exc_info=True)
            raise
            
        finally:
            # Close the bot instance
            try:
                await self._bot.close()
            except Exception as e:
                logger.error("Error closing bot: %s", str(e))
            
            logger.info("Notifier bot stopped")
    
    def request_shutdown(self) -> None:
        """Request the bot to shut down gracefully."""
        logger.info("Shutdown requested")
        self._shutdown_event.set()


async def run_bot() -> None:
    """Run the notifier bot with signal handling."""
    # Create and run bot
    bot = NotifierBot()
    
    # Setup signal handlers
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(
            sig,
            lambda s=sig: asyncio.create_task(
                handle_signal(s, bot, loop)
            )
        )
    
    try:
        await bot.run()
    finally:
        # Remove signal handlers
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.remove_signal_handler(sig)


async def handle_signal(sig: signal.Signals, bot: NotifierBot, loop: asyncio.AbstractEventLoop) -> None:
    """Handle shutdown signals."""
    logger.info("Received signal %s", sig.name)
    bot.request_shutdown()


if __name__ == "__main__":
    # Run the bot
    asyncio.run(run_bot()) 