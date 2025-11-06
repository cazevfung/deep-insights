import os
import re
import json
import shutil
import gzip
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from pathlib import Path

from core.config import Config
from loguru import logger

# Try to import brotli for decompression (optional dependency)
try:
    import brotli
    HAS_BROTLI = True
except ImportError:
    HAS_BROTLI = False


def _get_headers(cookies: dict, referer: str, origin: str) -> dict:
    cookie_str = "; ".join([f"{k}={v}" for k, v in cookies.items() if v])
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-User": "?1",
        "sec-ch-ua": '"Chromium";v="119", "Not?A_Brand";v="24"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "Origin": origin,
        "Referer": referer,
        "Cookie": cookie_str,
    }


def _make_session() -> requests.Session:
    s = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=[412, 429, 500, 502, 503, 504],
        allowed_methods=["GET", "HEAD"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=20, pool_maxsize=20)
    s.mount("http://", adapter)
    s.mount("https://", adapter)
    s.headers.update({
        "Connection": "keep-alive",
    })
    return s


def _load_cookies_from_config() -> dict:
    cfg = Config()
    cookies = cfg.get("scrapers.bilibili.cookies", {}) or {}
    # Ensure CURRENT_FNVAL favors DASH
    cookies.setdefault("CURRENT_FNVAL", "4048")
    return cookies


def _extract_bv(url: str) -> str:
    m = re.search(r"BV\w+", url)
    if not m:
        raise ValueError("Only BV links are supported in v1. Please provide a BV URL.")
    return m.group(0)


def _api_get(session: requests.Session, url: str, params: dict, headers: dict) -> dict:
    resp = session.get(url, params=params, headers=headers, timeout=10)
    resp.raise_for_status()
    
    # Check if response is empty
    if not resp.content:
        raise RuntimeError(f"Empty response from API: {url}. Status: {resp.status_code}, Headers: {dict(resp.headers)}")
    
    # Check Content-Encoding to handle compression manually if needed
    # Bilibili API often uses brotli compression which requests doesn't auto-decompress
    content_encoding = resp.headers.get('Content-Encoding', '').lower()
    
    # Manually decompress if needed (requests only auto-decompresses gzip/deflate, not brotli)
    decompressed_content = resp.content
    if content_encoding:
        if 'br' in content_encoding or 'brotli' in content_encoding:
            # Brotli compression - requests doesn't auto-decompress this
            if not HAS_BROTLI:
                raise RuntimeError(f"Brotli compression detected but 'brotli' package not installed. Install with: pip install brotli")
            try:
                decompressed_content = brotli.decompress(resp.content)
            except Exception as e:
                raise RuntimeError(f"Failed to decompress brotli response: {e}")
        elif 'gzip' in content_encoding:
            # Gzip compression - requests should handle this, but ensure it's decompressed
            try:
                decompressed_content = gzip.decompress(resp.content)
            except Exception:
                # If gzip decompress fails, try using resp.text which requests should have decompressed
                decompressed_content = resp.text.encode('utf-8')
    else:
        # No Content-Encoding header, but check if content looks compressed
        # Bilibili sometimes sends compressed responses without the header
        if resp.content and len(resp.content) > 2:
            # Check for gzip magic number (1f 8b) or brotli magic bytes
            if resp.content[:2] == b'\x1f\x8b':
                # Looks like gzip even without header
                try:
                    decompressed_content = gzip.decompress(resp.content)
                except Exception:
                    pass  # If it fails, use original content
            elif HAS_BROTLI and resp.content[:1] == b'\x81':  # Brotli often starts with 0x81
                try:
                    decompressed_content = brotli.decompress(resp.content)
                except Exception:
                    pass  # If it fails, use original content
    
    # Parse JSON from decompressed content
    try:
        data = json.loads(decompressed_content.decode('utf-8'))
    except (json.JSONDecodeError, ValueError, UnicodeDecodeError) as e:
        # If JSON parsing fails, show readable error
        try:
            response_text = decompressed_content.decode('utf-8', errors='replace')
        except Exception:
            response_text = f"<Binary data: {len(decompressed_content)} bytes, Content-Encoding: {content_encoding}>"
        
        preview = response_text[:500] if len(response_text) > 500 else response_text
        raise RuntimeError(f"Failed to parse JSON from {url}. Status: {resp.status_code}, Content-Type: {resp.headers.get('Content-Type')}, Content-Encoding: {content_encoding}, Response preview: {preview}. Error: {e}")
    
    if data.get("code") not in (0, None):
        raise RuntimeError(f"API error {data.get('code')}: {data.get('message')} from {url}")
    return data




