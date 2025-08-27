# MCP Server and RAG UI Documentation

This repository contains two main components:
1. **working-mcp-on-cloudrun**: MCP server implementation and deployment tools
2. **rag-mcp-server**: Simple web UI for interacting with MCP tools

> **📖 Quick Start**: See [SETUP.md](SETUP.md) for detailed setup instructions.

## 📁 Project Structure

```
test-rag-mcp/
├── working-mcp-on-cloudrun/          # MCP server implementation
│   ├── readonly-db-mcp-server.py     # Read-only database MCP server
│   ├── test_mcp_server.py            # MCP server testing utilities
│   ├── test_openai.py                # OpenAI API integration tests
│   ├── pyproject.toml                # Python dependencies
│   ├── uv.lock                       # Dependency lock file
│   └── Dockerfile                    # Cloud Run deployment
└── rag-mcp-server/                   # Web UI for MCP interaction
    ├── ui.py                         # Flask web application
    ├── rag_system.py                 # RAG (Retrieval-Augmented Generation) system
    └── documents/                    # Document storage for RAG
```

## 🚀 MCP Server (working-mcp-on-cloudrun)

### Overview
The MCP (Model Context Protocol) server provides tools for database querying and external API integration. It's designed to be deployed on Google Cloud Run for scalable, serverless operation.

### Key Files

#### `readonly-db-mcp-server.py`
**Purpose**: Main MCP server implementation with read-only database access and TMDB API integration.

**Features**:
- **Read-only Database Queries**: Secure PostgreSQL access with SELECT-only restrictions
- **TMDB API Integration**: Intelligent movie/TV show data retrieval
- **Connection Pooling**: Robust database connection management
- **Security Validation**: SQL injection protection and query validation

**Available Tools**:
- `query_demo_db(sql)`: Execute read-only SQL queries
- `tmdb_intelligent_call(request)`: Smart TMDB API calls
- `http_get(url, headers)`: Generic HTTP GET requests
- `add(a, b)`, `subtract(a, b)`: Basic arithmetic operations


#### `test_mcp_server.py`
**Purpose**: Testing utilities for MCP server functionality.

**Usage**:
```python
# Test MCP tools connectivity locally
uv run test_mcp_server.py
```

#### `test_openai.py`
**Purpose**: OpenAI API integration testing and validation.

**Features**:
- Tests OpenAI client configuration
- Validates API key authentication
- Tests MCP tool integration with OpenAI

### Deployment

#### Local Development
```bash
cd working-mcp-on-cloudrun
pip install -r requirements.txt
python readonly-db-mcp-server.py
```

#### Cloud Run MCP Server Deployment
Follow this guide: https://cloud.google.com/run/docs/tutorials/deploy-remote-mcp-server#source

#### Environment Variables
```bash
DATABASE_URL=postgresql://user:pass@host:port/db
MCP_SERVER_URL=https://your-mcp-server-url.run.app/mcp/
TMDB_API_KEY=your_tmdb_api_key
TMDB_ACCOUNT_ID=your_account_id
TMDB_SESSION_ID=your_session_id
OPENAI_API_KEY=your_openai_api_key
```

## 🌐 RAG UI (rag-mcp-server)

### Overview
A simple Flask-based web interface that combines traditional RAG (Retrieval-Augmented Generation) with MCP tool integration for enhanced query capabilities.

### Key Files

#### `ui.py`
**Purpose**: Main Flask web application providing the user interface.

**Features**:
- **Dual Search Modes**: Traditional RAG and MCP-powered search
- **Conversation Interface**: Scrollable chat-like interface with conversation history
- **Document References**: Links to source documents and references
- **MCP Integration**: Seamless integration with MCP tools

**Endpoints**:
- `GET /`: Main web interface
- `POST /ask`: Traditional RAG search
- `POST /ask_mcp`: MCP-powered database search
- `GET /doc/<path>`: Document serving

**Conversation Memory**:
```python
# Global conversation state management
current_response_id = None

@app.route('/ask_mcp', methods=['POST'])
def ask_mcp():
    global current_response_id
    # Maintains conversation continuity across requests
```

#### `rag_system.py`
**Purpose**: RAG (Retrieval-Augmented Generation) system implementation.

**Features**:
- **Document Processing**: Handles PDF, DOCX, and other document formats
- **Vector Embeddings**: Creates and manages document embeddings
- **Semantic Search**: Retrieves relevant document chunks
- **Answer Generation**: Generates answers based on retrieved context

**Usage**:
```python
from rag_system import RAGService

rag_service = RAGService()
result = rag_service.answer_question("Your question here")
```

### UI Features

#### Conversation Interface
- **Scrollable Chat**: Full conversation history with automatic scrolling
- **Message Types**: Distinct styling for user questions and assistant responses
- **Markdown Support**: Rich text formatting for responses
- **Reference Links**: Clickable links to source documents

#### Search Modes
1. **Traditional RAG** (`/ask`): Document-based search with vector embeddings
2. **MCP Search** (`/ask_mcp`): Database querying with conversation memory

## 🔧 Setup and Installation

### Prerequisites
- Python 3.8+
- PostgreSQL database
- OpenAI API key
- TMDB API key (optional)
- Google Cloud account (for deployment)

### Local Setup

1.  **Run the Applications**
```bash
# Terminal 1: Start MCP server (no need if using an already deployed MCP server url)
cd working-mcp-on-cloudrun
python readonly-db-mcp-server.py

# Terminal 2: Start RAG UI
cd rag-mcp-server
python ui.py
```

## 🧪 Testing

### MCP Server Testing
```bash
cd working-mcp-on-cloudrun

# Test database connectivity
python test_mcp_server.py

# Test OpenAI integration
python test_openai.py

```

### RAG UI Testing
```bash
cd rag-mcp-server

# Start the UI
python ui.py

# Access at http://localhost:5000
# Test both search modes:
# 1. Traditional RAG: Ask questions about documents
# 2. MCP Search: Query the database with natural language
```

## 🔒 Security Considerations

### Database Security
- **Read-only Access**: Only SELECT queries are allowed
- **SQL Injection Protection**: Comprehensive query validation
- **Connection Pooling**: Secure connection management
- **Environment Variables**: Sensitive data stored in environment variables

### API Security
- **Rate Limiting**: Implement rate limiting for production
- **Authentication**: Add authentication for production deployments
- **CORS**: Configure CORS policies appropriately

## 📊 Monitoring and Logging

### Google Cloud Logging
The MCP server includes comprehensive logging for Google Cloud:
```python
logger.info(f"MCP Query Request: {question}")
logger.info(f"Tool calls executed: {len(resp.tool_calls)}")
```

### Log Levels
- **INFO**: Normal operation logs
- **WARNING**: Connection pool issues
- **ERROR**: Database connection failures

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## 🆘 Troubleshooting

### Common Issues

1. **Database Connection Errors**
   - Verify DATABASE_URL format
   - Check database user permissions
   - Ensure database is accessible

2. **MCP Server Not Starting**
   - Check environment variables
   - Verify port availability
   - Check dependency installation

3. **RAG UI Not Loading**
   - Ensure Flask dependencies are installed
   - Check port 5000 availability
   - Verify document directory exists
