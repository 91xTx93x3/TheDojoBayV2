"""Cache management for Dojo status data."""
import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any


class StatusCache:
    """Thread-safe cache for Dojo status data."""
    
    def __init__(self, cache_file: Path, cache_duration: int):
        """
        Initialize the cache.
        
        Args:
            cache_file: Path to the cache file
            cache_duration: Cache validity duration in seconds
        """
        self.cache_file = cache_file
        self.cache_duration = cache_duration
        self._memory_cache: Dict[str, Any] = {"data": None, "timestamp": None}
        self._lock = threading.Lock()
    
    def get(self) -> Optional[Dict[str, Any]]:
        """
        Get cached status if available and recent.
        
        Returns:
            Cached data if valid, None otherwise
        """
        # Check memory cache first
        with self._lock:
            if self._memory_cache["data"] and self._memory_cache["timestamp"]:
                age = (datetime.now() - self._memory_cache["timestamp"]).seconds
                if age < self.cache_duration:
                    return self._memory_cache["data"]
        
        # Fallback to file cache
        return self._load_from_file()
    
    def save(self, data: Dict[str, Any]) -> None:
        """
        Save status data to cache.
        
        Args:
            data: Status data to cache
        """
        # Save to memory
        with self._lock:
            self._memory_cache["data"] = data
            self._memory_cache["timestamp"] = datetime.now()
        
        # Save to file
        self._save_to_file(data)
    
    def _load_from_file(self) -> Optional[Dict[str, Any]]:
        """Load cache from file if valid."""
        if not self.cache_file.exists():
            return None
        
        try:
            with open(self.cache_file, 'r') as f:
                cache = json.load(f)
                cache_time = datetime.fromisoformat(cache['timestamp'])
                age = (datetime.now() - cache_time).seconds
                
                if age < self.cache_duration:
                    return cache['data']
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"Failed to load cache from file: {e}")
        
        return None
    
    def _save_to_file(self, data: Dict[str, Any]) -> None:
        """Save cache to file."""
        try:
            cache = {
                'timestamp': datetime.now().isoformat(),
                'data': data
            }
            with open(self.cache_file, 'w') as f:
                json.dump(cache, f, indent=2)
        except (IOError, OSError) as e:
            print(f"Failed to save cache to file: {e}")

    def invalidate(self) -> None:
        """Clear in-memory cache and delete the cache file."""
        with self._lock:
            self._memory_cache = {"data": None, "timestamp": None}
        try:
            if self.cache_file.exists():
                self.cache_file.unlink()
        except (IOError, OSError) as e:
            print(f"Failed to delete cache file: {e}")