def _select_streams(playinfo: dict, preferred_height: int = 480) -> tuple:
    # Support both DASH and durl (FLV) formats
    data = playinfo.get("data", playinfo)
    if not isinstance(data, dict):
        data = {}
    dash = data.get("dash")
    if not dash and data.get("durl"):
        # FLV fallback: return single URL twice, treat as video-only and skip audio
        first = data["durl"][0]
        url = first.get("url")
        if not url:
            raise RuntimeError("No URL in durl entry")
        return url, None
    if not dash:
        raise RuntimeError("DASH info not found in playinfo")

    videos = dash.get("video", [])
    audios = dash.get("audio", [])
    if not videos:
        raise RuntimeError("No video streams available")
    if not audios:
        raise RuntimeError("No audio streams available")

    # Choose video closest to preferred height
    def height_of(v):
        return int(v.get("height") or v.get("codecid") or 0)

    videos_sorted = sorted(videos, key=lambda v: abs(height_of(v) - preferred_height))
    v = videos_sorted[0]
    a = audios[0]

    v_url = v.get("baseUrl") or (v.get("backupUrl") or [None])[0]
    a_url = a.get("baseUrl") or (a.get("backupUrl") or [None])[0]
    if not v_url or not a_url:
        raise RuntimeError("Missing video/audio URLs in DASH")
    return v_url, a_url


def _stream_download(url: str, headers: dict, out_path: Path, session: requests.Session, 
                     progress_callback=None, stage_name="downloading"):
    """
    Download with progress reporting.
    
    Args:
        url: URL to download
        headers: HTTP headers
        out_path: Output file path
        session: requests Session
        progress_callback: Optional callback function(stage, progress, message, bytes_downloaded, total_bytes)
        stage_name: Stage name for progress reporting
    """
    import time
    with session.get(url, headers=headers, stream=True, timeout=300) as r:
        r.raise_for_status()
        
        # Get total size if available
        total_bytes = int(r.headers.get('content-length', 0))
        downloaded = 0
        last_reported_percent = -1
        last_reported_time = time.time()
        report_interval = 0.5  # Report at most every 0.5 seconds
        
        with open(out_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 256):  # 256KB chunks
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    
                    # Report progress frequently (every 1% or every 0.5s, whichever comes first)
                    if total_bytes > 0 and progress_callback:
                        percent = int((downloaded / total_bytes) * 100)
                        current_time = time.time()
                        
                        # Report if:
                        # 1. Percentage changed by at least 1%, OR
                        # 2. At least 0.5 seconds have passed since last report
                        if (percent != last_reported_percent or 
                            (current_time - last_reported_time) >= report_interval):
                            
                            mb_downloaded = downloaded / (1024 * 1024)
                            mb_total = total_bytes / (1024 * 1024)
                            progress_callback(
                                stage_name,
                                percent,
                                f"Downloading ({mb_downloaded:.2f} MB / {mb_total:.2f} MB)",
                                downloaded,
                                total_bytes
                            )
                            last_reported_percent = percent
                            last_reported_time = current_time
                    elif progress_callback and not total_bytes:
                        # If we don't know total size, report every 1MB
                        if downloaded % (1024 * 1024) < len(chunk):
                            mb_downloaded = downloaded / (1024 * 1024)
                            progress_callback(
                                stage_name,
                                0,
                                f"Downloading ({mb_downloaded:.2f} MB)",
                                downloaded,
                                0
                            )


def _merge_with_moviepy(video_path: Path, audio_path: Path, out_path: Path):
    # Lazy import to avoid requiring moviepy if not used elsewhere
    from moviepy.editor import VideoFileClip, AudioFileClip

    if audio_path is None:
        # Single stream case: just move/copy
        shutil.move(str(video_path), str(out_path))
        return

    clip_v = VideoFileClip(str(video_path))
    clip_a = AudioFileClip(str(audio_path))
    clip_v = clip_v.with_audio(clip_a)
    # Re-encode to MP4 with AAC audio for compatibility
    clip_v.write_videofile(str(out_path), codec="libx264", audio_codec="aac", bitrate="1200k", audio_bitrate="128k", logger=None)
    clip_a.close()
    clip_v.close()


