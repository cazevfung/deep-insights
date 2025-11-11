"""Download Inter font for PDF export."""
import urllib.request
import zipfile
from pathlib import Path

url = 'https://github.com/rsms/inter/releases/download/v4.0/Inter-4.0.zip'
zip_path = 'Inter-4.0.zip'

print(f"Downloading Inter font from {url}...")
urllib.request.urlretrieve(url, zip_path)

fonts_dir = Path('backend/app/services/fonts')
fonts_dir.mkdir(parents=True, exist_ok=True)

with zipfile.ZipFile(zip_path, 'r') as zf:
    # Extract specific font files we need
    members = [m for m in zf.namelist() if 
               'Inter-Regular.ttf' in m or 
               'Inter-Bold.ttf' in m or 
               'Inter-SemiBold.ttf' in m or
               'Inter-Medium.ttf' in m]
    zf.extractall(fonts_dir, members)
    print(f'Extracted {len(members)} font files to {fonts_dir}')

# Clean up
import os
os.remove(zip_path)
print("Done!")

