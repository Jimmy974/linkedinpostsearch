# LinkedIn Post Search Tool

A tool for searching and extracting content from LinkedIn posts using multiple search providers.

## Features

- Multiple search providers:
  - Google Search with LLM extraction
  - DuckDuckGo Search
  - Exa Search (semantic search)
- Date range filtering
- Content extraction
- Markdown export
- Configurable result limits

## Installation

1. Clone the repository
2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Environment Variables

Create a `.env` file with the following variables:

```env
# Required for LLM extraction (Google search)
TOGETHER_API_KEY=your_together_api_key

# Optional: Required only if using Exa search
EXA_API_KEY=your_exa_api_key
```

## Usage

You can use any of the three search providers to find LinkedIn posts:

```python
from n8nlinkedInPost.utils.linkedin import (
    search_linkedin_posts,
    search_linkedin_posts_duckduckgo,
    search_linkedin_posts_exa
)

# Using Google Search with LLM extraction
posts = await search_linkedin_posts(
    keywords="n8n automation",
    min_publish_date="2024-01-01"
)

# Using DuckDuckGo Search
posts = await search_linkedin_posts_duckduckgo(
    keywords="n8n automation",
    min_publish_date="2024-01-01"
)

# Using Exa Search (requires EXA_API_KEY)
posts = await search_linkedin_posts_exa(
    keywords="n8n automation",
    min_publish_date="2024-01-01"
)
```

### Search Provider Comparison

1. **Google Search with LLM**
   - Best for: Comprehensive results with good content extraction
   - Requires: TOGETHER_API_KEY
   - Features: Full content extraction, hashtag detection

2. **DuckDuckGo Search**
   - Best for: Quick searches without API key
   - Requires: No API key
   - Features: Basic content extraction, date filtering

3. **Exa Search**
   - Best for: Semantic search with high relevance
   - Requires: EXA_API_KEY
   - Features: Semantic understanding, good date filtering, fast results

## Output Format

All search providers return results in a consistent format using the `LinkedInSearchResult` class:

```python
@dataclass
class LinkedInSearchResult:
    title: str
    url: str
    description: str
    date: Optional[datetime]
    author: Optional[str]
    tags: List[str]
```

## Development

### Project Structure

```
n8nlinkedInPost/
├── api/
│   └── routes.py         # API endpoints
├── models/
│   └── schemas.py        # Pydantic models
├── utils/
│   └── linkedin.py       # LinkedIn scraping utilities
├── main.py              # FastAPI application
├── Dockerfile           # Docker configuration
├── requirements.txt     # Python dependencies
└── .env                # Environment variables
```

### Running Tests

```bash
pytest
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 