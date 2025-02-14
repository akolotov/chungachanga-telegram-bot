"""Main entry point for the notifier bot."""

import asyncio
import signal
from datetime import datetime
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
            
        self._current_task: Optional[asyncio.Task] = None
        self._next_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()
        self._bot = Bot(token=settings.notifier_telegram_bot_token)
        
    async def _execute_routine(self, scheduled_time: datetime) -> None:
        """Execute a single routine at the scheduled time.
        
        Args:
            scheduled_time: When this routine was scheduled to run
        """
        try:
            logger.info("Starting routine scheduled for %s", scheduled_time.isoformat())
            await process_recent_news(bot=self._bot, current_time=scheduled_time)
            logger.info("Completed routine scheduled for %s", scheduled_time.isoformat())
            
        except Exception as e:
            logger.error(
                "Error in routine scheduled for %s: %s",
                scheduled_time.isoformat(), str(e),
                exc_info=True
            )
            
        finally:
            # Clear the current task reference
            self._current_task = None
    
    def _schedule_next_routine(self, after_time: datetime) -> None:
        """Schedule the next routine to run after the given time.
        
        Args:
            after_time: Schedule next routine after this time
        """
        # Get next trigger time
        trigger_info = get_trigger_time_info(after_time)
        next_time = trigger_info.next
        
        # Calculate delay until next run
        now = datetime.now(COSTA_RICA_TIMEZONE)
        delay = (next_time - now).total_seconds()
        if delay < 0:
            # If we're already past the next time, schedule immediately
            delay = 0
            next_time = now
        
        logger.info(
            "Scheduling next routine for %s (in %.1f seconds)",
            next_time.isoformat(), delay
        )
        
        # Create and schedule the next task
        async def delayed_routine():
            try:
                # Wait until the scheduled time
                await asyncio.sleep(delay)
                
                # Check if we should still run
                if self._shutdown_event.is_set():
                    logger.info("Shutdown requested, cancelling scheduled routine")
                    return
                
                # If there's a current task running, wait for it
                if self._current_task and not self._current_task.done():
                    logger.info(
                        "Previous routine still running, waiting for completion"
                    )
                    try:
                        await self._current_task
                    except Exception:
                        # Previous task errors are already logged
                        pass
                
                # Become the current task and run
                self._current_task = asyncio.current_task()
                await self._execute_routine(next_time)
                
            finally:
                # Schedule the next routine before we finish
                if not self._shutdown_event.is_set():
                    self._schedule_next_routine(next_time)
                self._next_task = None
        
        # Schedule the next task
        self._next_task = asyncio.create_task(delayed_routine())
    
    async def run(self) -> None:
        """Run the bot until shutdown is requested."""
        logger.info("Starting notifier bot")
        
        try:
            # Initialize database
            init_db(settings.database_url)
            
            # Execute first routine immediately with current time
            now = datetime.now(COSTA_RICA_TIMEZONE)
            self._current_task = asyncio.create_task(self._execute_routine(now))
            
            # Schedule next routine
            self._schedule_next_routine(now)
            
            # Wait for shutdown
            await self._shutdown_event.wait()
            
            # Wait for current routine to finish if any
            if self._current_task and not self._current_task.done():
                logger.info("Waiting for current routine to complete")
                try:
                    await self._current_task
                except Exception:
                    # Errors are already logged
                    pass
            
            # Cancel next scheduled routine if any
            if self._next_task and not self._next_task.done():
                self._next_task.cancel()
                try:
                    await self._next_task
                except asyncio.CancelledError:
                    pass
            
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