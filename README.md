# LinkedIn Post Crawler for n8n

A FastAPI-based service that searches and extracts content from LinkedIn posts, designed to work with n8n workflows.

## Features

- Search LinkedIn posts using keywords
- Filter posts by date range (min and max publish dates)
- Extract post content and metadata
- Convert posts to markdown format
- Debug mode with HTML output
- Configurable LLM provider for content extraction
- Docker support for easy deployment

## Installation

### Using Docker

1. Build the Docker image:
```bash
docker build -t n8n-linkedin-post .
```

2. Run the container:
```bash
docker run -p 8000:8000 -e TOGETHER_API_KEY=your_api_key n8n-linkedin-post
```

### Local Development

1. Clone the repository:
```bash
git clone <your-repo-url>
cd n8nlinkedInPost
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create `.env` file with your API keys:
```bash
TOGETHER_API_KEY=your_api_key
```

5. Run the application:
```bash
uvicorn main:app --reload
```

## API Usage

### Search Endpoint

`POST /search`

Request body:
```json
{
    "keywords": "n8n automation workflow",
    "min_publish_date": "2024-01-01",
    "max_publish_date": "2024-03-31",
    "debug_html": false,
    "llm_provider": "together_ai/meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo"
}
```

Response:
```json
{
    "posts": [
        {
            "title": "Example Post",
            "url": "https://linkedin.com/posts/example",
            "author": "John Doe",
            "date": "2024-02-01",
            "content": "Post content in markdown",
            "tags": ["n8n", "automation"],
            "debug_files": null
        }
    ],
    "total_posts": 1,
    "search_metadata": {
        "keywords": "n8n automation workflow",
        "min_publish_date": "2024-01-01",
        "max_publish_date": "2024-03-31",
        "timestamp": "2024-03-20T10:30:00.000Z"
    }
}
```

### Debug Files Endpoint

`GET /debug/{filename}`

Returns the debug HTML file for a specific post.

## Environment Variables

- `TOGETHER_API_KEY`: API key for Together.ai LLM service
- `PORT`: Port to run the service on (default: 8000)

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