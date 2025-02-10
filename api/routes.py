from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
import os
from models.schemas import SearchRequest, SearchResponse
from utils.linkedin import search_linkedin_posts, extract_post_content, search_linkedin_posts_duckduckgo, search_linkedin_posts_exa

router = APIRouter()

@router.post("/search", response_model=SearchResponse)
async def search_linkedin_posts_endpoint(request: SearchRequest) -> SearchResponse:
    """
    Search LinkedIn posts with the given keywords and parameters
    """
    try:
        # Get posts from LinkedIn
        # posts = await search_linkedin_posts(
        #     keywords=request.keywords,
        #     min_publish_date=request.min_publish_date,
        #     max_publish_date=request.max_publish_date,
        #     llm_provider=request.llm_provider
        # )
        # # Get posts from LinkedIn
        # posts = await search_linkedin_posts_duckduckgo(
        #     keywords=request.keywords,
        #     min_publish_date=request.min_publish_date,
        #     max_publish_date=request.max_publish_date
        # )        
        posts = await search_linkedin_posts_exa(
            keywords=request.keywords,
            min_publish_date=request.min_publish_date,
            max_publish_date=request.max_publish_date
        )
        # Process each post
        post_responses = []
        for post in posts:
            try:
                # Extract content
                content = await extract_post_content(post.url, {
                    "url": post.url,
                    "title": post.title,
                    "description": post.description,
                    "date": post.date.isoformat() if post.date else "",
                    "author": post.author or "",
                    "tags": post.tags or []
                }, debug_html=request.debug_html)
                
                # Get debug files if enabled
                debug_files = None
                if request.debug_html:
                    post_id = post.url.split("/")[-1].replace('/', '_')
                    debug_dir = "debug_html"
                    if os.path.exists(debug_dir):
                        files = [
                            f for f in os.listdir(debug_dir)
                            if f.startswith(post_id)
                        ]
                        if files:
                            debug_files = files
                
                post_response = {
                    "title": post.title,
                    "url": post.url,
                    "id": post.url.split("/")[-1],  # Extract ID from URL
                    "author": post.author,
                    "date": post.date.isoformat() if post.date else "",
                    "content": content,
                    "tags": post.tags,
                    "debug_files": debug_files
                }
                post_responses.append(post_response)
                
            except Exception as e:
                print(f"Error processing post {post.url}: {str(e)}")
                continue
        
        return SearchResponse(
            posts=post_responses,
            total_posts=len(post_responses),
            search_metadata={
                "keywords": request.keywords,
                "min_publish_date": request.min_publish_date,
                "max_publish_date": request.max_publish_date,
                "llm_provider": request.llm_provider
            }
        )
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