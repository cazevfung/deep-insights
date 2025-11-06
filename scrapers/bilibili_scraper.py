"""Bilibili video scraper using SnapAny service with browser automation."""
import time
import os
from datetime import datetime
from typing import Dict, Optional
from pathlib import Path
from loguru import logger
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeout
from scrapers.base_scraper import BaseScraper
import requests


class BilibiliScraper(BaseScraper):
    """
    Extract Bilibili videos using in-house downloader + Paraformer transcription.
    
    Process:
    1. Navigate to SnapAny website
    2. Input Bilibili video URL
    3. Click extract button
    4. Wait for download button to appear
    5. Click download button (opens popup)
    6. Download video from popup page
    7. Convert MP4 to MP3 (mp3 format, always)
    8. Upload MP3 to OSS bucket
    9. Get public HTTP URL
    10. Transcribe with Paraformer API
    11. Return transcript
    
    Required Configuration (config.yaml):
      scrapers:
        bilibili:
          dashscope_api_key: 'your-api-key'
          oss_access_key_id: 'your-oss-access-key-id'
          oss_access_key_secret: 'your-oss-access-key-secret'
          oss_bucket: 'your-bucket-name'  # Must be in cn-beijing region
    """
    
    def __init__(self, **kwargs):
        """Initialize Bilibili scraper."""
        super().__init__(**kwargs)
        self.download_dir = Path("downloads")
        self.download_dir.mkdir(exist_ok=True)
        logger.info("[Bilibili] Initialized with in-house downloader")
    
    def validate_url(self, url: str) -> bool:
        """Check if URL is a valid Bilibili URL."""
        return 'bilibili.com' in url.lower()
    
    def extract(self, url: str, batch_id: str = None, link_id: str = None) -> Dict:
        """
        Extract video from Bilibili using official API (WBI) + downloader.
        
        Args:
            url: Bilibili video URL
            batch_id: Optional batch identifier for results
            link_id: Optional link identifier for results
            
        Returns:
            Dictionary with extraction results
        """
        start_time = time.time()
        
        # Set extraction context for progress reporting
        self._set_extraction_context(batch_id, link_id, url)
        
        # Extract BV id from URL
        import re
        bv_id = None
        bv_match = re.search(r'BV([a-zA-Z0-9]+)', url, re.IGNORECASE)
        if bv_match:
            bv_id = "BV" + bv_match.group(1)
        
        try:
            # Use in-house downloader (480p) with progress callback
            from scrapers.bilibili_downloader import download_bilibili_480p
            logger.info("[Bilibili] Downloading with in-house downloader (480p)...")
            self._report_progress("downloading", 0, "Initializing download")
            
            # Create progress callback wrapper for downloader
            def download_progress(stage, progress, message, bytes_downloaded=0, total_bytes=0):
                # Map downloader progress (0-50%) to overall scraper progress (5-50%)
                # The downloader will report 0-50%, we map it to 5-50% of overall
                overall_progress = 5 + (progress * 0.45)  # 5% base + 45% from download
                self._report_progress(stage, overall_progress, message, bytes_downloaded, total_bytes)
            
            result = download_bilibili_480p(url, self.download_dir, progress_callback=download_progress)
            video_path = str(result.get('merged_mp4'))
            
            # Transcribe with Paraformer via Alibaba Cloud
            logger.info("[Bilibili] Transcribing with Paraformer...")
            self._report_progress("transcribing", 80, "Transcribing audio")
            transcript = self._transcribe_with_paraformer(video_path)
            
            # Step 10: Cleanup - Always remove video file after transcription (audio already removed in _transcribe_with_paraformer)
            try:
                if os.path.exists(video_path):
                    os.remove(video_path)
                    logger.info(f"[Bilibili] Cleaned up video file: {video_path}")
            except Exception as e:
                logger.warning(f"[Bilibili] Failed to clean up video file: {e}")
            
            elapsed_time = round(time.time() - start_time, 2)
            
            # Validate transcript - return success=False if transcription failed
            if not transcript:
                logger.error("[Bilibili] Transcription returned empty result")
                return {
                    'success': False,
                    'bv_id': bv_id,
                    'url': url,
                    'content': None,
                    'title': '',
                    'author': '',
                    'publish_date': '',
                    'source': 'Bilibili (via SnapAny + Paraformer)',
                    'language': 'zh-CN',
                    'word_count': 0,
                    'extraction_method': 'snapany_paraformer',
                    'extraction_timestamp': datetime.now().isoformat(),
                    'batch_id': batch_id,
                    'link_id': link_id,
                    'error': 'Transcription returned empty result. Possible timeout or API failure.'
                }
            
            # For Chinese, count characters (not words by splitting)
            word_count = len(transcript)
            
            logger.info(f"[Bilibili] Extracted {word_count} words in {elapsed_time}s")
            
            return {
                'success': True,
                'bv_id': bv_id,
                'url': url,
                'content': transcript,
                'title': '',  # Could be extracted from page if needed
                'author': '',
                'publish_date': '',
                'source': 'Bilibili (via SnapAny + Paraformer)',
                'language': 'zh-CN',
                'word_count': word_count,
                'extraction_method': 'snapany_paraformer',
                'extraction_timestamp': datetime.now().isoformat(),
                'batch_id': batch_id,
                'link_id': link_id,
                'error': None
            }
            
        except Exception as e:
            logger.error(f"[Bilibili] Extraction failed: {e}")
            return self._error_result(url, str(e), batch_id, link_id)
        
        finally:
            pass
    
    def _extract_video_url(self, page: Page) -> str:
        """Extract video URL from popup page."""
        logger.info("[Bilibili] Attempting to extract video URL...")
        
        # Debug: Print page HTML to console
        html = page.content()
        logger.info(f"[Bilibili] Page HTML (first 500 chars): {html[:500]}")
        
        # Try multiple methods to get the video URL
        try:
            # Method 1: Try video source element
            video_selector = 'video source'
            page.wait_for_selector('video', timeout=5000)
            video_source = page.query_selector('video source')
            
            if video_source:
                video_url = video_source.get_attribute('src')
                if video_url:
                    logger.info(f"[Bilibili] Found video URL from source: {video_url[:50]}...")
                    return video_url
            else:
                logger.warning("[Bilibili] No video source element found")
        except Exception as e:
            logger.warning(f"[Bilibili] Method 1 failed: {e}")
        
        # Method 2: Try video element directly
        try:
            video_element = page.query_selector('video')
            if video_element:
                video_url = video_element.get_attribute('src')
                if video_url:
                    logger.info(f"[Bilibili] Found video URL from video element")
                    return video_url
        except:
            pass
        
        # Method 3: Get from any anchor tag (SnapAny download link)
        try:
            download_links = page.query_selector_all('a[href*="upgcxcode"], a[href*="bilivideo"]')
            if download_links:
                video_url = download_links[0].get_attribute('href')
                logger.info(f"[Bilibili] Found video URL from anchor tag")
                return video_url
        except:
            pass
        
        # Method 4: Try to get from iframe if present
        try:
            iframes = page.query_selector_all('iframe')
            for iframe in iframes:
                src = iframe.get_attribute('src')
                if src and 'bilivideo' in src:
                    logger.info("[Bilibili] Found video URL from iframe")
                    return src
        except:
            pass
        
        # Last resort: Get the page URL itself if it's a direct video link
        current_url = page.url
        if 'bilivideo.com' in current_url or '.mp4' in current_url:
            logger.info("[Bilibili] Using page URL as video URL")
            return current_url
        
        raise ValueError("Could not extract video URL from popup. Tried all methods.")
    
    def _extract_video_url_from_page(self, page: Page) -> str:
        """Extract video URL from current page (fallback)."""
        # Look for video download link
        download_link = page.locator('a[href*="upgcxcode"]').first
        video_url = download_link.get_attribute('href')
        
        if not video_url:
            raise ValueError("Could not find video download link")
        
        return video_url
    
    def _download_video_from_popup(self, popup_page: Page, video_url: str) -> str:
        """Download video from popup page using Playwright's download."""
        logger.info(f"[Bilibili] Starting download from: {video_url[:50]}...")
        
        # Generate filename
        filename = f"bilibili_{int(time.time())}.mp4"
        output_path = self.download_dir / filename
        
        # Use Playwright to download from the popup page (preserves session/cookies)
        try:
            # Navigate popup page to the video URL
            popup_page.goto(video_url, timeout=300000, wait_until='domcontentloaded')
            logger.info("[Bilibili] Popup navigated to video URL")
            
            # Get cookies from popup and download with same session
            cookies = popup_page.context.cookies()
            
            # Use requests with the cookies from the Playwright session
            import requests
            
            # Build cookie header
            cookie_header = '; '.join([f"{c['name']}={c['value']}" for c in cookies])
            
            # Set headers
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'https://snapany.com/',
                'Cookie': cookie_header
            }
            
            logger.info("[Bilibili] Downloading with session cookies...")
            response = requests.get(video_url, headers=headers, stream=True, timeout=300)
            response.raise_for_status()
            
            # Get total size if available
            total_bytes = int(response.headers.get('content-length', 0))
            if total_bytes:
                self._report_progress("downloading", 50, f"Downloading video (0 MB)", 0, total_bytes)
            
            # Download file with progress tracking
            downloaded = 0
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        # Report progress every 10%
                        if total_bytes:
                            progress = 50 + (downloaded / total_bytes) * 30  # 50% to 80%
                            self._report_progress("downloading", progress, 
                                                f"Downloading video ({downloaded / (1024*1024):.2f} MB / {total_bytes / (1024*1024):.2f} MB)", 
                                                downloaded, total_bytes)
            
            self._report_progress("downloading", 80, f"Video downloaded: {output_path}")
            logger.info(f"[Bilibili] Video saved to: {output_path}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"[Bilibili] Download failed: {e}")
            raise
    
    def _download_video_direct(self, page: Page, video_url: str) -> str:
        """Download video directly from URL (fallback method)."""
        import requests
        
        # Add referer header (Bilibili CDN requirement)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://www.bilibili.com/'
        }
        
        logger.info(f"[Bilibili] Downloading from: {video_url[:50]}...")
        
        response = requests.get(video_url, headers=headers, stream=True, timeout=300)
        response.raise_for_status()
        
        # Generate filename from URL
        filename = f"bilibili_{int(time.time())}.mp4"
        output_path = self.download_dir / filename
        
        # Download file
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        
        logger.info(f"[Bilibili] Video saved to: {output_path}")
        return str(output_path)
    
    def _transcribe_with_paraformer(self, video_path: str) -> Optional[str]:
        """Transcribe video using Paraformer via Alibaba Cloud."""
        try:
            import subprocess
            import sys
            from pathlib import Path
            
            # Setup ffmpeg PATH if needed (for packaging)
            self._setup_ffmpeg_path()
            
            # Convert MP4 to MP3 using ffmpeg (Paraformer supports MP3)
            logger.info("[Bilibili] Converting MP4 to MP3...")
            self._report_progress("converting", 52, "Preparing conversion")
            audio_path = str(Path(video_path).with_suffix('.mp3'))
            logger.info(f"[Bilibili] Audio path: {audio_path}")
            
            # Get video duration for progress tracking
            import subprocess as sp
            duration_cmd = [
                'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1', video_path
            ]
            duration = 0
            try:
                result = sp.run(duration_cmd, capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    duration = float(result.stdout.strip())
            except:
                pass
            
            # Use ffmpeg to convert to MP3 with optimized settings for Paraformer
            # Use stderr parsing to track progress
            import threading
            import time
            conversion_start_time = time.time()
            conversion_progress = 0
            conversion_done = threading.Event()
            
            def monitor_conversion():
                nonlocal conversion_progress
                while not conversion_done.is_set():
                    # Estimate progress based on elapsed time and duration
                    if duration > 0:
                        elapsed = time.time() - conversion_start_time
                        # Estimate conversion takes about 0.3x duration (fast operation)
                        estimated_total = duration * 0.3
                        if elapsed < estimated_total:
                            conversion_progress = min(85, 52 + (elapsed / estimated_total) * 33)
                            self._report_progress("converting", conversion_progress, 
                                                 f"Converting to MP3 ({elapsed:.1f}s)")
                    else:
                        # If we don't know duration, just show progress
                        conversion_progress = min(82, 52 + 30)
                        self._report_progress("converting", conversion_progress, "Converting to MP3")
                    time.sleep(0.5)  # Update every 0.5 seconds
            
            monitor_thread = threading.Thread(target=monitor_conversion, daemon=True)
            monitor_thread.start()
            
            ffmpeg_cmd = [
                'ffmpeg',
                '-i', video_path,
                '-vn',  # No video
                '-acodec', 'libmp3lame',  # MP3 codec
                '-ar', '16000',  # Sample rate 16kHz (Paraformer optimal)
                '-ac', '1',  # Mono channel
                '-b:a', '32k',  # Low bitrate to reduce file size
                '-y',  # Overwrite output file
                audio_path
            ]
            
            # Run ffmpeg
            result = sp.run(ffmpeg_cmd, capture_output=True, text=True, timeout=120)
            conversion_done.set()
            
            if result.returncode != 0:
                logger.error(f"[Bilibili] Conversion failed: {result.stderr}")
                return None
            
            logger.info(f"[Bilibili] Audio file created: {audio_path}")
            
            # Verify audio file exists
            if not os.path.exists(audio_path):
                logger.error(f"[Bilibili] Audio file not found: {audio_path}")
                return None
            
            file_size = os.path.getsize(audio_path) / (1024*1024)
            logger.info(f"[Bilibili] Audio file verified: {file_size:.2f} MB")
            self._report_progress("converting", 85, f"Audio ready: {file_size:.2f} MB")
            
            # Upload to user's OSS bucket
            logger.info("[Bilibili] Uploading to user's OSS bucket...")
            self._report_progress("uploading", 87, "Uploading audio to OSS")
            upload_result = self._upload_to_oss(audio_path)
            
            if not upload_result:
                logger.error("[Bilibili] Failed to upload to OSS")
                return None
            
            # Get OSS credentials from config
            oss_access_key_id = self.scraper_config.get('oss_access_key_id')
            oss_access_key_secret = self.scraper_config.get('oss_access_key_secret')
            oss_bucket = self.scraper_config.get('oss_bucket', 'transcription-services')
            
            # Generate signed URL for Paraformer access
            object_key = upload_result.get('object_key', '')
            
            if not object_key:
                logger.error("[Bilibili] No object key returned from upload")
                return None
            
            logger.info(f"[Bilibili] Generating signed URL for Paraformer...")
            self._report_progress("uploading", 90, "Preparing transcription")
            signed_url = self._generate_signed_url(oss_bucket, object_key, oss_access_key_id, oss_access_key_secret)
            
            if not signed_url:
                logger.error("[Bilibili] Failed to generate signed URL")
                return None
                
            logger.info(f"[Bilibili] Signed URL generated (expires in 3600s)")
            logger.debug(f"[Bilibili] Using signed URL for Paraformer")
            
            # Transcribe with Paraformer using signed HTTP URL
            logger.info("[Bilibili] Calling Paraformer API...")
            self._report_progress("transcribing", 92, "Calling Paraformer API")
            # Note: Pass None for credentials since we're using signed URL (no OSS credentials needed)
            transcript = self._call_paraformer(signed_url, None, None)
            
            return transcript
            
        except ImportError as e:
            logger.error(f"[Bilibili] Required library not installed: {e}")
            logger.error("[Bilibili] Install with: pip install dashscope")
            return None
        except Exception as e:
            logger.error(f"[Bilibili] Paraformer transcription failed: {e}")
            import traceback
            logger.error(f"[Bilibili] Traceback: {traceback.format_exc()}")
            return None
        finally:
            # Cleanup audio file
            if 'audio_path' in locals():
                try:
                    os.remove(audio_path)
                    logger.info("[Bilibili] Cleaned up audio file")
                except Exception as e:
                    logger.warning(f"[Bilibili] Failed to clean up audio file: {e}")
    
    def _transcribe_with_whisper(self, video_path: str) -> Optional[str]:
        """Transcribe video using Whisper (local transcription)."""
        try:
            from faster_whisper import WhisperModel
            
            # Setup ffmpeg PATH if needed
            self._setup_ffmpeg_path()
            
            # Convert MP4 to MP3 (consistent format)
            import subprocess as sp
            audio_path = str(Path(video_path).with_suffix('.mp3'))
            
            logger.info("[Bilibili] Converting MP4 to MP3 for Whisper...")
            ffmpeg_cmd = [
                'ffmpeg',
                '-i', video_path,
                '-vn',
                '-acodec', 'libmp3lame',
                '-ar', '16000',
                '-ac', '1',
                '-b:a', '32k',
                '-y',
                audio_path
            ]
            
            result = sp.run(ffmpeg_cmd, capture_output=True, text=True, timeout=120)
            if result.returncode != 0:
                logger.error(f"[Bilibili] Conversion failed: {result.stderr}")
                return None
            
            logger.info(f"[Bilibili] Audio created: {audio_path}")
            
            # Load Whisper model
            model_name = self.scraper_config.get('whisper_model', 'small')
            logger.info(f"[Bilibili] Loading Whisper model: {model_name}")
            # Use int8 compute type for CPU compatibility
            model = WhisperModel(model_name, device="cpu", compute_type="int8")
            
            # Transcribe
            logger.info("[Bilibili] Transcribing with Whisper...")
            segments, info = model.transcribe(
                audio_path,
                language='zh',
                beam_size=5,
                vad_filter=True
            )
            
            # Extract text
            transcript_parts = []
            for segment in segments:
                transcript_parts.append(segment.text)
            
            transcript = ' '.join(transcript_parts)
            logger.info(f"[Bilibili] Transcribed {len(transcript)} characters")
            
            # Cleanup
            try:
                os.remove(audio_path)
            except:
                pass
            
            return transcript
            
        except Exception as e:
            logger.error(f"[Bilibili] Whisper transcription failed: {e}")
            return None
    
    def _upload_to_oss(self, file_path: str) -> Optional[dict]:
        """Upload file to user's own OSS bucket (not temporary storage)."""
        try:
            import oss2
            from pathlib import Path
            
            # Get OSS credentials from config
            oss_access_key_id = self.scraper_config.get('oss_access_key_id')
            oss_access_key_secret = self.scraper_config.get('oss_access_key_secret')
            oss_bucket = self.scraper_config.get('oss_bucket')
            oss_endpoint = self.scraper_config.get('oss_endpoint', 'https://oss-cn-beijing.aliyuncs.com')
            
            if not all([oss_access_key_id, oss_access_key_secret, oss_bucket]):
                logger.error("[Bilibili] Missing OSS credentials in config.yaml!")
                logger.error("[Bilibili] Please configure:")
                logger.error("  scrapers:")
                logger.error("    bilibili:")
                logger.error("      oss_access_key_id: 'YOUR_KEY_ID'")
                logger.error("      oss_access_key_secret: 'YOUR_KEY_SECRET'")
                logger.error("      oss_bucket: 'YOUR_BUCKET_NAME'")
                return None
            
            # Create OSS auth
            auth = oss2.Auth(oss_access_key_id, oss_access_key_secret)
            
            # Create bucket object
            bucket = oss2.Bucket(auth, oss_endpoint, oss_bucket)
            
            # Upload file
            file_name = Path(file_path).name
            object_key = f"audio/{file_name}"
            
            logger.info(f"[Bilibili] Uploading to bucket: {oss_bucket}, key: {object_key}")
            
            # Get file size for progress tracking
            file_size = os.path.getsize(file_path)
            
            # Upload with progress tracking
            # OSS2 doesn't support progress callbacks directly, so we'll track by chunks
            file_size_mb = file_size / (1024*1024)
            self._report_progress("uploading", 87, f"Uploading to OSS ({file_size_mb:.2f} MB)")
            
            # Upload in chunks to track progress
            chunk_size = 1024 * 1024 * 5  # 5MB chunks
            uploaded = 0
            
            with open(file_path, 'rb') as f:
                # For small files, upload directly
                if file_size < chunk_size:
                    bucket.put_object(object_key, f)
                    self._report_progress("uploading", 89, f"Upload complete: {file_size_mb:.2f} MB")
                else:
                    # For larger files, upload in chunks and report progress
                    import time
                    last_report_time = time.time()
                    last_report_percent = 0
                    
                    # OSS2 doesn't support chunked upload with progress easily,
                    # so we'll just upload and estimate progress based on file I/O
                    # (In real OSS, this would use multipart upload)
                    bucket.put_object(object_key, f)
                    # Since we can't easily track OSS upload progress, just report completion
                    self._report_progress("uploading", 89, f"Upload complete: {file_size_mb:.2f} MB")
            
            # Keep file as private (we'll use signed URLs for access)
            logger.info("[Bilibili] File uploaded as private")
            
            # Construct base URL (for reference)
            file_url = f"https://{oss_bucket}.oss-cn-beijing.aliyuncs.com/{object_key}"
            
            logger.info(f"[Bilibili] File uploaded successfully: {file_url}")
            
            return {
                'url': file_url,
                'object_key': object_key
            }
            
        except ImportError:
            logger.error("[Bilibili] oss2 not installed. Install with: pip install oss2")
            return None
        except Exception as e:
            logger.error(f"[Bilibili] OSS upload failed: {e}")
            import traceback
            logger.error(f"[Bilibili] Traceback: {traceback.format_exc()}")
            return None
    
    def _generate_signed_url(self, bucket_name: str, object_key: str, access_key_id: str, access_key_secret: str, expires: int = 3600) -> Optional[str]:
        """Generate a signed URL for temporary access to OSS object."""
        try:
            import oss2
            
            # Get OSS endpoint from config
            oss_endpoint = self.scraper_config.get('oss_endpoint', 'https://oss-cn-beijing.aliyuncs.com')
            
            # Create OSS auth and bucket
            auth = oss2.Auth(access_key_id, access_key_secret)
            bucket = oss2.Bucket(auth, oss_endpoint, bucket_name)
            
            # Generate signed URL (valid for 'expires' seconds)
            signed_url = bucket.sign_url('GET', object_key, expires)
            
            logger.info(f"[Bilibili] Generated signed URL (expires in {expires}s)")
            logger.debug(f"[Bilibili] Signed URL: {signed_url[:100]}...")
            
            return signed_url
            
        except Exception as e:
            logger.error(f"[Bilibili] Failed to generate signed URL: {e}")
            import traceback
            logger.error(f"[Bilibili] Traceback: {traceback.format_exc()}")
            return None
    
    def _upload_to_alicloud(self, file_path: str) -> Optional[str]:
        """Upload file to Alibaba Cloud and get temporary URL."""
        try:
            import json
            from pathlib import Path
            
            # Get API key from config or use default
            api_key = self.scraper_config.get('dashscope_api_key', 'sk-57b64160eb2f461390cfa25b2906956b')
            
            # Model name for Paraformer (must match between upload and transcription)
            model_name = self.scraper_config.get('paraformer_model', 'paraformer-v2')
            
            # Step 1: Get upload policy
            logger.info(f"[Bilibili] Getting upload policy from Alibaba Cloud...")
            policy_data = self._get_upload_policy(api_key, model_name)
            
            # Debug: Log available fields in policy_data
            logger.debug(f"[Bilibili] Policy data keys: {list(policy_data.keys())}")
            if 'oss_access_key_id' in policy_data:
                logger.debug(f"[Bilibili] OSS Access Key ID: {policy_data['oss_access_key_id'][:10]}...")
            if 'oss_access_key_secret' in policy_data:
                logger.debug(f"[Bilibili] OSS Access Key Secret: {policy_data['oss_access_key_secret'][:10]}...")
            
            # Step 2: Upload file to OSS
            logger.info(f"[Bilibili] Uploading file to OSS...")
            file_name = Path(file_path).name
            key = f"{policy_data['upload_dir']}/{file_name}"
            
            with open(file_path, 'rb') as file:
                # Determine content type based on file extension
                if file_path.lower().endswith('.mp3'):
                    content_type = 'audio/mpeg'
                elif file_path.lower().endswith('.wav'):
                    content_type = 'audio/wav'
                elif file_path.lower().endswith('.mp4'):
                    content_type = 'video/mp4'
                else:
                    content_type = 'application/octet-stream'
                
                files_data = {
                    'OSSAccessKeyId': (None, policy_data['oss_access_key_id']),
                    'Signature': (None, policy_data['signature']),
                    'policy': (None, policy_data['policy']),
                    'x-oss-object-acl': (None, policy_data['x_oss_object_acl']),
                    'x-oss-forbid-overwrite': (None, policy_data['x_oss_forbid_overwrite']),
                    'key': (None, key),
                    'success_action_status': (None, '200'),
                    'file': (file_name, file, content_type)
                }
                
                response = requests.post(policy_data['upload_host'], files=files_data)
                
                if response.status_code != 200:
                    logger.error(f"[Bilibili] Upload failed: {response.text}")
                    return None
            
            logger.info(f"[Bilibili] File uploaded successfully to: {key}")
            
            # Step 3: Generate URLs
            # Extract bucket name from upload_host
            upload_host = policy_data.get('upload_host', '')
            bucket_name = None
            http_url = None
            
            if upload_host:
                # Extract base URL
                # upload_host format: https://dashscope-file-xxx.oss-cn-beijing.aliyuncs.com
                http_url = f"{upload_host.rstrip('/')}/{key}"
                logger.info(f"[Bilibili] Constructed HTTP URL: {http_url}")
                
                # Extract bucket name from host (format: bucket-name.oss-cn-beijing.aliyuncs.com)
                if '.aliyuncs.com' in upload_host:
                    host_part = upload_host.replace('https://', '').replace('http://', '')
                    bucket_name = host_part.split('.')[0]
                    logger.info(f"[Bilibili] Extracted bucket name: {bucket_name}")
            
            # Return both URLs and OSS credentials
            result = {
                'oss_url': f"oss://{bucket_name}/{key}" if bucket_name else f"oss://{key}",
                'http_url': http_url,
                'key': key,
                'bucket_name': bucket_name,
                'oss_access_key_id': policy_data['oss_access_key_id'],
            }
            
            # Check if oss_access_key_secret exists (it might not be in the policy response)
            if 'oss_access_key_secret' in policy_data:
                result['oss_access_key_secret'] = policy_data['oss_access_key_secret']
                logger.info("[Bilibili] OSS credentials include secret")
            else:
                logger.warning("[Bilibili] OSS Access Key Secret not found in policy data")
            
            return result
            
        except Exception as e:
            logger.error(f"[Bilibili] Upload to Alibaba Cloud failed: {e}")
            import traceback
            logger.error(f"[Bilibili] Traceback: {traceback.format_exc()}")
            return None
    
    def _get_upload_policy(self, api_key: str, model_name: str) -> dict:
        """Get file upload policy from Alibaba Cloud."""
        url = "https://dashscope.aliyuncs.com/api/v1/uploads"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        params = {
            "action": "getPolicy",
            "model": model_name
        }
        
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code != 200:
            raise Exception(f"Failed to get upload policy: {response.text}")
        
        return response.json()['data']
    
    def _call_paraformer(self, file_url: str, oss_access_key_id: Optional[str] = None, oss_access_key_secret: Optional[str] = None) -> Optional[str]:
        """Call Paraformer API to transcribe audio."""
        try:
            from dashscope.audio.asr import Transcription
            from http import HTTPStatus
            import json
            import dashscope
            import os
            
            # Get API key from config or use default
            api_key = self.scraper_config.get('dashscope_api_key', 'sk-57b64160eb2f461390cfa25b2906956b')
            model_name = self.scraper_config.get('paraformer_model', 'paraformer-v2')
            
            # Set API key
            dashscope.api_key = api_key
            
            # For OSS URLs, we need credentials (handled below in URL format check)
            # For HTTP URLs (signed URLs), no credentials needed
            
            # Call Paraformer API using SDK
            logger.info(f"[Bilibili] Calling Paraformer API with model: {model_name}")
            logger.info(f"[Bilibili] File URL: {file_url}")
            
            # Handle different URL formats
            if file_url.startswith('https://'):
                # HTTP/HTTPS URL (e.g., signed URL) - use as-is
                logger.info("[Bilibili] Using HTTP URL (signed URL or public URL)")
                # No conversion needed - HTTP URLs are supported by Paraformer
                # No credentials needed for HTTP URLs
            elif file_url.startswith('oss://'):
                # OSS URL format - needs credentials
                logger.info(f"[Bilibili] Using OSS URL: {file_url}")
                
                # Get OSS credentials (from parameter or config)
                if not oss_access_key_id or not oss_access_key_secret:
                    # Try to get from config
                    config_oss_id = self.scraper_config.get('oss_access_key_id')
                    config_oss_secret = self.scraper_config.get('oss_access_key_secret')
                    
                    if config_oss_id and config_oss_secret:
                        oss_access_key_id = config_oss_id
                        oss_access_key_secret = config_oss_secret
                    else:
                        logger.error("[Bilibili] OSS credentials required for oss:// URLs")
                        return None
                
                # Set credentials for OSS access
                os.environ['OSS_ACCESS_KEY_ID'] = oss_access_key_id
                os.environ['OSS_ACCESS_KEY_SECRET'] = oss_access_key_secret
                logger.info("[Bilibili] Set OSS credentials for Paraformer")
            else:
                logger.error(f"[Bilibili] Unsupported URL format: {file_url[:50]}...")
                return None
            
            # Use SDK's Transcription with async call
            task_response = Transcription.async_call(
                model=model_name,
                file_urls=[file_url],
                language_hints=['zh', 'en']
            )
            
            logger.info(f"[Bilibili] Task created: {task_response.output.task_id}")
            
            # Wait for transcription with progress polling
            # Poll task status periodically to report progress
            task_id = task_response.output.task_id
            self._report_progress("transcribing", 92, "Waiting for transcription to complete")
            
            import time
            start_time = time.time()
            timeout = 600  # 10 minutes
            poll_interval = 2  # Check every 2 seconds
            
            # Use wait method but also poll for progress updates
            last_progress_update = 92
            progress_checked = False
            
            def poll_progress():
                nonlocal last_progress_update, progress_checked
                while time.time() - start_time < timeout:
                    try:
                        # Try to get task status (if SDK supports it)
                        # Note: Transcription.wait might not expose intermediate status
                        # So we'll estimate based on elapsed time
                        elapsed = time.time() - start_time
                        # Paraformer typically takes 30-60% of audio duration
                        # Estimate: assume average 2-3 minutes for typical video
                        estimated_time = 120  # 2 minutes average
                        progress_estimate = min(98, 92 + (elapsed / estimated_time) * 6)
                        
                        if progress_estimate > last_progress_update + 1:  # Update every 1%
                            last_progress_update = progress_estimate
                            self._report_progress("transcribing", progress_estimate, 
                                                 f"Transcribing ({elapsed:.0f}s)")
                    except:
                        pass
                    time.sleep(poll_interval)
            
            # Start progress monitoring in background
            import threading
            progress_thread = threading.Thread(target=poll_progress, daemon=True)
            progress_thread.start()
            
            # Wait for transcription using SDK's wait method
            # Increased timeout from 300s to 600s (10 minutes) to handle longer videos
            transcribe_response = Transcription.wait(task=task_id, timeout=timeout)
            
            self._report_progress("transcribing", 95, "Transcription completed")
            logger.info(f"[Bilibili] Task completed, status: {transcribe_response.status_code}")
            
            # Check task status
            output = transcribe_response.output
            logger.debug(f"[Bilibili] Paraformer response: {json.dumps(output, indent=2, ensure_ascii=False)}")
            
            # Check if task failed
            task_status = output.get('task_status', 'UNKNOWN') if isinstance(output, dict) else getattr(output, 'task_status', 'UNKNOWN')
            
            if task_status == 'FAILED':
                error_code = output.get('code', 'UNKNOWN') if isinstance(output, dict) else getattr(output, 'code', 'UNKNOWN')
                error_msg = output.get('message', 'No error message') if isinstance(output, dict) else getattr(output, 'message', 'No error message')
                logger.error(f"[Bilibili] Transcription task failed: {error_code} - {error_msg}")
                
                # Log detailed error from results
                results = output.get('results', []) if isinstance(output, dict) else getattr(output, 'results', [])
                for result in results:
                    if isinstance(result, dict):
                        file_url = result.get('file_url', 'unknown')
                        result_code = result.get('code', 'unknown')
                        result_msg = result.get('message', 'no message')
                        logger.error(f"[Bilibili] File error for {file_url}: {result_code} - {result_msg}")
                
                return None
            
            if task_status == 'SUCCEEDED' or task_status == 'SUCCESS':
                logger.info("[Bilibili] Transcription completed successfully")
                
                # Extract transcription URL from results
                transcription_url = None
                if isinstance(output, dict):
                    results = output.get('results', [])
                    if results and isinstance(results[0], dict):
                        transcription_url = results[0].get('transcription_url')
                elif hasattr(output, 'results') and output.results:
                    if hasattr(output.results[0], 'transcription_url'):
                        transcription_url = output.results[0].transcription_url
                
                # Download and parse the transcription result
                if transcription_url:
                    logger.info(f"[Bilibili] Downloading transcription result from: {transcription_url[:100]}...")
                    self._report_progress("transcribing", 97, "Downloading transcription result")
                    transcript = self._download_and_parse_transcription(transcription_url)
                else:
                    # Fallback: try to extract sentences from response
                    transcript_parts = []
                    
                    # Try to extract sentences from different possible response structures
                    if isinstance(output, dict):
                        if 'sentences' in output:
                            sentences = output['sentences']
                        elif 'sentence' in output:
                            sentences = output['sentence']
                        elif 'text' in output:
                            sentences = [{'text': output['text']}]
                        else:
                            sentences = []
                    else:
                        if hasattr(output, 'sentences'):
                            sentences = output.sentences
                        elif hasattr(output, 'sentence'):
                            sentences = output.sentence
                        elif hasattr(output, 'text'):
                            sentences = [{'text': output.text}]
                        else:
                            sentences = []
                    
                    # Extract text from sentences
                    for sentence in sentences:
                        if isinstance(sentence, dict):
                            text = sentence.get('text', '')
                        elif hasattr(sentence, 'text'):
                            text = sentence.text
                        else:
                            text = str(sentence)
                        
                        if text:
                            transcript_parts.append(text)
                    
                    transcript = ' '.join(transcript_parts) if transcript_parts else ''
                
                if not transcript:
                    # Fallback: try to extract any text field
                    logger.warning("[Bilibili] No transcript found in response")
                    if isinstance(output, dict):
                        transcript = json.dumps(output, ensure_ascii=False)
                    elif hasattr(output, '__dict__'):
                        transcript = str(output.__dict__)
                    else:
                        transcript = str(output)
                
                logger.info(f"[Bilibili] Extracted transcript: {len(transcript)} characters")
                return transcript
            else:
                logger.error(f"[Bilibili] Transcription in unexpected status: {task_status}")
                logger.error(f"[Bilibili] Full response: {json.dumps(output, indent=2, ensure_ascii=False) if isinstance(output, dict) else str(output)}")
            return None
                
        except Exception as e:
            error_msg = str(e)
            # Check if this is a timeout error
            if 'timeout' in error_msg.lower() or 'Timeout' in str(type(e).__name__):
                logger.error(f"[Bilibili] Paraformer transcription timed out after 600 seconds: {e}")
                logger.error("[Bilibili] This may indicate the video is too long or the API is slow. Consider using a shorter video or increasing timeout.")
            else:
                logger.error(f"[Bilibili] Paraformer API call failed: {e}")
            import traceback
            logger.error(f"[Bilibili] Traceback: {traceback.format_exc()}")
            return None
    
    def _download_and_parse_transcription(self, transcription_url: str) -> Optional[str]:
        """Download transcription result JSON and extract text."""
        try:
            import json
            import requests
            
            logger.info("[Bilibili] Downloading transcription result...")
            response = requests.get(transcription_url, timeout=60)
            response.raise_for_status()
            
            # Parse JSON response
            data = response.json()
            logger.debug(f"[Bilibili] Transcription result keys: {list(data.keys()) if isinstance(data, dict) else 'not a dict'}")
            
            # Extract sentences from transcription result
            sentences = []
            if isinstance(data, dict):
                # Try different possible structures
                if 'transcripts' in data:
                    # Paraformer result structure
                    transcripts = data['transcripts']
                    for transcript in transcripts:
                        if isinstance(transcript, dict) and 'text' in transcript:
                            sentences.append({'text': transcript['text']})
                elif 'sentences' in data:
                    sentences = data['sentences']
                elif 'sentence' in data:
                    sentences = data['sentence']
                elif 'result' in data:
                    # Nested result structure
                    result_data = data['result']
                    if isinstance(result_data, dict):
                        if 'sentences' in result_data:
                            sentences = result_data['sentences']
                        elif 'sentence' in result_data:
                            sentences = result_data['sentence']
                        elif 'text' in result_data:
                            sentences = [{'text': result_data['text']}]
                elif 'text' in data:
                    sentences = [{'text': data['text']}]
            
            # Extract text from sentences
            transcript_parts = []
            for sentence in sentences:
                if isinstance(sentence, dict):
                    text = sentence.get('text', '')
                    # Also check for 'word' key in case sentences contain words
                    if not text and 'word' in sentence:
                        words = sentence.get('word', '')
                        if isinstance(words, str):
                            text = words
                        elif isinstance(words, list):
                            # Join words if it's a list
                            text = ' '.join([w.get('text', '') if isinstance(w, dict) else str(w) for w in words])
                elif hasattr(sentence, 'text'):
                    text = sentence.text
                else:
                    text = str(sentence)
                
                if text:
                    transcript_parts.append(text)
            
            transcript = ' '.join(transcript_parts)
            
            if not transcript:
                logger.warning("[Bilibili] No text found in transcription result, trying full extraction")
                transcript = json.dumps(data, ensure_ascii=False, indent=2)
            
            logger.info(f"[Bilibili] Extracted {len(transcript)} characters from transcription")
            self._report_progress("transcribing", 100, f"Transcription complete: {len(transcript)} characters")
            return transcript
            
        except Exception as e:
            logger.error(f"[Bilibili] Failed to download/parse transcription: {e}")
            import traceback
            logger.error(f"[Bilibili] Traceback: {traceback.format_exc()}")
            return None
    
    def _setup_ffmpeg_path(self):
        """Setup ffmpeg PATH for Whisper if bundled with app."""
        import os
        import sys
        from pathlib import Path
        
        # Try to find ffmpeg in common locations
        if getattr(sys, 'frozen', False):
            # Running as packaged executable
            base_path = Path(sys._MEIPASS)
            ffmpeg_bin = base_path / 'ffmpeg' / 'bin'
        else:
            # Running as script - check if ffmpeg is in PATH or local
            ffmpeg_bin = Path(__file__).parent.parent / 'ffmpeg' / 'bin'
        
        # Check if ffmpeg exists in bundled location
        if ffmpeg_bin.exists() and (ffmpeg_bin / 'ffmpeg.exe').exists():
            ffmpeg_path = str(ffmpeg_bin)
            current_path = os.environ.get("PATH", "")
            if ffmpeg_path not in current_path:
                os.environ["PATH"] = ffmpeg_path + os.pathsep + current_path
                logger.info(f"[Bilibili] Added bundled ffmpeg to PATH: {ffmpeg_path}")
        
        # Also check standard install location
        standard_ffmpeg = Path(r"C:\ffmpeg\ffmpeg-8.0-essentials_build\bin")
        if standard_ffmpeg.exists() and (standard_ffmpeg / 'ffmpeg.exe').exists():
            ffmpeg_path = str(standard_ffmpeg)
            current_path = os.environ.get("PATH", "")
            if ffmpeg_path not in current_path:
                os.environ["PATH"] = ffmpeg_path + os.pathsep + current_path
                logger.debug(f"[Bilibili] Added standard ffmpeg to PATH: {ffmpeg_path}")
    
    def _error_result(self, url: str, error: str, batch_id: str = None, link_id: str = None) -> Dict:
        """Create error result."""
        # Extract BV id from URL for error result
        import re
        bv_id = None
        try:
            bv_match = re.search(r'BV([a-zA-Z0-9]+)', url, re.IGNORECASE)
            if bv_match:
                bv_id = "BV" + bv_match.group(1)
        except:
            pass
        
        return {
            'success': False,
            'bv_id': bv_id,
            'url': url,
            'content': None,
            'title': '',
            'author': '',
            'publish_date': '',
            'source': 'Bilibili',
            'language': 'zh-CN',
            'word_count': 0,
            'extraction_method': 'snapany_browser',
            'extraction_timestamp': datetime.now().isoformat(),
            'batch_id': batch_id,
            'link_id': link_id,
            'error': error
        }

