# Installing Transcription Upgrade (faster-whisper)

## Quick Install

Upgrade from the poor-quality base Whisper model to faster-whisper with better accuracy:

```bash
# Install faster-whisper
pip install faster-whisper

# Optional: Uninstall the old whisper package (not required, but saves space)
pip uninstall openai-whisper
```

## Verify Installation

```bash
python -c "from faster_whisper import WhisperModel; model = WhisperModel('small'); print('✓ faster-whisper installed successfully!')"
```

Expected output:
```
✓ faster-whisper installed successfully!
```

## What Changed?

### Configuration (config.yaml)
- ✅ Upgraded model: `base` → `small` (better accuracy)
- ✅ Added: `use_faster_whisper: true` (uses faster-whisper)

### Code (bilibili_scraper.py)
- ✅ Supports both faster-whisper and openai-whisper
- ✅ Automatically uses faster-whisper when enabled
- ✅ Falls back to openai-whisper if faster-whisper not installed

### Dependencies (requirements.txt)
- ✅ Replaced `openai-whisper` with `faster-whisper`

## Test It

1. Run your Bilibili scraper test:
```bash
cd tests
python test_bilibili_snapany.py
```

2. Check the transcription quality in the results - you should see much cleaner Chinese text!

## Troubleshooting

### ImportError: No module named 'faster_whisper'
```bash
pip install faster-whisper
```

### Model download fails
```bash
# Manual download test
python -c "from faster_whisper import WhisperModel; m = WhisperModel('small')"
# This will download ~460MB model on first run
```

### Still getting poor quality
Try upgrading to a larger model:
```yaml
bilibili:
  whisper_model: 'medium'  # Instead of 'small'
```

## Performance Notes

- First run: Downloads the model (~460MB for 'small')
- Subsequent runs: Uses cached model
- CPU usage: Moderate (much better than openai-whisper)
- Speed: 4-5x faster than standard Whisper
- Accuracy: Much better for Chinese audio

## Rollback

If you want to go back to the old Whisper:

1. Edit `config.yaml`:
```yaml
bilibili:
  use_faster_whisper: false  # Use old whisper
```

2. Install openai-whisper:
```bash
pip install openai-whisper
```

## Further Improvements

For even better accuracy, consider:

1. **Commercial APIs** (best quality but costs money):
   - AssemblyAI
   - Deepgram
   - Microsoft Azure Speech-to-Text

2. **Larger models** (better quality but slower):
   - `medium` model (1.4GB)
   - `large-v3` model (2.9GB)

3. **Post-processing**:
   - Add punctuation correction
   - Add spell checking
   - Add translation cleanup

See `docs/solutions/TRANSCRIPTION_ALTERNATIVES.md` for more details.

