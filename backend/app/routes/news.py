"""
News API routes.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List, Literal
from loguru import logger

try:
    from core.config import Config
    from app.services.news_outline_service import NewsOutlineService
    from app.services.news_article_service import NewsArticleService
    from app.services.news_summary_workflow_service import NewsSummaryWorkflowService
except ImportError as e:
    logger.warning(f"Unable to import required modules: {e}")
    Config = None  # type: ignore
    NewsOutlineService = None  # type: ignore
    NewsArticleService = None  # type: ignore
    NewsSummaryWorkflowService = None  # type: ignore

router = APIRouter()

# Initialize config and services (lazy initialization)
_config: Optional[Config] = None
_outline_service: Optional[NewsOutlineService] = None
_article_service: Optional[NewsArticleService] = None
_workflow_service: Optional[NewsSummaryWorkflowService] = None


def get_outline_service() -> NewsOutlineService:
    """Get or create news outline service."""
    global _config, _outline_service
    
    if NewsOutlineService is None:
        raise HTTPException(status_code=500, detail="NewsOutlineService unavailable")
    
    if _outline_service is None:
        if _config is None:
            if Config is None:
                raise HTTPException(status_code=500, detail="Config unavailable")
            _config = Config()
        _outline_service = NewsOutlineService(_config)
    
    return _outline_service


def get_article_service() -> NewsArticleService:
    """Get or create news article service."""
    global _config, _article_service
    
    if NewsArticleService is None:
        raise HTTPException(status_code=500, detail="NewsArticleService unavailable")
    
    if _article_service is None:
        if _config is None:
            if Config is None:
                raise HTTPException(status_code=500, detail="Config unavailable")
            _config = Config()
        _article_service = NewsArticleService(_config)
    
    return _article_service


def get_workflow_service() -> NewsSummaryWorkflowService:
    """Get or create news summary workflow service."""
    global _config, _workflow_service
    
    if NewsSummaryWorkflowService is None:
        raise HTTPException(status_code=500, detail="NewsSummaryWorkflowService unavailable")
    
    if _workflow_service is None:
        if _config is None:
            if Config is None:
                raise HTTPException(status_code=500, detail="Config unavailable")
            _config = Config()
        _workflow_service = NewsSummaryWorkflowService(_config)
    
    return _workflow_service


class GenerateOutlineRequest(BaseModel):
    """Request model for outline generation."""
    batch_id: str
    link_ids: Optional[List[str]] = None  # If None, process all links in batch


class GenerateOutlineResponse(BaseModel):
    """Response model for outline generation."""
    status: Literal["success", "error"]
    outline_id: Optional[str] = None
    outline: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


@router.post("/outlines/generate", response_model=GenerateOutlineResponse)
async def generate_outline(request: GenerateOutlineRequest):
    """Generate news article outline from Phase 0 summarized points."""
    try:
        service = get_outline_service()
        
        logger.info(f"Generating outline for batch: {request.batch_id}")
        
        # Generate outline
        outline = service.generate_outline_from_batch(
            batch_id=request.batch_id,
            link_ids=request.link_ids
        )
        
        # Save outline
        output_path = service.save_outline(outline)
        
        logger.info(f"Generated outline: {outline.get('outline_id')}")
        
        return GenerateOutlineResponse(
            status="success",
            outline_id=outline.get("outline_id"),
            outline=outline
        )
    
    except FileNotFoundError as e:
        logger.error(f"Batch or files not found: {e}")
        return GenerateOutlineResponse(
            status="error",
            error=f"Batch or files not found: {str(e)}"
        )
    
    except ValueError as e:
        logger.error(f"Invalid request or data: {e}")
        return GenerateOutlineResponse(
            status="error",
            error=f"Invalid request or data: {str(e)}"
        )
    
    except Exception as e:
        logger.error(f"Failed to generate outline: {e}", exc_info=True)
        return GenerateOutlineResponse(
            status="error",
            error=f"Failed to generate outline: {str(e)}"
        )


@router.get("/outlines/{outline_id}")
async def get_outline(outline_id: str):
    """Get a generated outline by ID."""
    try:
        service = get_outline_service()
        
        logger.info(f"Retrieving outline: {outline_id}")
        
        outline = service.load_outline(outline_id)
        
        return {
            "status": "success",
            "outline": outline
        }
    
    except FileNotFoundError as e:
        logger.error(f"Outline not found: {e}")
        raise HTTPException(status_code=404, detail=f"Outline not found: {outline_id}")
    
    except Exception as e:
        logger.error(f"Failed to retrieve outline: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve outline: {str(e)}")


@router.get("/outlines")
async def list_outlines(batch_id: Optional[str] = None):
    """List all generated outlines, optionally filtered by batch_id."""
    try:
        service = get_outline_service()
        
        logger.info(f"Listing outlines (batch_id={batch_id})")
        
        outlines = service.list_outlines(batch_id=batch_id)
        
        return {
            "status": "success",
            "count": len(outlines),
            "outlines": outlines
        }
    
    except Exception as e:
        logger.error(f"Failed to list outlines: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list outlines: {str(e)}")


# Article generation endpoints

class GenerateArticleRequest(BaseModel):
    """Request model for article generation."""
    outline_id: str


class GenerateArticleResponse(BaseModel):
    """Response model for article generation."""
    status: Literal["success", "error"]
    article_id: Optional[str] = None
    article: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


@router.post("/articles/generate", response_model=GenerateArticleResponse)
async def generate_article(request: GenerateArticleRequest):
    """Generate news article from outline."""
    try:
        service = get_article_service()
        
        logger.info(f"Generating article for outline: {request.outline_id}")
        
        # Generate article
        markdown_content, metadata = service.generate_article_from_outline(
            outline_id=request.outline_id
        )
        
        # Save article
        md_file, json_file = service.save_article(metadata, markdown_content)
        
        logger.info(f"Generated article: {metadata.get('article_id')}")
        
        return GenerateArticleResponse(
            status="success",
            article_id=metadata.get("article_id"),
            article=metadata
        )
    
    except FileNotFoundError as e:
        logger.error(f"Outline or files not found: {e}")
        return GenerateArticleResponse(
            status="error",
            error=f"Outline or files not found: {str(e)}"
        )
    
    except ValueError as e:
        logger.error(f"Invalid request or data: {e}")
        return GenerateArticleResponse(
            status="error",
            error=f"Invalid request or data: {str(e)}"
        )
    
    except Exception as e:
        logger.error(f"Failed to generate article: {e}", exc_info=True)
        return GenerateArticleResponse(
            status="error",
            error=f"Failed to generate article: {str(e)}"
        )


@router.get("/articles/{article_id}")
async def get_article(article_id: str):
    """Get article metadata by ID."""
    try:
        service = get_article_service()
        
        logger.info(f"Retrieving article: {article_id}")
        
        article = service.load_article(article_id)
        
        return {
            "status": "success",
            "article": article
        }
    
    except FileNotFoundError as e:
        logger.error(f"Article not found: {e}")
        raise HTTPException(status_code=404, detail=f"Article not found: {article_id}")
    
    except Exception as e:
        logger.error(f"Failed to retrieve article: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve article: {str(e)}")


@router.get("/articles/{article_id}/markdown")
async def get_article_markdown(article_id: str):
    """Get article markdown content by ID."""
    try:
        service = get_article_service()
        
        logger.info(f"Retrieving article markdown: {article_id}")
        
        markdown_content = service.get_article_markdown(article_id)
        
        return {
            "status": "success",
            "article_id": article_id,
            "markdown": markdown_content
        }
    
    except FileNotFoundError as e:
        logger.error(f"Article markdown not found: {e}")
        raise HTTPException(status_code=404, detail=f"Article markdown not found: {article_id}")
    
    except Exception as e:
        logger.error(f"Failed to retrieve article markdown: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve article markdown: {str(e)}")


@router.get("/articles")
async def list_articles(outline_id: Optional[str] = None, batch_id: Optional[str] = None):
    """List all generated articles, optionally filtered by outline_id or batch_id."""
    try:
        service = get_article_service()
        
        logger.info(f"Listing articles (outline_id={outline_id}, batch_id={batch_id})")
        
        articles = service.list_articles(outline_id=outline_id, batch_id=batch_id)
        
        return {
            "status": "success",
            "count": len(articles),
            "articles": articles
        }
    
    except Exception as e:
        logger.error(f"Failed to list articles: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list articles: {str(e)}")


# Workflow endpoints

class CreateWorkflowSessionRequest(BaseModel):
    """Request model for creating workflow session."""
    start_date: str  # Format: YYYY-MM-DD
    end_date: str    # Format: YYYY-MM-DD
    channel_ids: Optional[List[str]] = None  # Optional: filter specific channels
    options: Optional[Dict[str, Any]] = None  # Workflow options


class CreateWorkflowSessionResponse(BaseModel):
    """Response model for creating workflow session."""
    status: Literal["success", "error"]
    session_id: Optional[str] = None
    error: Optional[str] = None


class RunWorkflowRequest(BaseModel):
    """Request model for running workflow."""
    session_id: str
    options: Optional[Dict[str, Any]] = None  # Workflow options


class RunWorkflowResponse(BaseModel):
    """Response model for running workflow."""
    status: Literal["success", "error", "in_progress"]
    session_id: str
    current_step: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class SessionStatusResponse(BaseModel):
    """Response model for session status."""
    session_id: str
    status: str
    current_step: Optional[str] = None
    metadata: Dict[str, Any]


@router.post("/workflow/sessions", response_model=CreateWorkflowSessionResponse)
async def create_workflow_session(request: CreateWorkflowSessionRequest):
    """Create a new workflow session."""
    try:
        service = get_workflow_service()
        
        logger.info(f"Creating workflow session: {request.start_date} to {request.end_date}")
        
        # Validate date format
        try:
            datetime.strptime(request.start_date, '%Y-%m-%d')
            datetime.strptime(request.end_date, '%Y-%m-%d')
        except ValueError:
            return CreateWorkflowSessionResponse(
                status="error",
                error="Invalid date format. Use YYYY-MM-DD format."
            )
        
        # Create session
        date_range = {
            "start_date": request.start_date,
            "end_date": request.end_date
        }
        
        options = request.options or {}
        if request.channel_ids:
            options['channel_ids'] = request.channel_ids
        
        session_id = service.create_session(date_range)
        
        logger.info(f"Created workflow session: {session_id}")
        
        return CreateWorkflowSessionResponse(
            status="success",
            session_id=session_id
        )
    
    except Exception as e:
        logger.error(f"Failed to create workflow session: {e}", exc_info=True)
        return CreateWorkflowSessionResponse(
            status="error",
            error=f"Failed to create workflow session: {str(e)}"
        )


@router.post("/workflow/sessions/{session_id}/run", response_model=RunWorkflowResponse)
async def run_workflow(session_id: str, request: Optional[RunWorkflowRequest] = None):
    """Run the complete workflow for a session."""
    try:
        service = get_workflow_service()
        
        # Get session metadata to get date_range
        try:
            metadata = service.load_session_metadata(session_id)
            date_range = metadata.get('date_range', {})
        except FileNotFoundError:
            return RunWorkflowResponse(
                status="error",
                session_id=session_id,
                error=f"Session not found: {session_id}"
            )
        
        # Use request options if provided, otherwise use metadata
        options = request.options if request else None
        
        logger.info(f"Running workflow for session: {session_id}")
        
        # Run workflow (this is synchronous and may take a long time)
        # In production, this should be run as a background task
        result = service.run_workflow(
            session_id=session_id,
            date_range=date_range,
            options=options
        )
        
        return RunWorkflowResponse(
            status=result.get("status", "in_progress"),
            session_id=session_id,
            current_step=result.get("steps", {}).get("current_step"),
            result=result
        )
    
    except ValueError as e:
        logger.error(f"Invalid request: {e}")
        return RunWorkflowResponse(
            status="error",
            session_id=session_id,
            error=f"Invalid request: {str(e)}"
        )
    
    except Exception as e:
        logger.error(f"Failed to run workflow: {e}", exc_info=True)
        return RunWorkflowResponse(
            status="error",
            session_id=session_id,
            error=f"Failed to run workflow: {str(e)}"
        )


@router.get("/workflow/sessions/{session_id}/status", response_model=SessionStatusResponse)
async def get_workflow_session_status(session_id: str):
    """Get current status of a workflow session."""
    try:
        service = get_workflow_service()
        
        logger.info(f"Retrieving workflow session status: {session_id}")
        
        status = service.get_session_status(session_id)
        
        return SessionStatusResponse(
            session_id=session_id,
            status=status.get("status", "unknown"),
            current_step=status.get("current_step"),
            metadata=status.get("metadata", {})
        )
    
    except ValueError as e:
        logger.error(f"Session not found: {e}")
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")
    
    except Exception as e:
        logger.error(f"Failed to retrieve session status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve session status: {str(e)}")


@router.get("/workflow/sessions")
async def list_workflow_sessions(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    status: Optional[str] = None
):
    """List all workflow sessions, optionally filtered by date range or status."""
    try:
        service = get_workflow_service()
        
        logger.info(f"Listing workflow sessions (start_date={start_date}, end_date={end_date}, status={status})")
        
        sessions = service.list_sessions(
            start_date=start_date,
            end_date=end_date,
            status=status
        )
        
        return {
            "status": "success",
            "count": len(sessions),
            "sessions": sessions
        }
    
    except Exception as e:
        logger.error(f"Failed to list workflow sessions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list workflow sessions: {str(e)}")


@router.get("/workflow/sessions/{session_id}/metadata")
async def get_workflow_session_metadata(session_id: str):
    """Get full session metadata."""
    try:
        service = get_workflow_service()
        
        logger.info(f"Retrieving workflow session metadata: {session_id}")
        
        metadata = service.load_session_metadata(session_id)
        
        return {
            "status": "success",
            "session_id": session_id,
            "metadata": metadata
        }
    
    except FileNotFoundError as e:
        logger.error(f"Session metadata not found: {e}")
        raise HTTPException(status_code=404, detail=f"Session metadata not found: {session_id}")
    
    except Exception as e:
        logger.error(f"Failed to retrieve session metadata: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve session metadata: {str(e)}")


@router.get("/workflow/sessions/{session_id}/artifacts")
async def get_workflow_session_artifacts(session_id: str):
    """Get all artifacts for a session (links to files)."""
    try:
        service = get_workflow_service()
        
        logger.info(f"Retrieving workflow session artifacts: {session_id}")
        
        metadata = service.load_session_metadata(session_id)
        artifacts = metadata.get("artifacts", {})
        
        return {
            "status": "success",
            "session_id": session_id,
            "artifacts": artifacts
        }
    
    except FileNotFoundError as e:
        logger.error(f"Session metadata not found: {e}")
        raise HTTPException(status_code=404, detail=f"Session metadata not found: {session_id}")
    
    except Exception as e:
        logger.error(f"Failed to retrieve session artifacts: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve session artifacts: {str(e)}")

