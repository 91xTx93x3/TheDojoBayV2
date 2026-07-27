"""Dojo checker service for monitoring onion URLs."""
import requests
from datetime import datetime
from typing import Dict, Any, List


class DojoChecker:
    """Service for checking Dojo onion service availability."""
    
    def __init__(self, proxies: Dict[str, str], timeout: int = 15):
        """
        Initialize the checker.
        
        Args:
            proxies: Proxy configuration for Tor
            timeout: Request timeout in seconds
        """
        self.proxies = proxies
        self.timeout = timeout
    
    def check_dojo(self, dojo_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check a single Dojo onion URL.
        
        Args:
            dojo_info: Dojo information dictionary
            
        Returns:
            Updated dojo info with status
        """
        entry = dojo_info.copy()
        entry["status"] = "Inactive"
        entry["checked_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Preserve signature if present
        if "signature" in dojo_info and isinstance(dojo_info["signature"], str):
            entry["signature"] = str(dojo_info["signature"])
        elif "signature" in entry:
            entry.pop("signature")
        # Preserve pairing_details if present (needed for signature verification)
        if "pairing_details" in dojo_info and isinstance(dojo_info["pairing_details"], str):
            entry["pairing_details"] = dojo_info["pairing_details"]
        elif "pairing_details" in entry:
            entry.pop("pairing_details")
        
        # Skip check if marked as out of service
        if dojo_info.get("status") == "out_of_service":
            entry["status"] = "Out of Service"
            return entry
        
        url = dojo_info.get("pairing", {}).get("url") or dojo_info.get("url")
        if not url:
            entry["error"] = "Missing or invalid URL"
            print(f"[ERROR] Invalid URL for node: {dojo_info.get('name', 'Unknown')}")
            return entry
        
        # Check URL availability
        return self._check_url(url, entry)
    
    def check_all(self, mainnet_dojos: List[Dict], testnet_dojos: List[Dict]) -> Dict[str, Any]:
        """
        Check all Dojo services.
        
        Args:
            mainnet_dojos: List of mainnet Dojo configurations
            testnet_dojos: List of testnet Dojo configurations
            
        Returns:
            Complete status results with stats
        """
        results = {
            "mainnet": [self.check_dojo(dojo) for dojo in mainnet_dojos],
            "testnet": [self.check_dojo(dojo) for dojo in testnet_dojos],
            "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        results["stats"] = self._calculate_stats(results)
        return results
    
    def _extract_onion_url(self, dojo_info: Dict[str, Any]) -> str:
        """Extract base onion URL from Dojo info."""
        full_url = dojo_info.get("pairing", {}).get("url") or dojo_info.get("url")
        
        if not full_url:
            return ""
        
        idx = full_url.find(".onion")
        if idx != -1:
            return full_url[:idx + 6]
        
        return ""
    
    def _check_url(self, url: str, entry: Dict[str, Any]) -> Dict[str, Any]:
        """Check URL availability via Tor."""
        try:
            resp = requests.get(url, proxies=self.proxies, timeout=self.timeout)
            # Consider service active if we get a response (2xx, 4xx, 5xx)
            # 4xx means server is responding but endpoint/auth issue
            # Only mark inactive if we can't connect at all
            if resp.status_code < 500:
                entry["status"] = "Active"
                # Extract Dojo version
                entry["dojo_version"] = resp.headers.get("X-Dojo-Version")
            else:
                entry["status"] = "Inactive"
                entry["error"] = f"HTTP {resp.status_code}"
        except requests.RequestException as e:
            entry["error"] = f"{type(e).__name__}"
            print(f"[ERROR] {url}: {type(e).__name__}")
        
        return entry
    
    @staticmethod
    def _calculate_stats(results: Dict[str, Any]) -> Dict[str, int]:
        """Calculate statistics from results."""
        return {
            "mainnet_active": sum(1 for d in results["mainnet"] if d["status"] == "Active"),
            "mainnet_total": len(results["mainnet"]),
            "testnet_active": sum(1 for d in results["testnet"] if d["status"] == "Active"),
            "testnet_total": len(results["testnet"])
        }
