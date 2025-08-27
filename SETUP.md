# Setup Guide

This guide will help you set up the MCP server and RAG UI for local development.

## Prerequisites

- Python 3.8+
- PostgreSQL database
- OpenAI API key
- TMDB API key (optional, for movie/TV show data)

## Environment Configuration

1. **Edit `.env` with your actual values:**
   ```bash
   # Database Configuration
   DATABASE_URL=postgresql://username:password@host:port/database_name
   
   # OpenAI Configuration
   OPENAI_API_KEY=your_openai_api_key_here
   
   # TMDB Configuration (optional)
   TMDB_API_KEY=your_tmdb_api_key_here
   TMDB_ACCOUNT_ID=your_tmdb_account_id_here
   
   # MCP Server Configuration
   MCP_SERVER_URL=https://your-mcp-server-url.run.app/mcp/
   
   ```

## Database Setup

1. **Create a PostgreSQL database** (you can use services like Supabase, Railway, or local PostgreSQL)

2. **Set up the database schema** - The MCP server expects specific tables. You can create a demo database with sample data or connect to your existing database.

3. **Update the `DATABASE_URL`** in your `.env` file with your database connection string.

## Running the MCP Server

### Local Development

1. **Navigate to the MCP server directory:**
   ```bash
   cd working-mcp-on-cloudrun
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   # or if using uv:
   uv sync
   ```

3. **Run the MCP server:**
   ```bash
   python readonly-db-mcp-server.py
   ```

The server will start on `http://localhost:8080/mcp/`

### Testing the MCP Server

1. **Test the server:**
   ```bash
   uv run test_mcp_server.py
   ```

2. **Test with OpenAI:**
   ```bash
   python test_openai.py
   ```

## Running the RAG UI

1. **Navigate to the RAG server directory:**
   ```bash
   cd rag-mcp-server
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the UI:**
   ```bash
   python ui.py
   ```

The UI will be available at `http://localhost:5000`

## Deployment to Google Cloud Run

1. **Build and deploy the MCP server:**
   ```
   Follow https://cloud.google.com/run/docs/tutorials/deploy-remote-mcp-server#source 
   ```

2. **Update your `.env` file** with the deployed MCP server URL:
   ```bash
   MCP_SERVER_URL=https://your-mcp-server-url.run.app/mcp/
   ```


## Security Notes

- **Never commit your `.env` file** - it's already in `.gitignore`
- **Use environment variables** for all sensitive configuration
- **The MCP server enforces read-only database access** for security
- **Consider using Google Cloud Secret Manager** for production deployments

## Troubleshooting

### Common Issues

1. **Database connection errors:**
   - Verify your `DATABASE_URL` is correct
   - Ensure your database is accessible from your deployment environment
   - Check firewall rules if using cloud databases

2. **MCP server not responding:**
   - Verify the server URL in your `.env` file
   - Check that the MCP server is running and accessible
   - Review logs for any startup errors

3. **OpenAI API errors:**
   - Verify your `OPENAI_API_KEY` is valid
   - Check your OpenAI account has sufficient credits
   - Ensure you're using the correct API endpoint

### Getting Help

- Check the logs in Google Cloud Console for deployment issues
- Review the MCP server logs for database connection problems
- Verify all environment variables are set correctly 