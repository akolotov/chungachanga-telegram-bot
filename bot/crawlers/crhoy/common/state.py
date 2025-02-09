"""Shared state management for CRHoy crawler components."""

class CrawlerState:
    """Global state for crawler components."""
    
    def __init__(self):
        """Initialize crawler state."""
        self.should_exit = False
        
    def request_shutdown(self):
        """Request graceful shutdown."""
        self.should_exit = True
        
    def is_shutdown_requested(self) -> bool:
        """Check if shutdown was requested."""
        return self.should_exit


# Global state instance
state = CrawlerState() 