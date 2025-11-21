"""
Test script for News Summary Service Workflow.

This script tests the complete news summary workflow from channel scraping
to article generation using a couple of test channel links.
"""
import sys
import json
import time
from pathlib import Path
from datetime import datetime, timedelta

print("Starting test script...", flush=True)

# Set up logging before importing loguru
import logging
logging.basicConfig(level=logging.INFO)

try:
    from loguru import logger
    print("✓ Loguru imported", flush=True)
except ImportError as e:
    print(f"✗ Failed to import loguru: {e}", flush=True)
    sys.exit(1)

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
print(f"✓ Added project root to path: {project_root}", flush=True)

try:
    # Add backend directory to path
    backend_dir = project_root / "backend"
    sys.path.insert(0, str(backend_dir))
    print(f"✓ Added backend to path: {backend_dir}", flush=True)
    
    print("Importing Config...", flush=True)
    from core.config import Config
    print("✓ Config imported", flush=True)
    
    print("Initializing Config...", flush=True)
    config = Config()
    print("✓ Config initialized", flush=True)
    
    print("Importing NewsSummaryWorkflowService...", flush=True)
    from app.services.news_summary_workflow_service import NewsSummaryWorkflowService
    print("✓ NewsSummaryWorkflowService imported", flush=True)
except ImportError as e:
    print(f"✗ Failed to import required modules: {e}", flush=True)
    import traceback
    traceback.print_exc()
    sys.exit(1)
except Exception as e:
    print(f"✗ Error during initialization: {e}", flush=True)
    import traceback
    traceback.print_exc()
    sys.exit(1)


def print_step(step_num: int, step_name: str, message: str = ""):
    """Print a formatted step message."""
    print(f"\n{'='*80}")
    print(f"Step {step_num}: {step_name}")
    print(f"{'='*80}")
    if message:
        print(message)


def print_result(result: dict, indent: int = 0):
    """Print a result dictionary in a formatted way."""
    prefix = "  " * indent
    for key, value in result.items():
        if isinstance(value, dict):
            print(f"{prefix}{key}:")
            print_result(value, indent + 1)
        elif isinstance(value, list):
            print(f"{prefix}{key}: [{len(value)} items]")
            if value and isinstance(value[0], dict):
                for i, item in enumerate(value[:3]):  # Show first 3 items
                    print(f"{prefix}  [{i}]:")
                    print_result(item, indent + 2)
                if len(value) > 3:
                    print(f"{prefix}  ... and {len(value) - 3} more items")
        else:
            print(f"{prefix}{key}: {value}")


# Test channel IDs for workflow testing
# Pick channels that are likely to have recent videos (news channels)
TEST_CHANNEL_IDS = [
    "UCBi2mrWuNuyYy4gbM6fU18Q",  # ABC News - major global news
    "UC16niRr50-MSBwiO3YDb3RA"   # BBC News - major global news
]


