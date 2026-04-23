"""
Auto-detect APK Fetcher - just give URL, auto-detect source.

Input: Any APK download URL
- https://github.com/.../releases/download/v1.0.0/app.apk
- https://gitlab.com/.../releases/.../app.apk
- https://gitea.com/.../releases/.../app.apk
- https://apt.izzysoft.de/.../app.apk
- https://f-droid.org/.../app.apk
- https://xxx.com/.../app.apk (any direct URL)

Auto-detects source type from URL pattern.
"""

import re
from typing import Optional

from . import BaseFetcher, ApkInfo


def get_requests():
    from curl_cffi import requests
    return requests


class GitReleaseFetcher(BaseFetcher):
    """Auto-detecting fetcher - URL in, ApkInfo out."""
    
    name = "git_release"
    
    # URL patterns -> source type
    SOURCE_PATTERNS = [
        (r"github\.com.*releases", "github"),
        (r"gitlab\.com", "gitlab"),
        (r"gitea\.com", "gitea"),
        (r"bitbucket\.org", "bitbucket"),
        (r"codeberg\.org", "codeberg"),
        (r"apt\.izzysoft\.de", "izzysoft"),
        (r"f-droid\.org", "fdroid"),
        (r"sourceforge\.net", "sourceforge"),
    ]
    
    def get_latest_version(
        self,
        app_name: str,
        current_version: str,
        url: str = "",
        **kwargs
    ) -> Optional[ApkInfo]:
        """Get latest APK - just give URL.
        
        Args:
            app_name: App name (for logging)
            current_version: Currently tracked version
            url: APK download URL
        """
        if not url:
            print(f"    [-] No url provided for {app_name}")
            return None
        
        url = url.strip()
        
        # Detect source type
        source_type = self._detect_source(url)
        
        print(f"    [*] URL detected: {source_type} → {app_name}")
        
        try:
            if source_type == "direct":
                return self._handle_direct(url, current_version, app_name)
            elif source_type == "github":
                return self._handle_github(url, current_version, app_name)
            elif source_type == "gitlab":
                return self._handle_gitlab(url, current_version, app_name)
            elif source_type == "gitea":
                return self._handle_gitea(url, current_version, app_name)
            elif source_type == "izzysoft":
                return self._handle_izzysoft(url, current_version, app_name)
            elif source_type == "fdroid":
                return self._handle_fdroid(url, current_version, app_name)
            else:
                return self._handle_direct(url, current_version, app_name)
            
        except Exception as e:
            print(f"    [-] Error: {e}")
            return None
    
    def _detect_source(self, url: str) -> str:
        """Detect source type from URL."""
        
        url_lower = url.lower()
        
        for pattern, source in self.SOURCE_PATTERNS:
            if re.search(pattern, url_lower):
                return source
        
        return "direct"
    
    def _parse_release_url(self, url: str) -> dict:
        """Parse components from release URL."""
        
        parts = url.split("/")
        
        result = {"url": url}
        
        try:
            idx = None
            for i, p in enumerate(parts):
                if p == "releases":
                    idx = i
                    break
            
            if idx and idx >= 3:
                result["host"] = parts[2]
                result["owner"] = parts[idx + 1]
                result["repo"] = parts[idx + 2]
                
                if idx + 3 < len(parts):
                    next_part = parts[idx + 3]
                    if next_part == "download" and idx + 4 < len(parts):
                        result["tag"] = parts[idx + 4]
                    else:
                        result["tag"] = next_part
            
        except:
            pass
        
        return result
    
    def _handle_direct(self, url: str, current: str, app_name: str) -> Optional[ApkInfo]:
        """Direct URL - just download and get version."""
        
        filename = url.split("/")[-1].split("?")[0]
        
        # Try to extract version from filename
        version = self._extract_version_from_filename(filename)
        
        if not version:
            version = self._download_get_version(url, app_name)
        
        if version and version != current:
            return ApkInfo(
                version=version,
                download_url=url,
                filename=filename
            )
        
        return None
    
    def _handle_github(self, url: str, current: str, app_name: str) -> Optional[ApkInfo]:
        """GitHub - get version from tag."""
        
        info = self._parse_release_url(url)
        
        host = info.get("host", "github.com")
        owner = info.get("owner", "")
        repo = info.get("repo", "")
        tag = info.get("tag", "")
        
        if not owner or not repo:
            return self._handle_direct(url, current, app_name)
        
        version = tag.lstrip("v") if tag else None
        
        if not version:
            version = self._fetch_github_version(owner, repo, host)
        
        if version and version != current:
            filename = url.split("/")[-1].split("?")[0]
            return ApkInfo(
                version=version,
                download_url=url,
                filename=filename
            )
        
        return None
    
    def _fetch_github_version(self, owner: str, repo: str, host: str) -> Optional[str]:
        """Fetch latest version from GitHub API."""
        
        rs = get_requests()
        url = f"https://api.{host}/repos/{owner}/{repo}/releases/latest"
        
        try:
            r = rs.get(url, headers={"Accept": "application/vnd.github+json"}, impersonate="chrome")
            
            if r.status_code == 200:
                data = r.json()
                tag = data.get("tag_name", "")
                return tag.lstrip("v") if tag else None
            
        except:
            pass
        
        return None
    
    def _handle_gitlab(self, url: str, current: str, app_name: str) -> Optional[ApkInfo]:
        """GitLab."""
        
        info = self._parse_release_url(url)
        host = info.get("host", "gitlab.com")
        owner = info.get("owner", "")
        repo = info.get("repo", "")
        tag = info.get("tag", "")
        
        if not owner or not repo:
            return self._handle_direct(url, current, app_name)
        
        version = tag.lstrip("v") if tag else self._fetch_gitlab_version(owner, repo, host)
        
        if version and version != current:
            filename = url.split("/")[-1].split("?")[0]
            return ApkInfo(
                version=version,
                download_url=url,
                filename=filename
            )
        
        return None
    
    def _fetch_gitlab_version(self, owner: str, repo: str, host: str) -> Optional[str]:
        """Fetch latest from GitLab."""
        
        from urllib.parse import quote
        rs = get_requests()
        project = quote(f"{owner}/{repo}", safe="")
        
        url = f"https://{host}/api/v4/projects/{project}/releases"
        
        try:
            r = rs.get(url, impersonate="chrome")
            
            if r.status_code == 200:
                data = r.json()
                if data:
                    tag = data[0].get("tag_name", "")
                    return tag.lstrip("v") if tag else None
            
        except:
            pass
        
        return None
    
    def _handle_gitea(self, url: str, current: str, app_name: str) -> Optional[ApkInfo]:
        """Gitea."""
        
        info = self._parse_release_url(url)
        host = info.get("host", "gitea.com")
        owner = info.get("owner", "")
        repo = info.get("repo", "")
        tag = info.get("tag", "")
        
        if not owner or not repo:
            return self._handle_direct(url, current, app_name)
        
        version = tag.lstrip("v") if tag else self._fetch_gitea_version(owner, repo, host)
        
        if version and version != current:
            filename = url.split("/")[-1].split("?")[0]
            return ApkInfo(
                version=version,
                download_url=url,
                filename=filename
            )
        
        return None
    
    def _fetch_gitea_version(self, owner: str, repo: str, host: str) -> Optional[str]:
        """Fetch latest from Gitea."""
        
        rs = get_requests()
        url = f"https://{host}/api/v1/repos/{owner}/{repo}/releases/latest"
        
        try:
            r = rs.get(url, impersonate="chrome")
            
            if r.status_code == 200:
                data = r.json()
                tag = data.get("tag_name", "")
                return tag.lstrip("v") if tag else None
            
        except:
            pass
        
        return None
    
    def _handle_izzysoft(self, url: str, current: str, app_name: str) -> Optional[ApkInfo]:
        """IzzySoft APKMirror."""
        
        package = self._extract_package_from_url(url, "izzysoft.de")
        
        if not package:
            return self._handle_direct(url, current, app_name)
        
        rs = get_requests()
        
        api_url = f"https://apt.izzysoft.de/fdroid/api/v2/details/{package}"
        
        try:
            r = rs.get(api_url, impersonate="chrome")
            
            if r.status_code != 200:
                api_url = f"https://apt.izzysoft.de/fdroid/index/apk/{package}"
                r = rs.get(api_url, impersonate="chrome")
            
            if r.status_code == 200:
                try:
                    data = r.json()
                except:
                    return self._scrape_izzysoft(api_url, current)
                
                versions = data.get("versions", [])
                if versions:
                    latest = versions[0]
                    version = latest.get("version", "")
                    apk_url = latest.get("apkurl", "")
                    
                    if version and version != current and apk_url:
                        return ApkInfo(
                            version=version,
                            download_url=apk_url,
                            filename=apk_url.split("/")[-1]
                        )
            
        except Exception as e:
            print(f"    [-] IzzySoft error: {e}")
        
        return None
    
    def _scrape_izzysoft(self, url: str, current: str) -> Optional[ApkInfo]:
        """Scrape IzzySoft page."""
        
        rs = get_requests()
        
        try:
            r = rs.get(url, impersonate="chrome")
            
            if r.status_code == 200:
                v_match = re.search(r'Version:\s*<[^>]*>(\d+\.[^<]+)', r.text)
                a_match = re.search(r'href="(https://[^"]+\.apk)"', r.text)
                
                if v_match and a_match:
                    version = v_match.group(1)
                    apk_url = a_match.group(1)
                    filename = apk_url.split("/")[-1]
                    
                    if version != current:
                        return ApkInfo(
                            version=version,
                            download_url=apk_url,
                            filename=filename
                        )
            
        except:
            pass
        
        return None
    
    def _handle_fdroid(self, url: str, current: str, app_name: str) -> Optional[ApkInfo]:
        """F-Droid."""
        
        package = self._extract_package_from_url(url, "f-droid.org")
        
        if not package:
            return self._handle_direct(url, current, app_name)
        
        rs = get_requests()
        api_url = f"https://f-droid.org/api/v1/packages/{package}"
        
        try:
            r = rs.get(api_url, impersonate="chrome", timeout=30)
            
            if r.status_code == 200:
                data = r.json()
                version = data.get("suggestedVersion", data.get("versionCode", ""))
                apk_url = data.get("apkUrl", "")
                
                if version and version != current and apk_url:
                    return ApkInfo(
                        version=version,
                        download_url=apk_url,
                        filename=apk_url.split("/")[-1]
                    )
            
        except Exception as e:
            print(f"    [-] F-Droid error: {e}")
        
        return None
    
    def _extract_package_from_url(self, url: str, host_pattern: str) -> Optional[str]:
        """Extract package name from URL."""
        
        url_lower = url.lower()
        
        if "izzysoft" in host_pattern and "/apk/" in url_lower:
            return url_lower.split("/apk/")[-1].rstrip("/")
        
        if "f-droid" in host_pattern and "/packages/" in url_lower:
            return url_lower.split("/packages/")[-1].rstrip("/")
        
        return None
    
    def _extract_version_from_filename(self, filename: str) -> Optional[str]:
        """Extract version from filename."""
        
        patterns = [
            r'[_-]v?(\d+\.\d+(?:\.\d+)?)',
            r'_(\d+\.\d+(?:\.\d+)?)',
            r'-(\d+\.\d+(?:\.\d+)\.\d+)',
        ]
        
        for p in patterns:
            m = re.search(p, filename)
            if m:
                return m.group(1)
        
        return None
    
    def _download_get_version(self, url: str, app_name: str) -> Optional[str]:
        """Download APK and extract version with aapt."""
        
        import os
        import subprocess
        
        temp = f"/tmp/{app_name}.apk"
        
        try:
            rs = get_requests()
            r = rs.get(url, stream=True, timeout=60, impersonate="chrome")
            r.raise_for_status()
            
            with open(temp, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            result = subprocess.run(
                ['aapt', 'dump', 'badging', temp],
                capture_output=True, text=True
            )
            
            match = re.search(r"versionName='([^']+)'", result.stdout)
            return match.group(1) if match else None
            
        except Exception:
            pass
        finally:
            if os.path.exists(temp):
                os.remove(temp)
        
        return None