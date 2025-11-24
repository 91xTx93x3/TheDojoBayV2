"""Background checker service for periodic Dojo status updates."""
import threading
import time
from typing import List, Dict, Any

from checker import DojoChecker
from cache import StatusCache


class BackgroundChecker:
    """Background service for periodic Dojo status checks."""
    
    def __init__(
        self,
        checker: DojoChecker,
        cache: StatusCache,
        mainnet_dojos: List[Dict[str, Any]],
        testnet_dojos: List[Dict[str, Any]],
        check_interval: int
    ):
        """
        Initialize the background checker.
        
        Args:
            checker: DojoChecker instance
            cache: StatusCache instance
            mainnet_dojos: List of mainnet Dojo configurations
            testnet_dojos: List of testnet Dojo configurations
            check_interval: Time between checks in seconds
        """
        self.checker = checker
        self.cache = cache
        self.mainnet_dojos = mainnet_dojos
        self.testnet_dojos = testnet_dojos
        self.check_interval = check_interval
        self._thread = None
        self._running = False
    
    def start(self) -> None:
        """Start the background checker thread."""
        if self._running:
            print("[WARNING] Background checker already running")
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        print("[INFO] Background checker started")
    
    def stop(self) -> None:
        """Stop the background checker thread."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        print("[INFO] Background checker stopped")
    
    def _run(self) -> None:
        """Main loop for background checking."""
        while self._running:
            try:
                results = self.checker.check_all(self.mainnet_dojos, self.testnet_dojos)
                self.cache.save(results)
                print(f"[INFO] Status check completed at {results['last_update']}")
            except Exception as e:
                print(f"[ERROR] Background check failed: {e}")
            
            time.sleep(self.check_interval)
