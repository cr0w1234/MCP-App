# MCP App

A Model Context Protocol (MCP) server implementation designed for deployment, providing database querying capabilities and OpenAI API integration.

![UI](ui_img.png "UI Demo")

## 📁 Project Structure

```
mcp-server/
├── Dockerfile                   # Container configuration for Cloud Run deployment
├── newest-mcp-server.py         # Main MCP server application
├── pyproject.toml               # Python project dependencies and configuration
└── uv.lock                      # Dependency lock file for reproducible builds
test-mcp-server/
├── test_mcp_server.py           # Test local or deployed MCP server on custom queries
└── test_openai.py               # Test deployed MCP server on OpenAI Responses API
rag-mcp-app/                 
├── README_UI.md                 # UI documentation and setup guide
├── persistence_ui_memory.py     # Main UI with chat memory persistence and connected to PostGres Database + OpenAI API
├── rag_system.py                # Core RAG system implementation
└── supabase_setup_memory.sql    # Database schema for storing chat information
```

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- PostgreSQL database
- Deployment service account (e.g. Google Cloud, AWS)
- Environment variables configured

### Setup
1. **Set up environment variables**:
   Create .env file with:
   OPENAI_API_KEY (create in OpenAI)
   DATABASE_URL (e.g. postgresql://user:pass@host:port/db)
   MCP_SERVER_URL (http://localhost:8080/mcp/ if local. Always add /mcp/ to the end of the URL)
   SUPABASE_URL (e.g. https://cvzlylxhvthjvmjuluqe.supabase.co)
   SUPABASE_ANON_KEY (found in Supabase settings)


2. **Install dependencies**:
   ```bash
   cd mcp-server
   uv sync
   ```
   Or manually install the required depencies in the toml file

3. **Run the server locally**:
   ```bash
   uv run newest-mcp-server.py
   ```

### Cloud Run Deployment (if using Google Cloud)

1. **Build and deploy**:
   Follow https://cloud.google.com/run/docs/tutorials/deploy-remote-mcp-server#container-image
   

## 🛠️ Available Tools

The MCP server provides the following tools:

- **`pg_query(sql)`**: Execute read-only SQL queries against PostgreSQL database
- **`pg_explain(sql)`**: Return EXPLAIN (FORMAT JSON) for a query as JSON from PostgreSQL.

## 🧪 Testing

### Test MCP Server Functionality
```bash
cd test-mcp-server
python test_mcp_server.py
```

### Test OpenAI Integration
```bash
cd test-mcp-server
python test_openai.py
```

## 🌐 RAG Application

The `rag-mcp-app/` directory contains a web-based RAG/MCP system with persistent chat functionality:

### Features
- **Persistent Chat Sessions**: Chat history saved to Supabase database
- **Document Processing**: Handles PDF, DOCX, and other formats
- **Vector Search**: Semantic search across document embeddings
- **MCP Integration**: Combines traditional RAG with MCP tool access

### Setup
1. **Database Setup**: Run `supabase_setup_memory.sql` in your Supabase instance to create the chat-storing table
2. **Environment Variables**: Configure Supabase and OpenAI API keys
3. **Run Application**: `python persistence_ui_memory.py`

See `rag-mcp-app/README_UI.md` for more detailed information.

## 🔒 Security

- **Read-only Database Access**: Only SELECT queries are permitted
- **SQL Injection Protection**: Comprehensive query validation
- **Connection Pooling**: Secure database connection management
- **Environment Variables**: Sensitive data stored securely


## 🆘 Troubleshooting

### Common Issues

1. **Database Connection Errors**
   - Verify `DATABASE_URL` format
   - Check database permissions
   - Ensure database accessibility

2. **Server Not Starting**
   - Check environment variables
   - Verify port 8080 availability
   - Check dependency installation

3. **MCP Tools Not Working**
   - Verify server URL configuration
   - Check tool registration
   - Review server logs
