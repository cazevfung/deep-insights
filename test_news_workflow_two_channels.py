"""
Test script for News Summary Workflow with two channel links.

This script tests the complete news summary workflow from channel scraping
to article generation using two test channel links.
"""
import sys
import json
import time
from pathlib import Path
from datetime import datetime, timedelta

print("=" * 80)
print("News Summary Workflow Test - Two Channels")
print("=" * 80)
print()

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Add backend directory to path
backend_dir = project_root / "backend"
sys.path.insert(0, str(backend_dir))

try:
    from loguru import logger
    from core.config import Config
    from app.services.news_summary_workflow_service import NewsSummaryWorkflowService
    print("✓ All modules imported successfully")
except ImportError as e:
    print(f"✗ Failed to import required modules: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Configure two test channels
# Using ABC News and BBC News for testing
TEST_CHANNELS = [
    {
        "name": "ABC News",
        "channelId": "UCBi2mrWuNuyYy4gbM6fU18Q",
        "link": "https://www.youtube.com/channel/UCBi2mrWuNuyYy4gbM6fU18Q",
        "id": "UCBi2mrWuNuyYy4gbM6fU18Q"
    },
    {
        "name": "BBC News",
        "channelId": "UC16niRr50-MSBwiO3YDb3RA",
        "link": "https://www.youtube.com/channel/UC16niRr50-MSBwiO3YDb3RA",
        "id": "UC16niRr50-MSBwiO3YDb3RA"
    }
]

def main():
    """Run the complete workflow test."""
    print("\n" + "=" * 80)
    print("Step 1: Initialize Services")
    print("=" * 80)
    
    try:
        config = Config()
        workflow_service = NewsSummaryWorkflowService(config)
        print("✓ Services initialized")
    except Exception as e:
        print(f"✗ Failed to initialize services: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Set date range (today only)
    today = datetime.now()
    date_range = {
        "start_date": today.strftime("%Y-%m-%d"),
        "end_date": today.strftime("%Y-%m-%d")
    }
    
    print(f"\nDate range: {date_range['start_date']} to {date_range['end_date']} (today only)")
    print(f"Testing with {len(TEST_CHANNELS)} channels:")
    for channel in TEST_CHANNELS:
        print(f"  - {channel['name']}: {channel['link']}")
    
    # Check if channels file exists and is readable
    print("\n" + "=" * 80)
    print("Step 1.5: Verify Channels File")
    print("=" * 80)
    try:
        from pathlib import Path
        from core.config import find_project_root
        project_root = find_project_root() if find_project_root else Path.cwd()
        channels_file = project_root / "data/news/channels"
        
        if not channels_file.exists():
            print(f"⚠ Channels file not found: {channels_file}")
            print("  The workflow will fail at channel loading step.")
        else:
            file_size = channels_file.stat().st_size
            print(f"✓ Channels file exists: {channels_file}")
            print(f"  File size: {file_size} bytes")
            
            if file_size == 0:
                print("  ⚠ WARNING: Channels file is empty!")
            else:
                # Try to read first few lines
                with open(channels_file, 'r', encoding='utf-8') as f:
                    first_line = f.readline()
                    print(f"  First line preview: {first_line[:100]}...")
    except Exception as e:
        print(f"⚠ Could not verify channels file: {e}")
    
    print("\n" + "=" * 80)
    print("Step 2: Create Workflow Session")
    print("=" * 80)
    
    try:
        session_id = workflow_service.create_session(date_range)
        print(f"✓ Session created: {session_id}")
    except Exception as e:
        print(f"✗ Failed to create session: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Update session metadata with channel IDs (using manual save since method doesn't exist)
    try:
        metadata = workflow_service.load_session_metadata(session_id)
        metadata['channel_ids'] = [ch['id'] for ch in TEST_CHANNELS]
        metadata['test_channels'] = TEST_CHANNELS
        
        # Manually save metadata
        from pathlib import Path
        session_dir = workflow_service.sessions_dir / session_id
        metadata_file = session_dir / workflow_service.session_metadata_file
        import json
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        print(f"✓ Session metadata updated with {len(TEST_CHANNELS)} channel IDs")
    except Exception as e:
        print(f"⚠ Warning: Failed to update session metadata: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 80)
    print("Step 3: Run Complete Workflow")
    print("=" * 80)
    print("This will:")
    print("  1. Open Playwright browser window (headless=False)")
    print("  2. Scrape video links from the 2 test channels")
    print("  3. Continue with content scraping, Phase 0, outline, and article generation")
    print()
    print("This may take a while...")
    print()
    
    # Options for workflow
    options = {
        "channel_ids": [ch['id'] for ch in TEST_CHANNELS],
        "max_videos_per_channel": 5,  # Limit to 5 videos per channel for testing
        "skip_phase0": False,
        "skip_outline": False,
        "skip_article": False
    }
    
    print(f"Workflow options:")
    print(f"  - Channel IDs: {options['channel_ids']}")
    print(f"  - Max videos per channel: {options['max_videos_per_channel']}")
    print(f"  - Date range: {date_range['start_date']} (today only)")
    print(f"  - Browser: Will open visible window (headless=False)")
    print()
    
    start_time = time.time()
    
    try:
        result = workflow_service.run_workflow(
            session_id=session_id,
            date_range=date_range,
            options=options
        )
        
        elapsed_time = time.time() - start_time
        
        print("\n" + "=" * 80)
        print("Step 4: Workflow Results")
        print("=" * 80)
        print(f"✓ Workflow completed in {elapsed_time:.2f} seconds")
        print(f"Session ID: {session_id}")
        print(f"Status: {result.get('status', 'unknown')}")
        
        steps = result.get('steps', {})
        print("\nWorkflow Steps:")
        for step_name, step_result in steps.items():
            if step_name == 'current_step':
                continue
            status = step_result.get('status', 'unknown')
            print(f"  - {step_name}: {status}")
            if step_result.get('error'):
                print(f"    Error: {step_result['error']}")
        
        # Check artifacts
        artifacts = result.get('artifacts', {})
        if artifacts:
            print("\nGenerated Artifacts:")
            for artifact_type, artifact_paths in artifacts.items():
                if isinstance(artifact_paths, list):
                    print(f"  - {artifact_type}: {len(artifact_paths)} files")
                    for path in artifact_paths[:3]:  # Show first 3
                        print(f"    • {path}")
                    if len(artifact_paths) > 3:
                        print(f"    ... and {len(artifact_paths) - 3} more")
                else:
                    print(f"  - {artifact_type}: {artifact_paths}")
        
        print("\n" + "=" * 80)
        print("Step 5: Verify Session Files")
        print("=" * 80)
        
        # Check session directory
        session_dir = workflow_service.sessions_dir / session_id
        if session_dir.exists():
            print(f"✓ Session directory exists: {session_dir}")
            
            # List subdirectories
            subdirs = [d for d in session_dir.iterdir() if d.is_dir()]
            if subdirs:
                print(f"  Subdirectories: {len(subdirs)}")
                for subdir in subdirs:
                    files = list(subdir.glob("*"))
                    print(f"    - {subdir.name}: {len(files)} files")
            
            # Check metadata file
            metadata_file = session_dir / workflow_service.session_metadata_file
            if metadata_file.exists():
                print(f"✓ Metadata file exists: {metadata_file}")
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    final_metadata = json.load(f)
                    print(f"  Status: {final_metadata.get('status', 'unknown')}")
                    print(f"  Current step: {final_metadata.get('current_step', 'none')}")
        else:
            print(f"✗ Session directory not found: {session_dir}")
        
        print("\n" + "=" * 80)
        print("Test Summary")
        print("=" * 80)
        print(f"Session ID: {session_id}")
        print(f"Total time: {elapsed_time:.2f} seconds")
        print(f"Status: {result.get('status', 'unknown')}")
        print(f"Session directory: {session_dir}")
        print("\n✓ Test completed!")
        
    except Exception as e:
        elapsed_time = time.time() - start_time
        print(f"\n✗ Workflow failed after {elapsed_time:.2f} seconds: {e}")
        import traceback
        traceback.print_exc()
        
        # Try to get session status
        try:
            status = workflow_service.get_session_status(session_id)
            print(f"\nSession status: {status.get('status', 'unknown')}")
            print(f"Current step: {status.get('current_step', 'none')}")
        except:
            pass

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠ Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

