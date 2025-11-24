"""Data loader for Dojo configurations."""
import json
from pathlib import Path
from typing import List, Dict, Any, Tuple


class DojoDataLoader:
    """Loader for Dojo configuration data."""
    
    def __init__(self, data_file: Path):
        """
        Initialize the loader.
        
        Args:
            data_file: Path to the dojos_data.json file
        """
        self.data_file = data_file
    
    def load(self) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Load Dojo data from JSON file.
        
        Returns:
            Tuple of (mainnet_dojos, testnet_dojos)
        """
        try:
            with open(self.data_file, "r") as f:
                data = json.load(f)
                mainnet = data.get("mainnet", [])
                testnet = data.get("testnet", [])
                return mainnet, testnet
        except FileNotFoundError:
            print(f"[ERROR] Data file not found: {self.data_file}")
            return [], []
        except json.JSONDecodeError as e:
            print(f"[ERROR] Failed to parse JSON: {e}")
            return [], []
        except Exception as e:
            print(f"[ERROR] Failed to load dojos_data.json: {e}")
            return [], []
