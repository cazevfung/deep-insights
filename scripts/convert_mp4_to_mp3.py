"""Standalone MP4 to MP3 converter using moviepy.
This script will be called by the Bilibili scraper via subprocess.
"""
import sys
import os

def convert_mp4_to_mp3(video_path, audio_path):
    """
    Convert MP4 video to MP3 audio.
    
    Args:
        video_path: Path to input MP4 file
        audio_path: Path to output MP3 file
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Import directly from moviepy (not moviepy.editor)
        from moviepy import VideoFileClip
        
        # Load video
        video = VideoFileClip(video_path)
        
        # Extract audio
        audio = video.audio
        
        # Write audio file as WAV format (better compatibility with Whisper)
        audio.write_audiofile(audio_path, codec='pcm_s16le', logger=None)
        
        # Clean up
        audio.close()
        video.close()
        
        return True
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        return False


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python convert_mp4_to_mp3.py <input_mp4> <output_mp3>", file=sys.stderr)
        sys.exit(1)
    
    video_path = sys.argv[1]
    audio_path = sys.argv[2]
    
    if not os.path.exists(video_path):
        print(f"Error: Video file not found: {video_path}", file=sys.stderr)
        sys.exit(1)
    
    success = convert_mp4_to_mp3(video_path, audio_path)
    sys.exit(0 if success else 1)