def test_news_summary_workflow():
    """Test the complete news summary workflow."""
    
    print("\n" + "="*80, flush=True)
    print("NEWS SUMMARY WORKFLOW TEST", flush=True)
    print("="*80, flush=True)
    
    # Initialize service
    print("Initializing NewsSummaryWorkflowService...", flush=True)
    try:
        service = NewsSummaryWorkflowService(config)
        print("✓ NewsSummaryWorkflowService initialized successfully", flush=True)
        logger.info("NewsSummaryWorkflowService initialized successfully")
    except Exception as e:
        print(f"✗ Failed to initialize service: {e}", flush=True)
        logger.error(f"Failed to initialize service: {e}", exc_info=True)
        import traceback
        traceback.print_exc()
        return False
    
    # Set up test parameters
    # Use a recent date range (last 14 days for better chance of finding videos)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=14)
    
    date_range = {
        "start_date": start_date.strftime('%Y-%m-%d'),
        "end_date": end_date.strftime('%Y-%m-%d')
    }
    
    print(f"\nTest Configuration:")
    print(f"  Date Range: {date_range['start_date']} to {date_range['end_date']}")
    print(f"  Test Channels ({len(TEST_CHANNEL_IDS)}):")
    for channel_id in TEST_CHANNEL_IDS:
        print(f"    - {channel_id}")
    
    # Step 1: Create Session
    print_step(1, "Creating Workflow Session")
    try:
        session_id = service.create_session(date_range)
        print(f"✓ Session created: {session_id}")
        print(f"  Session directory: data/news/sessions/{session_id}/")
    except Exception as e:
        logger.error(f"Failed to create session: {e}", exc_info=True)
        return False
    
    # Step 2: Run Workflow
    print_step(2, "Running Complete Workflow")
    print("This may take a while...")
    print("Note: Step 2 (Content Scraping + Phase 0) has a placeholder and may not work fully.")
    
    try:
        # Run workflow with limited channels for testing
        # Use the test channel IDs defined above
        options = {
            "channel_ids": TEST_CHANNEL_IDS  # Limit to 2 test channels for faster testing
        }
        
        print(f"\n  Running with {len(TEST_CHANNEL_IDS)} test channels...")
        
        start_time = time.time()
        result = service.run_workflow(
            session_id=session_id,
            date_range=date_range,
            options=options
        )
        elapsed_time = time.time() - start_time
        
        print(f"\n✓ Workflow completed in {elapsed_time:.2f} seconds")
        print(f"  Status: {result.get('status', 'unknown')}")
        
        # Print step results
        print("\nStep Results:")
        steps = result.get('steps', {})
        for step_name, step_result in steps.items():
            print(f"\n  {step_name}:")
            if isinstance(step_result, dict):
                status = step_result.get('status', 'unknown')
                print(f"    Status: {status}")
                if 'error' in step_result:
                    print(f"    Error: {step_result['error']}")
                if 'batch_id' in step_result:
                    print(f"    Batch ID: {step_result['batch_id']}")
                if 'outline_id' in step_result:
                    print(f"    Outline ID: {step_result['outline_id']}")
                if 'article_id' in step_result:
                    print(f"    Article ID: {step_result['article_id']}")
                if 'total_videos' in step_result:
                    print(f"    Total Videos: {step_result['total_videos']}")
                if 'channels_scraped' in step_result:
                    print(f"    Channels Scraped: {step_result['channels_scraped']}")
        
        # Print errors if any
        errors = result.get('errors', [])
        if errors:
            print(f"\n⚠ Errors ({len(errors)}):")
            for error in errors:
                print(f"  - {error.get('step', 'unknown')}: {error.get('error', 'unknown error')}")
        
    except Exception as e:
        logger.error(f"Failed to run workflow: {e}", exc_info=True)
        print(f"\n✗ Workflow failed: {str(e)}")
        return False
    
    # Step 3: Check Session Status
    print_step(3, "Checking Session Status")
    try:
        status = service.get_session_status(session_id)
        print(f"✓ Session status retrieved")
        print(f"  Status: {status.get('status', 'unknown')}")
        print(f"  Current Step: {status.get('current_step', 'none')}")
    except Exception as e:
        logger.error(f"Failed to get session status: {e}", exc_info=True)
        print(f"✗ Failed to get session status: {str(e)}")
    
    # Step 4: Load Session Metadata
    print_step(4, "Loading Session Metadata")
    try:
        metadata = service.load_session_metadata(session_id)
        print(f"✓ Session metadata loaded")
        print(f"  Created At: {metadata.get('created_at', 'unknown')}")
        print(f"  Status: {metadata.get('status', 'unknown')}")
        print(f"  Date Range: {metadata.get('date_range', {})}")
        
        # Print artifacts
        artifacts = metadata.get('artifacts', {})
        if artifacts:
            print(f"\n  Artifacts:")
            for key, path in artifacts.items():
                print(f"    {key}: {path}")
        
        # Print steps summary
        steps = metadata.get('steps', {})
        if steps:
            print(f"\n  Steps Summary:")
            for step_name, step_data in steps.items():
                step_status = step_data.get('status', 'unknown')
                completed_at = step_data.get('completed_at', 'not completed')
                print(f"    {step_name}: {step_status} ({completed_at})")
        
    except Exception as e:
        logger.error(f"Failed to load session metadata: {e}", exc_info=True)
        print(f"✗ Failed to load session metadata: {str(e)}")
    
    # Step 5: List Sessions
    print_step(5, "Listing All Sessions")
    try:
        sessions = service.list_sessions()
        print(f"✓ Found {len(sessions)} sessions")
        if sessions:
            print(f"\n  Recent Sessions:")
            for session in sessions[:5]:  # Show first 5
                print(f"    - {session.get('session_id', 'unknown')}")
                print(f"      Status: {session.get('status', 'unknown')}")
                print(f"      Created: {session.get('created_at', 'unknown')}")
    except Exception as e:
        logger.error(f"Failed to list sessions: {e}", exc_info=True)
        print(f"✗ Failed to list sessions: {str(e)}")
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"Session ID: {session_id}")
    print(f"Status: {result.get('status', 'unknown')}")
    print(f"Steps Completed: {len([s for s in result.get('steps', {}).values() if s.get('status') == 'completed'])}")
    print(f"Errors: {len(result.get('errors', []))}")
    
    if result.get('status') == 'completed':
        print("\n✓ Workflow completed successfully!")
        print(f"\nYou can find the results in: data/news/sessions/{session_id}/")
        return True
    else:
        print(f"\n⚠ Workflow completed with errors or warnings")
        print(f"Check the logs and session metadata for details")
        return False


def test_quick_workflow():
    """Quick test that only creates a session and checks it exists."""
    print("\n" + "="*80)
    print("QUICK NEWS SUMMARY WORKFLOW TEST")
    print("="*80)
    
    try:
        config = Config()
        service = NewsSummaryWorkflowService(config)
        
        # Create session
        date_range = {
            "start_date": (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d'),
            "end_date": datetime.now().strftime('%Y-%m-%d')
        }
        
        print(f"\nCreating test session with date range: {date_range}")
        session_id = service.create_session(date_range)
        print(f"✓ Session created: {session_id}")
        
        # Check session exists
        status = service.get_session_status(session_id)
        print(f"✓ Session status: {status.get('status')}")
        
        # Load metadata
        metadata = service.load_session_metadata(session_id)
        print(f"✓ Session metadata loaded")
        print(f"  Date Range: {metadata.get('date_range')}")
        print(f"  Status: {metadata.get('status')}")
        
        return True
        
    except Exception as e:
        logger.error(f"Quick test failed: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test News Summary Workflow")
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run quick test (only creates session, doesn't run full workflow)"
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Run full workflow test (may take a long time)"
    )
    
    args = parser.parse_args()
    
    if args.quick:
        success = test_quick_workflow()
    elif args.full:
        success = test_news_summary_workflow()
    else:
        # Default: run quick test
        print("Running quick test (use --full for complete workflow test)")
        success = test_quick_workflow()
        if success:
            print("\nQuick test passed! Run with --full to test the complete workflow.")
    
    sys.exit(0 if success else 1)

