from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.encoders import jsonable_encoder
import os
from models.schemas import SearchRequest, SearchResponse
from utils.linkedin import search_linkedin_posts, extract_post_content, search_linkedin_posts_duckduckgo, search_linkedin_posts_exa

router = APIRouter()

@router.post("/search", response_model=SearchResponse)
async def search_linkedin_posts_endpoint(request: SearchRequest) -> JSONResponse:
    """
    Search LinkedIn posts with the given keywords and parameters
    """
    try:
        posts = await search_linkedin_posts_exa(
            keywords=request.keywords,
            min_publish_date=request.min_publish_date,
            max_publish_date=request.max_publish_date
        )
        
        # Process each post
        post_responses = []
        for post in posts:
            try:
                # Extract content with simplified data structure
                content = await extract_post_content(post.url, {
                    "url": str(post.url),
                    "title": str(post.title),
                    "description": str(post.description),
                    "date": post.date.isoformat() if post.date else "",
                    "author": str(post.author or ""),
                    "tags": [str(tag) for tag in (post.tags or [])]
                }, debug_html=request.debug_html)
                
                # Get debug files if enabled
                debug_files = None
                if request.debug_html:
                    post_id = post.url.split("/")[-1].replace('/', '_')
                    debug_dir = "debug_html"
                    if os.path.exists(debug_dir):
                        debug_files = [f for f in os.listdir(debug_dir) if f.startswith(post_id)]
                
                # Create a simplified post response dictionary
                post_response = {
                    "title": str(post.title),
                    "url": str(post.url),
                    "id": str(post.url.split("/")[-1]),
                    "author": str(post.author),
                    "date": post.date.isoformat() if post.date else "",
                    "content": str(content),
                    "tags": [str(tag) for tag in (post.tags or [])],
                    "debug_files": debug_files
                }
                post_responses.append(post_response)
                
            except Exception as e:
                print(f"Error processing post {post.url}: {str(e)}")
                continue
        
        response_data = {
            "posts": post_responses,
            "total_posts": len(post_responses),
            "search_metadata": {
                "keywords": str(request.keywords),
                "min_publish_date": str(request.min_publish_date),
                "max_publish_date": str(request.max_publish_date),
                "llm_provider": str(request.llm_provider)
            }
        }
        
        # Use JSONResponse with jsonable_encoder to handle serialization
        return JSONResponse(content=jsonable_encoder(response_data))
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing request: {str(e)}"
        )

@router.get("/debug/{filename}")
async def get_debug_file(filename: str):
    """
    Serve debug files directly
    """
    debug_dir = "debug_html"
    file_path = os.path.join(debug_dir, filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=404,
            detail=f"Debug file {filename} not found"
        )
    
    # Determine content type based on file extension
    content_type = "text/plain"
    if filename.endswith(".html"):
        content_type = "text/html"
    elif filename.endswith(".json"):
        content_type = "application/json"
    
    return FileResponse(
        file_path,
        media_type=content_type,
        filename=filename
    ) 