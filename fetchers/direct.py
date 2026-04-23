"""Direct URL fetcher - downloads APK from fixed URL (current implementation)."""

from typing import Optional
from . import BaseFetcher, ApkInfo


class DirectFetcher(BaseFetcher):
    """Fetcher for direct APK URLs (no API lookup)."""
    
    name = "direct"
    
    def get_latest_version(self, app_name: str, current_version: str, download_url: str = "", **kwargs) -> Optional[ApkInfo]:
        """
        Check for updates using direct URL.
        
        Args:
            app_name: Application name
            current_version: Currently tracked version
            download_url: Direct URL to APK file
            **kwargs: Ignored
            
        Returns:
            ApkInfo if new version found, None otherwise
        """
        if not download_url:
            print(f"    [-] No download_url provided for {app_name}")
            return None
        
        version = self.download_and_extract_version(download_url, app_name)
        
        if version and version != current_version:
            return ApkInfo(
                version=version,
                download_url=download_url,
                filename=f"{app_name}_v{version}.apk"
            )
        
        return None