# MCP Server and RAG UI Documentation

This repository contains two main components:
1. **working-mcp-on-cloudrun**: MCP server implementation and deployment tools
2. **rag-mcp-server**: Simple web UI for interacting with MCP tools

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

**Security Features**:
```python
# Only SELECT queries allowed
if not sql.strip().upper().startswith("SELECT"):
    raise ValueError("Only SELECT queries are allowed. This is a read-only database connection.")

# Dangerous keyword filtering
dangerous_keywords = ["INSERT", "UPDATE", "DELETE", "DROP", "CREATE", "ALTER", ...]
```

#### `test_mcp_server.py`
**Purpose**: Testing utilities for MCP server functionality.

**Usage**:
```python
# Test database connectivity
python test_mcp_server.py

# Test specific MCP tools
python test_mcp_server.py --tool query_demo_db
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

#### Cloud Run Deployment
```bash
# Build and deploy to Google Cloud Run
gcloud run deploy mcp-server \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

#### Environment Variables
```bash
DATABASE_URL=postgresql://user:pass@host:port/db
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

1. **Clone and Install Dependencies**
```bash
git clone <repository-url>
cd test-rag-mcp

# Install MCP server dependencies
cd working-mcp-on-cloudrun
pip install -e .

# Install RAG UI dependencies
cd ../rag-mcp-server
pip install flask python-dotenv
```

2. **Environment Configuration**
```bash
# Create .env files in both directories
cp .env.example .env

# Configure your environment variables
DATABASE_URL=postgresql://user:pass@host:port/db
OPENAI_API_KEY=your_openai_api_key
TMDB_API_KEY=your_tmdb_api_key
```

3. **Database Setup**
```sql
-- Create read-only user (recommended)
CREATE USER readonly_user WITH PASSWORD 'your_password';
GRANT CONNECT ON DATABASE your_database TO readonly_user;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO readonly_user;
```

4. **Run the Applications**
```bash
# Terminal 1: Start MCP server
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

# Test specific tools
python -c "
from readonly_db_mcp_server import query_demo_db
result = query_demo_db('SELECT COUNT(*) FROM companies')
print(result)
"
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

## 🚀 Production Deployment

### Cloud Run Deployment
```bash
# Deploy MCP server
cd working-mcp-on-cloudrun
gcloud run deploy mcp-server --source .

# Deploy RAG UI
cd ../rag-mcp-server
gcloud run deploy rag-ui --source .
```

### Environment Variables for Production
```bash
# Set production environment variables
gcloud run services update mcp-server \
  --set-env-vars DATABASE_URL=$DATABASE_URL,OPENAI_API_KEY=$OPENAI_API_KEY
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

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

### Support
For issues and questions, please open an issue in the repository. 