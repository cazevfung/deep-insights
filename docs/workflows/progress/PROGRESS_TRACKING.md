# Progress Tracking

All scrapers now support progress tracking for downloads and loading operations. This feature is designed to be used when building a client application.

## Overview

The progress tracking system reports progress through stages of:
- **Loading**: Page navigation and content loading
- **Extracting**: Content extraction and processing
- **Downloading**: File downloads with byte-level tracking
- **Uploading**: File uploads to cloud storage
- **Converting**: File format conversion (e.g., MP4 to MP3)
- **Transcribing**: Audio transcription processing

## Usage

### Basic Example

```python
from scrapers.reddit_scraper import RedditScraper

def progress_callback(data):
    """Handle progress updates."""
    print(f"[{data['scraper']}] {data['stage']}: {data['progress']:.1f}% - {data['message']}")

# Create scraper with progress callback
scraper = RedditScraper(progress_callback=progress_callback)

# Extract content - progress will be reported automatically
result = scraper.extract(url)

scraper.close()
```

### Progress Data Structure

The progress callback receives a dictionary with the following fields:

```python
{
    'stage': str,              # Current stage ('loading', 'extracting', 'downloading', etc.)
    'progress': float,         # Progress percentage (0.0 to 100.0)
    'message': str,            # Human-readable status message
    'bytes_downloaded': int,   # Bytes downloaded (if applicable)
    'total_bytes': int,        # Total bytes to download (if applicable)
    'scraper': str             # Type of scraper ('reddit', 'youtube', etc.)
}
```

### Advanced Example with Progress Bar

```python
import sys

def progress_callback(data):
    """Display progress with a visual bar."""
    stage = data['stage']
    progress = data['progress']
    message = data['message']
    
    # Create progress bar
    bar_length = 40
    filled = int(bar_length * progress / 100)
    bar = '█' * filled + '░' * (bar_length - filled)
    
    # For downloading, show byte information
    if data.get('bytes_downloaded') and data.get('total_bytes'):
        mb_downloaded = data['bytes_downloaded'] / (1024 * 1024)
        mb_total = data['total_bytes'] / (1024 * 1024)
        message = f"{message} ({mb_downloaded:.2f} MB / {mb_total:.2f} MB)"
    
    # Print on same line (create smooth progress bar effect)
    sys.stdout.write(f'\r[{stage:12s}] [{bar}] {progress:5.1f}% | {message}')
    sys.stdout.flush()
    
    # New line at 100%
    if progress >= 100:
        print()  # Move to next line
```

## Scraper-Specific Progress

### Reddit Scraper

**Stages:**
- `loading` (10%): Loading Reddit post
- `loading` (30%): Content loaded
- `extracting` (40%): Extracting metadata
- `extracting` (50%): Extracting post content
- `extracting` (70%): Extracting comments
- `extracting` (100%): Extraction complete

### YouTube Scraper

**Stages:**
- `loading` (10%): Loading YouTube video
- `loading` (30%): Video loaded
- `extracting` (40%): Extracting metadata
- `extracting` (50%): Opening transcript
- `extracting` (70%): Extracting transcript segments
- `extracting` (85%): Processing segments
- `extracting` (100%): Extraction complete

### Bilibili Scraper

**Stages:**
- `navigating` (5%): Navigating to SnapAny
- `loading` (10%): Loading SnapAny page
- `extracting` (15%): Submitting video URL
- `extracting` (20%): Processing video link
- `extracting` (30%): Waiting for video to be ready
- `extracting` (40%): Preparing video download
- `extracting` (45%): Opening video page
- `extracting` (47%): Popup page loaded
- `downloading` (50-80%): Downloading video (with byte-level progress)
- `downloading` (80%): Video downloaded
- `converting` (82%): Converting video to audio (MP3)
- `converting` (85%): Audio ready
- `uploading` (87%): Uploading audio to OSS
- `uploading` (89%): Upload complete
- `uploading` (90%): Preparing transcription
- `transcribing` (92%): Calling Paraformer API
- `transcribing` (95%): Transcription completed
- `transcribing` (97%): Downloading transcription result
- `transcribing` (100%): Transcription complete

### Article Scraper

**Stages:**
- `loading` (10%): Loading article
- `loading` (30%): Article loaded
- `loading` (40%): Loading additional content
- `extracting` (50%): Expanding content
- `extracting` (60%): Extracting metadata
- `extracting` (70%): Extracting article content
- `extracting` (100%): Extraction complete

## Integration with Client Apps

### Web Application

```python
from flask import Flask, jsonify, stream_with_context
from scrapers.reddit_scraper import RedditScraper

app = Flask(__name__)

# Store progress in session or database
progress_data = {}

def progress_callback(data):
    """Store progress for client polling."""
    progress_data['url'] = data

@app.route('/extract/<url>')
def extract(url):
    # Start extraction in background
    scraper = RedditScraper(progress_callback=progress_callback)
    result = scraper.extract(url)
    return jsonify(result)

@app.route('/progress')
def progress():
    """Client polls this endpoint for progress updates."""
    return jsonify(progress_data)
```

### CLI Application

```python
import sys

def progress_callback(data):
    """Display progress in CLI."""
    progress = data['progress']
    message = data['message']
    
    # Simple percentage display
    sys.stdout.write(f'\r{progress:5.1f}% - {message}')
    sys.stdout.flush()
    
    if progress >= 100:
        print()  # New line when done
```

### Desktop Application

For GUI applications (e.g., tkinter, PyQt, wxPython):

```python
import tkinter as tk

class ScraperApp:
    def __init__(self, root):
        self.root = root
        self.progress_var = tk.DoubleVar()
        self.status_var = tk.StringVar()
        
    def progress_callback(self, data):
        """Update GUI with progress."""
        self.progress_var.set(data['progress'])
        self.status_var.set(data['message'])
        self.root.update_idletasks()
    
    def extract(self, url):
        scraper = RedditScraper(progress_callback=self.progress_callback)
        result = scraper.extract(url)
        return result
```

## Implementation Details

### Progress Reporting Method

All scrapers inherit from `BaseScraper` which provides the `_report_progress()` method:

```python
self._report_progress(stage, progress, message, bytes_downloaded=0, total_bytes=0)
```

### Optional Callback

The progress callback is optional. If not provided, scrapers work normally without progress tracking:

```python
# Without progress tracking
scraper = RedditScraper()
result = scraper.extract(url)

# With progress tracking
scraper = RedditScraper(progress_callback=my_callback)
result = scraper.extract(url)
```

### Byte-Level Progress

For download operations, progress includes:
- Current bytes downloaded
- Total bytes to download

This allows for accurate download progress bars showing:
- Percentage complete
- MB downloaded / MB total
- Download speed (can be calculated by client)

## Testing

Run the progress tracking test:

```bash
# Test Reddit scraper
python tests/test_progress_tracking.py reddit

# Test YouTube scraper
python tests/test_progress_tracking.py youtube

# Test Article scraper
python tests/test_progress_tracking.py article

# Test Bilibili scraper
python tests/test_progress_tracking.py bilibili
```

## Error Handling

The progress callback should handle errors gracefully:

```python
def progress_callback(data):
    try:
        # Your progress handling code
        pass
    except Exception as e:
        print(f"Progress callback error: {e}")
```

If the callback raises an exception, it's caught and logged without stopping the scraper.

## Future Enhancements

Potential improvements for future versions:
- Real-time download speed reporting
- Estimated time remaining
- Multi-file progress tracking
- WebSocket-based progress streaming
- Progress persistence across restarts






