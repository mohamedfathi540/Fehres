"""
Web scraping controller for library documentation.
Handles sitemap discovery, crawling, and HTML content extraction.
"""
from .BaseController import basecontroller
from Helpers.Config import get_settings
from Utils.ContentFilter import extract_main_content, extract_links, extract_metadata, is_beneficial_link
from langchain_community.document_loaders import AsyncHtmlLoader
from typing import List, Set, Dict, Optional, Iterator
import requests
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser
import time
import logging
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)

# Global cancel flag - can be set to stop any running scrape
GLOBAL_SCRAPE_CANCEL = {"requested": False}


class ScrapingController(basecontroller):
    """Controller for scraping library documentation from URLs."""
    
    def __init__(self):
        super().__init__()
        self.settings = get_settings()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': self.settings.SCRAPING_USER_AGENT
        })
    
    def _check_robots_txt(self, base_url: str) -> Optional[RobotFileParser]:
        """Check robots.txt and return parser if available."""
        try:
            robots_url = urljoin(base_url, '/robots.txt')
            rp = RobotFileParser()
            rp.set_url(robots_url)
            rp.read()
            return rp
        except Exception as e:
            logger.warning(f"Could not parse robots.txt for {base_url}: {e}")
            return None

    def verify_url_accessible(self, url: str) -> bool:
        """Check if the URL is accessible (returns 200-299 status code)."""
        try:
            response = self.session.head(url, timeout=5, allow_redirects=True)
            if 200 <= response.status_code < 300:
                return True
            # Fallback to GET if HEAD fails (some servers block HEAD)
            response = self.session.get(url, timeout=5, stream=True)
            response.close()
            return 200 <= response.status_code < 300
        except Exception as e:
            logger.warning(f"URL verification failed for {url}: {e}")
            return False
    
    def _can_fetch(self, robots_parser: Optional[RobotFileParser], url: str) -> bool:
        """Check if URL can be fetched according to robots.txt."""
        if getattr(self.settings, "SCRAPING_IGNORE_ROBOTS", False):
            return True
        if robots_parser is None:
            return True
        return robots_parser.can_fetch(self.settings.SCRAPING_USER_AGENT, url)
    
    def discover_pages_from_sitemap(
        self,
        base_url: str,
        visited_sitemaps: Optional[Set[str]] = None,
        depth: int = 0,
        max_depth: int = 5,
    ) -> List[str]:
        """
        Discover pages from sitemap.xml.
        Returns list of URLs found in sitemap.
        """
        urls = []
        if visited_sitemaps is None:
            visited_sitemaps = set()
        if depth > max_depth:
            logger.warning(f"Max sitemap depth reached for {base_url}")
            return urls

        # If a sitemap URL was provided, use it directly.
        if base_url.endswith(".xml"):
            sitemap_urls = [base_url]
        else:
            # Try standard sitemap locations
            sitemap_urls = [
                urljoin(base_url, 'sitemap.xml'),
                urljoin(base_url, 'sitemap_index.xml'),
                urljoin(base_url, '/sitemap.xml'),
                urljoin(base_url, '/sitemap_index.xml'),
            ]
            
            # Check if robots.txt has specific sitemap
            robots_parser = self._check_robots_txt(base_url)
            if robots_parser and robots_parser.site_maps():
                sitemap_urls.extend(robots_parser.site_maps())
            
            # Remove duplicates while preserving order
            seen = set()
            sitemap_urls = [x for x in sitemap_urls if not (x in seen or seen.add(x))]
        
        for sitemap_url in sitemap_urls:
            if sitemap_url in visited_sitemaps:
                continue
            visited_sitemaps.add(sitemap_url)
            try:
                response = self.session.get(sitemap_url, timeout=self.settings.SCRAPING_TIMEOUT)
                if response.status_code == 200:
                    # Parse XML sitemap
                    root = ET.fromstring(response.content)
                    
                    # Handle sitemap index
                    if root.tag.endswith('sitemapindex'):
                        for sitemap_elem in root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}sitemap'):
                            loc_elem = sitemap_elem.find('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')
                            if loc_elem is not None:
                                nested_sitemap_url = (loc_elem.text or "").strip()
                                if not nested_sitemap_url:
                                    continue
                                nested_urls = self.discover_pages_from_sitemap(
                                    nested_sitemap_url,
                                    visited_sitemaps=visited_sitemaps,
                                    depth=depth + 1,
                                    max_depth=max_depth,
                                )
                                urls.extend(nested_urls)
                    
                    # Handle regular sitemap
                    elif root.tag.endswith('urlset'):
                        for url_elem in root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}url'):
                            loc_elem = url_elem.find('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')
                            if loc_elem is not None:
                                url = loc_elem.text
                                if is_beneficial_link(url, base_url, set()):
                                    urls.append(url)
                    
                    logger.info(f"Found {len(urls)} URLs in sitemap: {sitemap_url}")
                    break  # Use first successful sitemap
            except Exception as e:
                logger.warning(f"Could not parse sitemap {sitemap_url}: {e}")
                continue
        
        return urls
    
    def discover_pages_by_crawling(self, base_url: str, max_pages: int = None) -> List[str]:
        """
        Discover pages by crawling from base URL.
        Uses BFS to discover all pages.
        """
        if max_pages is None:
            max_pages = self.settings.SCRAPING_MAX_PAGES
        
        visited: Set[str] = set()
        to_visit: List[str] = [base_url]
        discovered_urls: List[str] = [base_url]
        
        robots_parser = self._check_robots_txt(base_url)
        
        while to_visit and len(discovered_urls) < max_pages:
            current_url = to_visit.pop(0)
            
            if current_url in visited:
                continue
            
            visited.add(current_url)
            
            # Check robots.txt
            if not self._can_fetch(robots_parser, current_url):
                logger.info(f"Skipping {current_url} (robots.txt disallows)")
                continue
            
            try:
                # Rate limiting
                time.sleep(self.settings.SCRAPING_RATE_LIMIT)
                
                response = self.session.get(
                    current_url,
                    timeout=self.settings.SCRAPING_TIMEOUT,
                    allow_redirects=True
                )
                
                if response.status_code != 200:
                    logger.warning(f"Failed to fetch {current_url}: HTTP {response.status_code}")
                    continue
                
                # Check content type
                content_type = response.headers.get('Content-Type', '').lower()
                if 'text/html' not in content_type:
                    logger.debug(f"Skipping {current_url} (not HTML: {content_type})")
                    continue
                
                # Extract links
                html_content = response.text
                links = extract_links(html_content, base_url, visited)
                
                # Add new links to queue
                for link in links:
                    if link not in visited and len(discovered_urls) < max_pages:
                        discovered_urls.append(link)
                        to_visit.append(link)
                
                logger.debug(f"Discovered {len(discovered_urls)} pages so far...")
                
            except Exception as e:
                logger.error(f"Error crawling {current_url}: {e}")
                continue
        
        logger.info(f"Crawling discovered {len(discovered_urls)} pages")
        return discovered_urls
    
    def discover_pages(self, base_url: str) -> List[str]:
        """
        Discover pages using sitemap first, fallback to crawling.
        """
        max_pages_limit = self.settings.SCRAPING_MAX_PAGES
        
        # Try sitemap first
        urls = self.discover_pages_from_sitemap(base_url)
        
        # If sitemap didn't find enough pages, supplement with crawling
        if len(urls) < 10:
            logger.info("Sitemap found few pages, supplementing with crawling...")
            crawled_urls = self.discover_pages_by_crawling(base_url)
            # Merge and deduplicate
            all_urls = list(set(urls + crawled_urls))
            return all_urls[:max_pages_limit]
        
        return urls[:max_pages_limit]
    
    def _fetch_html_playwright(self, url: str) -> Optional[str]:
        """Fetch page HTML using Playwright (headless browser). Returns None on failure."""
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                try:
                    page = browser.new_page()
                    page.set_default_timeout(self.settings.SCRAPING_TIMEOUT * 1000)
                    page.goto(url, wait_until="domcontentloaded")
                    page.wait_for_timeout(500)
                    html_content = page.content()
                    return html_content
                finally:
                    browser.close()
        except Exception as e:
            logger.warning(f"Playwright fetch failed for {url}: {e}")
            return None

    def scrape_page(self, url: str, log_debug_first: bool = False) -> tuple[Optional[Dict], Optional[str]]:
        """
        Scrape a single page and return content with metadata.
        Returns (dict, None) with 'content', 'metadata', 'url' on success;
        (None, skip_reason) when skipped.
        """
        html_content = None
        try:
            if getattr(self.settings, 'SCRAPING_USE_BROWSER', False):
                html_content = self._fetch_html_playwright(url)
                if not html_content:
                    logger.warning(f"Skip {url}: playwright_fetch_failed")
                    return (None, "playwright_fetch_failed")
            else:
                response = self.session.get(
                    url, timeout=self.settings.SCRAPING_TIMEOUT,
                    allow_redirects=True, stream=True
                )
                if response.status_code != 200:
                    response.close()
                    logger.warning(f"Skip {url}: non-200 status={response.status_code}")
                    return (None, f"non-200 status={response.status_code}")
                content_type = response.headers.get('Content-Type', '').lower()
                if 'text/html' not in content_type:
                    response.close()
                    logger.warning(f"Skip {url}: non-html content_type={content_type[:80]}")
                    return (None, f"non-html content_type={content_type[:80]}")
                html_content = response.text

            content = extract_main_content(html_content, url)
            metadata = extract_metadata(html_content, url)
            content_len = len(content.strip()) if content else 0

            if log_debug_first and getattr(self.settings, 'SCRAPING_DEBUG', False):
                snippet = (content or "")[:500].replace("\n", " ")
                logger.info(
                    f"[SCRAPE_DEBUG] url={url} html_len={len(html_content)} "
                    f"extracted_len={content_len} snippet={snippet!r}"
                )
                print(
                    f"[SCRAPE] DEBUG first URL: html_len={len(html_content)} "
                    f"extracted_len={content_len}"
                )

            if not content or content_len < 50:
                logger.warning(
                    f"Skip {url}: insufficient_content extracted_len={content_len}"
                )
                return (None, f"insufficient_content extracted_len={content_len}")

            return ({
                'content': content,
                'metadata': metadata,
                'url': url
            }, None)
        except Exception as e:
            logger.error(f"Skip {url}: exception {e!r}")
            return (None, f"exception {e!r}")
    
    def scrape_documentation(self, base_url: str, cancel_ref: Optional[Dict] = None) -> List[Dict]:
        """
        Main method to scrape entire documentation site.
        Returns list of page content dictionaries.
        If cancel_ref is provided and cancel_ref.get("requested") becomes True, stops and returns partial results.
        """
        print(f"[SCRAPE] Starting documentation scrape for: {base_url}")
        logger.info(f"Starting documentation scrape for: {base_url}")
        
        # Discover pages
        urls = self.discover_pages(base_url)
        print(f"[SCRAPE] Discovered {len(urls)} pages to scrape")
        logger.info(f"Discovered {len(urls)} pages to scrape")
        
        # Scrape each page
        scraped_pages = []
        first_skip_reason: Optional[str] = None
        skipped_by_robots = 0
        robots_parser = self._check_robots_txt(base_url)
        
        for i, url in enumerate(urls, 1):
            # Check global cancel flag
            if GLOBAL_SCRAPE_CANCEL.get("requested"):
                logger.info(f"[SCRAPE] Global cancel requested: {len(scraped_pages)}/{len(urls)} pages scraped")
                print(f"[SCRAPE] Global cancel. Scraped {len(scraped_pages)}/{len(urls)} pages.", flush=True)
                GLOBAL_SCRAPE_CANCEL["requested"] = False  # Reset for next scrape
                return scraped_pages
            
            # Check for cancel request
            if cancel_ref and cancel_ref.get("requested"):
                logger.info(f"[SCRAPE] Cancelled by user: {len(scraped_pages)}/{len(urls)} pages scraped")
                print(f"[SCRAPE] Cancelled. Scraped {len(scraped_pages)}/{len(urls)} pages.", flush=True)
                return scraped_pages
            # Check robots.txt
            if not self._can_fetch(robots_parser, url):
                skipped_by_robots += 1
                if skipped_by_robots == 1:
                    logger.warning(f"[SCRAPE] robots.txt disallows URL (user-agent: {self.settings.SCRAPING_USER_AGENT[:50]}...): {url}")
                    print(f"[SCRAPE] robots.txt disallows URLs. First skipped: {url}", flush=True)
                continue
            
            # Rate limiting
            if i > 1:
                time.sleep(self.settings.SCRAPING_RATE_LIMIT)
            
            log_debug_first = (
                i == 1 and getattr(self.settings, 'SCRAPING_DEBUG', False)
            )
            page_data, skip_reason = self.scrape_page(url, log_debug_first=log_debug_first)
            if page_data:
                scraped_pages.append(page_data)
                logger.info(f"[SCRAPE] OK {i}/{len(urls)}: {url}")
                print(f"[SCRAPE] OK {i}/{len(urls)}: {url}", flush=True)
            else:
                reason = skip_reason or "unknown"
                if first_skip_reason is None:
                    first_skip_reason = reason
                logger.warning(f"[SCRAPE] SKIP {i}/{len(urls)}: {url} ({reason})")
                print(f"[SCRAPE] SKIP {i}/{len(urls)}: {url} ({reason})", flush=True)
        
        if not scraped_pages:
            if skipped_by_robots == len(urls):
                msg = f"[SCRAPE] All {len(urls)} pages skipped: robots.txt disallows all URLs for this user-agent."
                logger.warning(msg)
                print(msg, flush=True)
            elif first_skip_reason:
                logger.warning(f"[SCRAPE] All pages skipped. Reason: {first_skip_reason}")
                print(f"[SCRAPE] All pages skipped. Reason: {first_skip_reason}", flush=True)
        logger.info(f"[SCRAPE] Done: {len(scraped_pages)}/{len(urls)} pages scraped")
        print(f"[SCRAPE] Successfully scraped {len(scraped_pages)} out of {len(urls)} pages", flush=True)
        return scraped_pages

    def scrape_documentation_iter(
        self,
        base_url: str,
        cancel_ref: Optional[Dict] = None,
        urls: Optional[List[str]] = None,
    ) -> Iterator[Dict]:
        """
        Stream scraped pages one-by-one.
        Yields dicts with keys: url, page_data, skip_reason, index, total.
        """
        print(f"[SCRAPE] Starting documentation scrape (stream) for: {base_url}")
        logger.info(f"Starting documentation scrape (stream) for: {base_url}")

        if urls is None:
            urls = self.discover_pages(base_url)
        total = len(urls)
        print(f"[SCRAPE] Discovered {total} pages to scrape", flush=True)
        logger.info(f"Discovered {total} pages to scrape")

        robots_parser = self._check_robots_txt(base_url)
        for i, url in enumerate(urls, 1):
            if GLOBAL_SCRAPE_CANCEL.get("requested"):
                logger.info(f"[SCRAPE] Global cancel requested: {i-1}/{total} pages scraped")
                print(f"[SCRAPE] Global cancel. Scraped {i-1}/{total} pages.", flush=True)
                GLOBAL_SCRAPE_CANCEL["requested"] = False
                return

            if cancel_ref and cancel_ref.get("requested"):
                logger.info(f"[SCRAPE] Cancelled by user: {i-1}/{total} pages scraped")
                print(f"[SCRAPE] Cancelled. Scraped {i-1}/{total} pages.", flush=True)
                return

            if not self._can_fetch(robots_parser, url):
                logger.warning(
                    f"[SCRAPE] robots.txt disallows URL (user-agent: {self.settings.SCRAPING_USER_AGENT[:50]}...): {url}"
                )
                yield {
                    "url": url,
                    "page_data": None,
                    "skip_reason": "robots.txt disallows URL",
                    "index": i,
                    "total": total,
                }
                continue

            if i > 1:
                time.sleep(self.settings.SCRAPING_RATE_LIMIT)

            log_debug_first = (
                i == 1 and getattr(self.settings, "SCRAPING_DEBUG", False)
            )
            page_data, skip_reason = self.scrape_page(url, log_debug_first=log_debug_first)
            yield {
                "url": url,
                "page_data": page_data,
                "skip_reason": skip_reason,
                "index": i,
                "total": total,
            }

    def scrape_page_debug(self, url: str) -> Dict:
        """
        Fetch one URL and return debug info: status, content_type, html_len,
        extracted_len, and first 500 chars of extracted text. No storage.
        """
        result = {
            "url": url,
            "status_code": None,
            "content_type": None,
            "html_len": 0,
            "extracted_len": 0,
            "extracted_snippet": "",
            "error": None,
        }
        try:
            if getattr(self.settings, 'SCRAPING_USE_BROWSER', False):
                html_content = self._fetch_html_playwright(url)
                if not html_content:
                    result["error"] = "playwright_fetch_failed"
                    return result
                result["status_code"] = 200
                result["content_type"] = "text/html"
            else:
                response = self.session.get(
                    url, timeout=self.settings.SCRAPING_TIMEOUT,
                    allow_redirects=True
                )
                result["status_code"] = response.status_code
                result["content_type"] = response.headers.get("Content-Type", "") or ""
                html_content = response.text
            result["html_len"] = len(html_content)
            content = extract_main_content(html_content, url)
            result["extracted_len"] = len(content.strip()) if content else 0
            result["extracted_snippet"] = (content or "").strip()[:500]
        except Exception as e:
            result["error"] = str(e)
        return result