def _merge_with_ffmpeg(video_path: Path, audio_path: Path | None, out_path: Path) -> bool:
    import subprocess
    try:
        if audio_path is None:
            # Remux or move
            cmd = [
                "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                "-i", str(video_path),
                "-c", "copy",
                str(out_path)
            ]
        else:
            cmd = [
                "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                "-i", str(video_path),
                "-i", str(audio_path),
                "-c:v", "copy", "-c:a", "aac",
                str(out_path)
            ]
        subprocess.check_call(cmd)
        return True
    except Exception:
        return False


def download_bilibili_480p(url: str, out_dir: str | Path, progress_callback=None) -> dict:
    """
    Download a Bilibili BV URL at ~480p, merge A+V to MP4, and return paths.
    
    Args:
        url: Bilibili video URL
        out_dir: Output directory
        progress_callback: Optional callback function(stage, progress, message, bytes_downloaded, total_bytes)

    Returns: {
      'video_mp4': Path,
      'audio_path': Path,
      'merged_mp4': Path,
      'title': str
    }
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    cookies = _load_cookies_from_config()
    origin = "https://www.bilibili.com"
    headers = _get_headers(cookies, referer=origin + "/", origin=origin)
    session = _make_session()
    # Load cookies into session cookiejar for API/CDN consistency
    for k, v in cookies.items():
        try:
            session.cookies.set(k, v, domain=".bilibili.com")
        except Exception:
            pass

    # Resolve b23 short links
    if re.search(r"https?://(b23\\.tv|b22\\.top)/", url):
        try:
            r = session.get(url, timeout=10, allow_redirects=False)
            loc = r.headers.get("Location")
            if loc and "bilibili.com" in loc:
                url = loc
        except Exception:
            pass

    bv = _extract_bv(url)
    # Use old API endpoints (no WBI needed)
    view = _api_get(session, "https://api.bilibili.com/x/web-interface/view", {"bvid": bv}, headers)
    data_view = view.get("data", {})
    cid = data_view.get("cid") or (data_view.get("pages") or [{}])[0].get("cid")
    title = data_view.get("title") or bv
    if not cid:
        raise RuntimeError("Failed to resolve cid from view API")
    # qn=32 (480p) preferred; fnval=4048 enables DASH; API may ignore qn with DASH but helps for durl
    play = _api_get(session, "https://api.bilibili.com/x/player/playurl", {"bvid": bv, "cid": cid, "qn": 32, "fnver": 0, "fnval": 4048, "fourk": 0}, headers)
    playinfo = {"data": play.get("data", {})}

    # Derive a title-safe basename
    title = title or bv
    safe_base = re.sub(r"[^\w\-\.]+", "_", title)[:80]

    v_url, a_url = _select_streams(playinfo, preferred_height=480)

    # If FLV single stream, download and remux; else download A+V
    is_single = a_url is None
    temp_video = out_dir / (f"{safe_base}.video.mp4" if not v_url.endswith('.flv') else f"{safe_base}.flv")
    temp_audio = None if is_single else out_dir / f"{safe_base}.audio.m4a"
    merged_mp4 = out_dir / f"{safe_base}.mp4"

    # Download video stream with progress (5% - 35% of overall progress)
    if progress_callback:
        progress_callback("downloading", 5, "Starting video download")
    _stream_download(v_url, headers, temp_video, session, progress_callback, "downloading")
    
    # Download audio stream if needed (35% - 45% of overall progress)
    if not is_single and temp_audio is not None and a_url is not None:
        if progress_callback:
            progress_callback("downloading", 35, "Starting audio download")
        _stream_download(a_url, headers, temp_audio, session, progress_callback, "downloading")

    # Merge streams (45% - 50% of overall progress)
    if progress_callback:
        progress_callback("converting", 45, "Merging video and audio")
    merged = _merge_with_ffmpeg(temp_video, temp_audio, merged_mp4)
    if not merged:
        if progress_callback:
            progress_callback("converting", 47, "Using moviepy for merging")
        _merge_with_moviepy(temp_video, temp_audio, merged_mp4)
    
    if progress_callback:
        progress_callback("downloading", 50, "Video download complete")

    # Cleanup temp streams
    for p in (temp_video, temp_audio if temp_audio is not None else None):
        if p is None:
            continue
        try:
            p.unlink(missing_ok=True)  # type: ignore[attr-defined]
        except Exception:
            pass

    return {
        "video_mp4": merged_mp4,
        "audio_path": None,
        "merged_mp4": merged_mp4,
        "title": title or bv,
    }


def mp4_to_mp3(mp4_path: Path, mp3_path: Path) -> bool:
    from utils.convert_mp4_to_mp3 import convert_mp4_to_mp3
    return convert_mp4_to_mp3(str(mp4_path), str(mp3_path))


