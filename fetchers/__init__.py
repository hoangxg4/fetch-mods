"""
Base fetcher interface for APK download strategies."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Tuple
import os
import subprocess
import re


@dataclass
class ApkInfo:
    """APK metadata extracted from download."""
    version: str
    download_url: str
    filename: str


class BaseFetcher(ABC):
    """Abstract base class for APK fetchers."""
    
    name: str = "base"  # Fetcher identifier
    
    @abstractmethod
    def get_latest_version(self, app_name: str, current_version: str, **kwargs) -> Optional[ApkInfo]:
        """
        Check for latest version and return APK info if update available.
        
        Args:
            app_name: Application name
            current_version: Version currently tracked
            **kwargs: Fetcher-specific parameters
            
        Returns:
            ApkInfo if new version found, None otherwise
        """
        pass
    
    def download_and_extract_version(self, download_url: str, app_name: str, temp_path: str = "temp.apk") -> Optional[str]:
        """
        Download APK and extract version using aapt.
        
        Args:
            download_url: Direct URL to APK
            app_name: App name for logging
            temp_path: Temporary file path
            
        Returns:
            Version string if successful, None otherwise
        """
        from curl_cffi import requests
        
        try:
            r = requests.get(download_url, stream=True, timeout=60, impersonate="chrome")
            r.raise_for_status()
            
            with open(temp_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            return self._get_apk_version(temp_path)
        except Exception as e:
            print(f"    [-] Download failed for {app_name}: {e}")
            return None
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
    
    def _get_apk_version(self, apk_path: str) -> Optional[str]:
        """Extract versionName from APK using aapt."""
        try:
            result = subprocess.run(
                ['aapt', 'dump', 'badging', apk_path],
                capture_output=True, text=True, check=True
            )
            match = re.search(r"versionName='([^']+)'", result.stdout)
            return match.group(1) if match else None
        except Exception as e:
            print(f"    [-] aapt extraction failed: {e}")
            return None