"""Background checker service for periodic Dojo status updates."""
import threading
import time
import os
import fcntl
from typing import List, Dict, Any
from pathlib import Path

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
        self._lock_file = None
        self._lock_path = Path("/tmp/dojobay_checker.lock")
    
    def start(self) -> None:
        """Start the background checker thread."""
        if self._running:
            print("[WARNING] Background checker already running")
            return
        
        # Try to acquire exclusive lock
        try:
            self._lock_file = open(self._lock_path, 'w')
            fcntl.flock(self._lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            print(f"[INFO] Acquired background checker lock (PID: {os.getpid()})")
        except (IOError, OSError):
            print(f"[INFO] Another background checker is running, skipping (PID: {os.getpid()})")
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        print(f"[INFO] Background checker started (PID: {os.getpid()})")
    
    def stop(self) -> None:
        """Stop the background checker thread."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        
        # Release lock
        if self._lock_file:
            try:
                fcntl.flock(self._lock_file.fileno(), fcntl.LOCK_UN)
                self._lock_file.close()
                self._lock_path.unlink(missing_ok=True)
            except Exception:
                pass
        
        print("[INFO] Background checker stopped")
    
    def _run(self) -> None:
        """Main loop for background checking."""
        # Perform initial check immediately
        try:
            results = self.checker.check_all(self.mainnet_dojos, self.testnet_dojos)
            self.cache.save(results)
            print(f"[INFO] Initial status check completed at {results['last_update']}")
        except Exception as e:
            print(f"[ERROR] Initial background check failed: {e}")

        checks_since_cleanup = 0
        # Run cleanup once per day (86400s / check_interval cycles)
        cleanup_every = max(1, 86400 // self.check_interval)

        # Continue with periodic checks
        while self._running:
            time.sleep(self.check_interval)

            try:
                results = self.checker.check_all(self.mainnet_dojos, self.testnet_dojos)
                self.cache.save(results)
                print(f"[INFO] Status check completed at {results['last_update']}")
            except Exception as e:
                print(f"[ERROR] Background check failed: {e}")

            checks_since_cleanup += 1
            if checks_since_cleanup >= cleanup_every:
                checks_since_cleanup = 0
                try:
                    from app import _cleanup_old_submissions
                    _cleanup_old_submissions()
                except Exception as e:
                    print(f"[ERROR] Cleanup failed: {e}")
