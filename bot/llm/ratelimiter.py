import threading
import time
import logging
from typing import Optional, Dict

class RateLimiter:
    _instances: Dict[str, "RateLimiter"] = {}
    _instances_lock = threading.Lock()

    def __init__(self, model_name: str, max_requests: int = 60, period: int = 60):
        """
        Initialize the rate limiter.
        
        Args:
            model_name (str): The name of the model this limiter is tracking
            max_requests (int): The maximum number of requests allowed within the period
            period (int): The time window (in seconds) in which max_requests are allowed
        """
        self.model_name = model_name
        self.max_requests = max_requests
        self.period = period
        self.lock = threading.Lock()
        self.request_timestamps = []  # Stores timestamps of the requests

    @classmethod
    def get_instance(cls, model_name: str, max_requests: int = 60, period: int = 60) -> "RateLimiter":
        """
        Get or create a rate limiter instance for the specified model.
        
        Args:
            model_name (str): The name of the model to get/create a limiter for
            max_requests (int): The maximum number of requests allowed within the period
            period (int): The time window (in seconds) in which max_requests are allowed
            
        Returns:
            RateLimiter: The rate limiter instance for the specified model
        """
        with cls._instances_lock:
            if model_name not in cls._instances:
                cls._instances[model_name] = cls(
                    model_name=model_name,
                    max_requests=max_requests,
                    period=period
                )
            return cls._instances[model_name]

    def acquire(self, logger: Optional[logging.Logger] = None):
        """
        Blocks until a request can be made without violating the rate limit.

        Args:
            logger (Optional[logging.Logger]): Logger instance to log delay warnings
        """
        with self.lock:
            now = time.time()
            # Remove entries that are older than the current window
            self.request_timestamps = [
                ts for ts in self.request_timestamps if now - ts < self.period
            ]
            if len(self.request_timestamps) >= self.max_requests:
                # Calculate time to sleep until the oldest request is out of the window
                sleep_time = self.period - (now - self.request_timestamps[0])
                if logger:
                    logger.warning(
                        f"Rate limit reached for model {self.model_name}. "
                        f"Delaying request for {sleep_time:.2f} seconds"
                    )
                time.sleep(sleep_time)
                now = time.time()
                # Clean up timestamps once more after sleep
                self.request_timestamps = [
                    ts for ts in self.request_timestamps if now - ts < self.period
                ]
            # Record the current request time
            self.request_timestamps.append(time.time()) 