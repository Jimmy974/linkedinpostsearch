import asyncio
from crawl4ai import AsyncWebCrawler
from crawl4ai.extraction_strategy import LLMExtractionStrategy, JsonCssExtractionStrategy
import json
import os
from bs4 import BeautifulSoup
from models.schemas import LinkedInPost
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def extract_post_content(url: str, post_meta: dict, debug_html: bool = False) -> str:
    """
    Extract the content of a LinkedIn post and format it as markdown
    """
    print(f"Extracting content from: {url}")
    
    # First get the raw HTML
    async with AsyncWebCrawler(verbose=True) as crawler:
        raw_result = await crawler.arun(
            url=url,
            word_count_threshold=1,
            bypass_cache=True,
            remove_overlay_elements=True
        )
        
        if debug_html:
            # Create debug directory if it doesn't exist
            debug_dir = "debug_html"
            os.makedirs(debug_dir, exist_ok=True)
            
            # Format HTML using BeautifulSoup
            soup = BeautifulSoup(raw_result.html, 'html.parser')
            formatted_html = soup.prettify()
            
            # Save raw and formatted HTML for debugging
            post_id = post_meta.get('id', 'unknown').replace('/', '_')
            
            # Save formatted HTML
            formatted_html_file = os.path.join(debug_dir, f"{post_id}_formatted.html")
            with open(formatted_html_file, 'w', encoding='utf-8') as f:
                f.write(formatted_html)
            print(f"Saved formatted HTML to {formatted_html_file}")
    
    # define schema for content extraction
    schema = {
        "name": "content",
        "baseSelector": "main",  # Start from main content area
        "fields": [
            {
                "name": "post_content",
                "selector": ".attributed-text-segment-list__content",
                "type": "text",
                "multiple": True  # Get all matching spans
            }
        ]
    }
    
    async with AsyncWebCrawler(verbose=True) as crawler:
        result = await crawler.arun(
            url=url,
            word_count_threshold=1,
            extraction_strategy=JsonCssExtractionStrategy(schema=schema),
            bypass_cache=True,
            remove_overlay_elements=True
        )
    
    try:
        # Extract content from the result
        extracted_data = json.loads(result.extracted_content)
        post_content = json.loads(result.extracted_content)[0]["post_content"]
        
        # Format as markdown
        markdown_content = []
        
        # Add title
        markdown_content.append(f"# {post_meta['title']}\n")
        
        # Add metadata
        if post_meta.get('author'):
            markdown_content.append(f"**Author:** {post_meta['author']}")
        if post_meta.get('date'):
            markdown_content.append(f"**Date:** {post_meta['date']}")
        markdown_content.append("")  # Empty line after metadata
        
        # Add main content
        if post_content:
            markdown_content.append(post_content)
        
        # Add hashtags
        if post_meta.get('tags'):
            markdown_content.append("\n**Tags:** " + " ".join(post_meta['tags']))
        
        return "\n".join(markdown_content)
        
    except Exception as e:
        print(f"Error processing extracted content: {str(e)}")
        print("Raw extracted content:", result.extracted_content)
        raise

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
            "llm_provider": "together_ai/meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo"
        },
        {
            "keywords": "n8n integration",
            "min_publish_date": None,
            "debug_html": True,
            "llm_provider": "together_ai/meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\nRunning test case {i}:")
        print(json.dumps(test_case, indent=2))
        
        try:
            # Search for posts
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
                    # Extract content
                    content = await extract_post_content(
                        post['url'],
                        post,
                        debug_html=test_case["debug_html"]
                    )
                    
                    # Save to markdown file
                    post_id = post.get('id', f'post_{j}').replace('/', '_')
                    filename = f"{post_id}.md"
                    with open(filename, 'w', encoding='utf-8') as f:
                        f.write(content)
                    print(f"Saved content to {filename}")
                    
                except Exception as e:
                    print(f"Error processing post {post.get('url')}: {str(e)}")
                    continue
                
        except Exception as e:
            print(f"Error in test case {i}: {str(e)}")
            continue

if __name__ == "__main__":
    asyncio.run(main()) 