"""
Channel scraper API routes.
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from pathlib import Path
from loguru import logger
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from app.services.channel_scraper_service import ChannelScraperService

router = APIRouter()

# Lazy initialization
_channel_scraper_service = None


def get_channel_scraper_service() -> ChannelScraperService:
    """Get or create ChannelScraperService instance."""
    global _channel_scraper_service
    if _channel_scraper_service is None:
        try:
            _channel_scraper_service = ChannelScraperService()
            logger.info("ChannelScraperService initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize ChannelScraperService: {e}", exc_info=True)
            raise
    return _channel_scraper_service


class ScrapeRequest(BaseModel):
    """Request model for scraping channels."""
    start_date: Optional[str] = Field(None, description="Start date in YYYY-MM-DD format")
    end_date: Optional[str] = Field(None, description="End date in YYYY-MM-DD format")
    channel_ids: Optional[List[str]] = Field(None, description="Optional list of channel IDs to filter")


class ScrapeResponse(BaseModel):
    """Response model for scrape request."""
    batch_id: str
    status: str
    timestamp: str


class BatchSummary(BaseModel):
    """Batch summary model."""
    batch_id: str
    timestamp: str
    date_range: Optional[dict]
    total_videos: int
    channels_scraped: int


@router.post("/scrape", response_model=ScrapeResponse)
async def scrape_channels(request: ScrapeRequest, background_tasks: BackgroundTasks):
    """
    Scrape video links from YouTube channels.
    
    Args:
        request: Scrape request with date range and optional channel filters
        background_tasks: FastAPI background tasks
        
    Returns:
        Batch ID and status
    """
    try:
        service = get_channel_scraper_service()
        
        # Parse dates
        start_date = None
        end_date = None
        
        if request.start_date:
            try:
                start_date = datetime.strptime(request.start_date, '%Y-%m-%d')
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid start_date format. Expected YYYY-MM-DD, got: {request.start_date}"
                )
        
        if request.end_date:
            try:
                end_date = datetime.strptime(request.end_date, '%Y-%m-%d')
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid end_date format. Expected YYYY-MM-DD, got: {request.end_date}"
                )
        
        # Validate date range
        if start_date and end_date and start_date > end_date:
            raise HTTPException(
                status_code=400,
                detail="start_date must be before or equal to end_date"
            )
        
        # Generate batch ID first so we can return it immediately
        batch_id = service.generate_batch_id()
        
        # Run scraping in background
        def run_scrape():
            try:
                result = service.scrape_channels(
                    start_date=start_date,
                    end_date=end_date,
                    channel_ids=request.channel_ids,
                    batch_id=batch_id  # Use the pre-generated batch_id
                )
                logger.info(f"Background scrape completed: batch_id={result.get('batch_id')}")
            except Exception as e:
                logger.error(f"Background scrape failed: {e}", exc_info=True)
        
        background_tasks.add_task(run_scrape)
        
        return ScrapeResponse(
            batch_id=batch_id,
            status="started",
            timestamp=datetime.now().isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting scrape: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/batches", response_model=dict)
async def list_batches():
    """
    List all batches.
    
    Returns:
        List of batch summaries
    """
    try:
        service = get_channel_scraper_service()
        batches = service.list_batches()
        
        return {
            "batches": batches
        }
    except Exception as e:
        logger.error(f"Error listing batches: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/batches/{batch_id}", response_model=dict)
async def get_batch(batch_id: str):
    """
    Get batch metadata.
    
    Args:
        batch_id: Batch ID
        
    Returns:
        Batch metadata
    """
    try:
        service = get_channel_scraper_service()
        metadata = service.get_batch_metadata(batch_id)
        
        if not metadata:
            raise HTTPException(status_code=404, detail=f"Batch {batch_id} not found")
        
        return metadata
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting batch {batch_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/batches/{batch_id}/links")
async def get_batch_links(batch_id: str):
    """
    Download batch links file.
    
    Args:
        batch_id: Batch ID
        
    Returns:
        Text file with video links
    """
    try:
        service = get_channel_scraper_service()
        
        # Get batch file path
        batch_file = service.batches_dir / f"{batch_id}.txt"
        
        if not batch_file.exists():
            raise HTTPException(status_code=404, detail=f"Batch file {batch_id} not found")
        
        return FileResponse(
            path=str(batch_file),
            filename=f"{batch_id}_links.txt",
            media_type="text/plain"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting batch links {batch_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

