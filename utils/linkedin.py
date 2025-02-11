import asyncio
from crawl4ai import AsyncWebCrawler
from crawl4ai.extraction_strategy import LLMExtractionStrategy, JsonCssExtractionStrategy
import json
import os
from bs4 import BeautifulSoup
from models.schemas import LinkedInPost
from dotenv import load_dotenv
from duckduckgo_search import DDGS
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from exa_py import Exa
import sys
from functools import partial

# Load environment variables
load_dotenv()

# Initialize Exa client
if not os.getenv("EXA_API_KEY"):
    print("Warning: EXA_API_KEY not found in environment variables. Exa search will not be available.")
    exa_client = None
else:
    exa_client = Exa(api_key=os.getenv("EXA_API_KEY"))

@dataclass
class LinkedInSearchResult:
    title: str
    url: str
    description: str
    date: Optional[datetime] = None
    author: Optional[str] = None
    tags: List[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []

def parse_duckduckgo_date(date_str: str) -> Optional[datetime]:
    """Parse DuckDuckGo date string into datetime object"""
    try:
        # Try parsing ISO format
        return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
    except (ValueError, AttributeError):
        try:
            # Try parsing relative date (e.g., "1 day ago", "2 weeks ago")
            if 'day' in date_str:
                days = int(date_str.split()[0])
                return datetime.now() - timedelta(days=days)
            elif 'week' in date_str:
                weeks = int(date_str.split()[0])
                return datetime.now() - timedelta(weeks=weeks)
            elif 'month' in date_str:
                months = int(date_str.split()[0])
                return datetime.now() - timedelta(days=months * 30)
        except:
            pass
    return None

async def extract_post_content(url: str, post_meta: dict, debug_html: bool = False) -> str:
    """
    Extract the content of a LinkedIn post and format it as markdown
    """
    print(f"Extracting content from: {url}")
    
    # Set recursion limit for this function
    original_limit = sys.getrecursionlimit()
    sys.setrecursionlimit(200000)  # Increase limit temporarily
    
    try:
        raw_result = None
        
        # Only get raw HTML if debug_html is True
        if debug_html:
            try:
                async with AsyncWebCrawler(
                    verbose=True,
                    max_recursion_depth=50,
                    timeout=30
                ) as crawler:
                    raw_result = await crawler.arun(
                        url=url,
                        word_count_threshold=1,
                        bypass_cache=True,
                        remove_overlay_elements=True,
                        max_retries=2
                    )
                    
                    if raw_result and hasattr(raw_result, 'html'):
                        try:
                            # Create debug directory if it doesn't exist
                            debug_dir = "debug_html"
                            os.makedirs(debug_dir, exist_ok=True)
                            
                            # Save raw HTML directly without processing
                            post_id = str(post_meta.get('id', 'unknown')).replace('/', '_')[:50]
                            debug_file = os.path.join(debug_dir, f"{post_id}_raw.html")
                            with open(debug_file, 'w', encoding='utf-8') as f:
                                f.write(raw_result.html[:20000])  # Reduced size limit
                        except Exception as e:
                            print(f"Debug file error: {e}")
            except Exception as e:
                print(f"Failed to get raw HTML for debug: {e}")
        
        # Simple schema for content extraction
        schema = {
            "name": "content",
            "baseSelector": "main",
            "fields": [
                {
                    "name": "post_content",
                    "selector": ".attributed-text-segment-list__content",
                    "type": "text",
                    "multiple": False
                }
            ]
        }
        
        # Extract content with safety limits
        async with AsyncWebCrawler(
            verbose=True,
            max_recursion_depth=50,
            timeout=30
        ) as crawler:
            try:
                result = await crawler.arun(
                    url=url,
                    word_count_threshold=1,
                    extraction_strategy=JsonCssExtractionStrategy(
                        schema=schema,
                        max_depth=3
                    ),
                    bypass_cache=True,
                    remove_overlay_elements=True,
                    max_retries=2
                )
            except Exception as e:
                print(f"Content extraction failed: {e}")
                return "Failed to extract content"
        
        # Early return if no content
        if not result or not hasattr(result, 'extracted_content') or not result.extracted_content:
            return "No content extracted"
            
        # Limit content size before processing
        content_str = result.extracted_content[:50000]
        
        try:
            # Parse JSON with basic structure
            extracted_data = json.loads(content_str)
            
            # Handle both list and dict responses
            if isinstance(extracted_data, list):
                content_item = extracted_data[0] if extracted_data else {}
            elif isinstance(extracted_data, dict):
                content_item = extracted_data
            else:
                return "Invalid content structure"
            
            # Get post content safely
            post_content = str(content_item.get("post_content", ""))
            if not post_content:
                return "No content found"
            
            # Limit final content size
            if len(post_content) > 20000:
                post_content = post_content[:20000] + "... (truncated)"
            
            return post_content
            
        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {e}")
            return "Failed to parse content"
        except Exception as e:
            print(f"Content processing error: {e}")
            return f"Error processing content: {str(e)}"
            
    except Exception as e:
        print(f"Extraction error: {e}")
        return f"Failed to extract content: {str(e)}"
    finally:
        # Restore original recursion limit
        sys.setrecursionlimit(original_limit)

async def search_linkedin_posts(
    keywords: str, 
    min_publish_date: str | None = None,
    max_publish_date: str | None = None,
    llm_provider: str = "together_ai/meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo"
):
    """
    Search for LinkedIn posts by keywords
    
    Args:
        keywords (str): Keywords to search for in posts
        min_publish_date (str | None): Minimum publish date in YYYY-MM-DD format
        max_publish_date (str | None): Maximum publish date in YYYY-MM-DD format
        llm_provider (str): LLM provider for content extraction
    """
    print(f"Searching LinkedIn posts with keywords: {keywords}")
    print(f"Using LLM provider: {llm_provider}")
    
    # Format keywords for URL
    formatted_keywords = '+'.join(keywords.strip().split())
    search_url = f"https://www.google.com/search?q=site:linkedin.com/posts+{formatted_keywords}"
    print(search_url)
    
    # Add date range parameters if specified
    if min_publish_date or max_publish_date:
        search_url += "&tbs=cdr:1"
        
        if min_publish_date:
            try:
                year, month, day = min_publish_date.split('-')
                formatted_min_date = f"{month}/{day}/{year}"
                search_url += f",cd_min:{formatted_min_date}"
                print(f"Filtering from date: {formatted_min_date}")
            except ValueError:
                print("Warning: Invalid min_publish_date format. Expected YYYY-MM-DD")
                
        if max_publish_date:
            try:
                year, month, day = max_publish_date.split('-')
                formatted_max_date = f"{month}/{day}/{year}"
                search_url += f",cd_max:{formatted_max_date}"
                print(f"Filtering to date: {formatted_max_date}")
            except ValueError:
                print("Warning: Invalid max_publish_date format. Expected YYYY-MM-DD")
    
    async with AsyncWebCrawler(verbose=True) as crawler:
        result = await crawler.arun(
            url=search_url,
            word_count_threshold=1,
            extraction_strategy=LLMExtractionStrategy(
                provider=llm_provider,
                api_token=os.getenv("TOGETHER_API_KEY"),
                schema=LinkedInPost.model_json_schema(),
                extraction_type="schema",
                instruction="""From the crawled content, extract up to a maximum of 15 LinkedIn post details in JSON format. 
                Each post should include:
                - title: The post title or headline
                - url: The LinkedIn post URL
                - id: The suffix after the last slash in the URL
                - description: Brief description or preview of the post
                - date: The publication date
                - author: The post author's name
                - tags: List of hashtags mentioned in the post
                
                Important: Return no more than 15 posts, prioritizing the most relevant ones."""
            ),
            bypass_cache=True
        )
    
    response = json.loads(result.extracted_content)
    print(response)
    print(f"Found {len(response)} posts")
    
    # Filter for valid LinkedIn post URLs and publication date
    valid_posts = []
    for post in response:
        if "linkedin.com/posts" not in str(post.get("url", "")).lower():
            continue
            
        if min_publish_date and post.get("date"):
            try:
                post_date = post["date"].split()[0]  # Get date part if time is included
                if post_date < min_publish_date:
                    continue
            except (ValueError, IndexError):
                pass
                
        if max_publish_date and post.get("date"):
            try:
                post_date = post["date"].split()[0]  # Get date part if time is included
                if post_date > max_publish_date:
                    continue
            except (ValueError, IndexError):
                pass
                
        valid_posts.append(post)
    
    return valid_posts

async def search_linkedin_posts_duckduckgo(
    keywords: str,
    min_publish_date: Optional[str] = None,
    max_publish_date: Optional[str] = None,
    max_results: int = 15
) -> List[LinkedInSearchResult]:
    """
    Search for LinkedIn posts by keywords using DuckDuckGo API
    
    Args:
        keywords (str): Keywords to search for in posts
        min_publish_date (str, optional): Minimum publish date in YYYY-MM-DD format
        max_publish_date (str, optional): Maximum publish date in YYYY-MM-DD format
        max_results (int): Maximum number of results to return (default: 15)
        
    Returns:
        List[LinkedInSearchResult]: List of found LinkedIn posts
    """
    print(f"Searching LinkedIn posts with DuckDuckGo using keywords: {keywords}")
    
    # Convert string dates to datetime if provided
    min_date = None
    max_date = None
    try:
        if min_publish_date:
            min_date = datetime.strptime(min_publish_date, "%Y-%m-%d")
        if max_publish_date:
            max_date = datetime.strptime(max_publish_date, "%Y-%m-%d")
    except ValueError as e:
        print(f"Error parsing date: {str(e)}")
        print("Date should be in YYYY-MM-DD format")
        return []
    
    # Determine time limit based on min_date
    timelimit = "y"  # default to 1 year
    if min_date:
        days_ago = (datetime.now() - min_date).days
        if days_ago <= 1:
            timelimit = "d"
        elif days_ago <= 7:
            timelimit = "w"
        elif days_ago <= 30:
            timelimit = "m"
    
    # Format search query
    search_query = f"site:linkedin.com/posts {keywords}"
    print(f"Search query: {search_query}")
    
    # Initialize DuckDuckGo search
    search_results = []
    try:
        with DDGS() as ddgs:
            results = ddgs.text(
                search_query,
                max_results=15,  # Get more results to account for filtering
                timelimit=timelimit
            )
            print(results)
            # Process results
            for r in results:
                if not "linkedin.com/posts" in r.get("link", "").lower():
                    continue
                    
                # Parse date
                post_date = parse_duckduckgo_date(r.get("datetime", ""))
                
                # Apply date filters
                if min_date and (not post_date or post_date < min_date):
                    continue
                if max_date and (not post_date or post_date > max_date):
                    continue
                
                # Extract author from title if possible
                title = r.get("title", "")
                author = ""
                if " | " in title:
                    author = title.split(" | ")[0].strip()
                
                # Create search result object
                result = LinkedInSearchResult(
                    title=title,
                    url=r.get("link", ""),
                    description=r.get("body", ""),
                    date=post_date,
                    author=author,
                    tags=[]  # Tags would need content parsing to extract
                )
                search_results.append(result)
                
                if len(search_results) >= max_results:
                    break
                    
    except Exception as e:
        print(f"Error during DuckDuckGo search: {str(e)}")
        return []
    
    print(f"Found {len(search_results)} valid posts")
    return search_results

async def search_linkedin_posts_exa(
    keywords: str,
    min_publish_date: Optional[str] = None,
    max_publish_date: Optional[str] = None,
    max_results: int = 15
) -> List[LinkedInSearchResult]:
    """
    Search for LinkedIn posts by keywords using Exa search API
    
    Args:
        keywords (str): Keywords to search for in posts
        min_publish_date (str, optional): Minimum publish date in YYYY-MM-DD format
        max_publish_date (str, optional): Maximum publish date in YYYY-MM-DD format
        max_results (int): Maximum number of results to return (default: 15)
        
    Returns:
        List[LinkedInSearchResult]: List of found LinkedIn posts
    """
    if not exa_client:
        print("Error: Exa client not initialized. Please set EXA_API_KEY environment variable.")
        return []
        
    print(f"Searching LinkedIn posts with Exa using keywords: {keywords}")
    
    
    # Prepare search parameters
    search_params = {
        "query": keywords,
        "num_results": max_results * 2,
        "include_domains": ["linkedin.com"],
        "exclude_domains": [],
        # "text": True,
        # "use_autoprompt": True,
        # "category": "linkedin posts"  # Added to focus on LinkedIn content
    }
    
    # Add date filters if provided
    if min_publish_date:
        search_params["start_published_date"] = min_publish_date
    if max_publish_date:
        search_params["end_published_date"] = max_publish_date
    
    search_results = []
    try:
        # Perform the search
        results = exa_client.search(**search_params)
        # print(results)
        
        # Process results
        for result in results.results:

            # Skip if not a LinkedIn post
            if not "linkedin.com/posts" in result.url.lower():
                continue
            
            # Parse the date from the result
            try:
                post_date = datetime.fromisoformat(result.published_date.replace('Z', '+00:00')) if result.published_date else None
            except (TypeError, ValueError):
                post_date = None
            
            
            # Extract author from title if possible
            title = result.title or ""
            author = ""
            if " | " in title:
                author = title.split(" | ")[0].strip()
            
            # Create search result object
            search_result = LinkedInSearchResult(
                title=title,
                url=result.url,
                description=result.text or "",
                date=post_date,
                author=author,
                tags=[]  # Tags would need content parsing to extract
            )
            search_results.append(search_result)
            
            if len(search_results) >= max_results:
                break
                
    except Exception as e:
        print(f"Error during Exa search: {str(e)}")
        return []
    
    print(f"Found {len(search_results)} valid posts")
    return search_results

async def main():
    """
    Main entry point for testing LinkedIn scraping functionality
    """
    # Test parameters
    test_cases = [
        {
            "keywords": "n8n automation workflow",
            "min_publish_date": "2024-01-01",
            "debug_html": True,
            "llm_provider": "together_ai/meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
            "use_duckduckgo": False,
            "use_exa": False
        },
        {
            "keywords": "n8n integration",
            "min_publish_date": None,
            "debug_html": True,
            "llm_provider": "together_ai/meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo",
            "use_duckduckgo": False,
            "use_exa": False
        },
        {
            "keywords": "n8n workflow automation",
            "min_publish_date": "2024-01-01",
            "debug_html": True,
            "use_duckduckgo": True,
            "use_exa": False
        },
        {
            "keywords": "n8n automation tips",
            "min_publish_date": "2024-01-01",
            "debug_html": True,
            "use_duckduckgo": False,
            "use_exa": True
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\nRunning test case {i}:")
        print(json.dumps(test_case, indent=2))
        
        try:
            # Search for posts using the specified method
            if test_case.get("use_exa", False):
                if not exa_client:
                    print("Skipping Exa search test case - EXA_API_KEY not set")
                    continue
                posts = await search_linkedin_posts_exa(
                    keywords=test_case["keywords"],
                    min_publish_date=test_case["min_publish_date"]
                )
            elif test_case.get("use_duckduckgo", False):
                posts = await search_linkedin_posts_duckduckgo(
                    keywords=test_case["keywords"],
                    min_publish_date=test_case["min_publish_date"]
                )
            else:
                posts = await search_linkedin_posts(
                    keywords=test_case["keywords"],
                    min_publish_date=test_case["min_publish_date"],
                    llm_provider=test_case["llm_provider"]
                )
            
            print(f"\nFound {len(posts)} posts")
            
            # Process each post
            for j, post in enumerate(posts, 1):
                print(f"\nProcessing post {j}:")
                try:
                    # Convert LinkedInSearchResult to dict if needed
                    post_dict = post if isinstance(post, dict) else {
                        "url": post.url,
                        "title": post.title,
                        "description": post.description,
                        "date": post.date.strftime("%Y-%m-%d") if post.date else "",
                        "author": post.author or "",
                        "id": post.url.split("/")[-1],
                        "tags": post.tags
                    }
                    
                    # Extract content
                    content = await extract_post_content(
                        post_dict["url"],
                        post_dict,
                        debug_html=test_case["debug_html"]
                    )
                    
                    # Save to markdown file
                    post_id = post_dict.get("id", f"post_{j}").replace("/", "_")
                    filename = f"{post_id}.md"
                    with open(filename, "w", encoding="utf-8") as f:
                        f.write(content)
                    print(f"Saved content to {filename}")
                    
                except Exception as e:
                    print(f"Error processing post {post_dict.get('url')}: {str(e)}")
                    continue
                
        except Exception as e:
            print(f"Error in test case {i}: {str(e)}")
            continue

if __name__ == "__main__":
    asyncio.run(main()) 