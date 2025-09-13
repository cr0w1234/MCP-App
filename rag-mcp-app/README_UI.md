# Persistent Chat RAG System

This enhanced version of the RAG system includes persistent chat functionality using Supabase as the backend database. Users can now:

- Create new chat sessions
- Return to previous chat sessions
- Have their chat history persist across browser refreshes
- View a list of all previous chat sessions
- Maintain conversation context with response IDs for continuity

## Features

### Session Management
- **Automatic Session Creation**: New sessions are created automatically when needed
- **Session Persistence**: Sessions are stored in localStorage and restored on page reload
- **Session History**: View all previous chat sessions with timestamps
- **Session Switching**: Click on any previous session to load its chat history
- **Session Deletion**: Delete entire chat sessions and all associated messages

### Message Persistence
- **Automatic Saving**: All user messages and assistant responses are automatically saved
- **Order Preservation**: Messages maintain their chronological order within each session
- **Rich Content Storage**: Full message content including markdown formatting is preserved
- **Response ID Tracking**: Maintains conversation continuity with OpenAI response IDs

## Setup Instructions

### 1. Database Setup

Run the SQL commands in `supabase_setup_memory.sql` in your Supabase SQL editor. This will:

- Create the `openai_memory_chats` table with proper schema
- Set up indexes for optimal performance
- Enable Row Level Security (RLS) with anonymous access policies
- Grant necessary permissions to the anon role

### 2. Environment Variables

If not done already, create a `.env` file with the following variables:

```env
# Supabase Configuration
SUPABASE_URL=your_supabase_project_url
SUPABASE_ANON_KEY=your_supabase_anon_key

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key

# MCP Server Configuration
MCP_SERVER_URL=your_mcp_server_url
```


### 3. Run the Application

```bash
python persistence_ui_memory.py
```

The application will be available at `http://localhost:5000`.

## API Endpoints

### Session Management

- `POST /api/sessions` - Create a new chat session
- `GET /api/sessions` - Get all chat sessions with metadata (sorted by last activity)
- `DELETE /api/sessions/<session_id>` - Delete a session and all its messages

### Message Management

- `GET /api/sessions/<session_id>/messages` - Get all messages for a session (ordered chronologically)
- `POST /api/sessions/<session_id>/messages` - Save a new message with optional response_id

### Chat Endpoints

- `GET /` - Main web interface
- `POST /ask` - Traditional RAG search
- `POST /ask_mcp` - MCP-powered search with conversation memory
- `GET /doc/<path>` - Serve document files

## Database Schema Details

### openai_memory_chats Table

| Column | Type | Description |
|--------|------|-------------|
| `id` | SERIAL PRIMARY KEY | Unique message identifier |
| `session_id` | TEXT | Unique session identifier (UUID) |
| `content` | JSONB | Message content with role, text, and metadata |
| `order` | INTEGER | Message order within the session (1, 2, 3, ...) |
| `response_id` | TEXT | OpenAI response ID for conversation continuity (optional) |
| `timestamp` | TIMESTAMP WITH TIME ZONE | When the message was created |

### Content JSON Structure

```json
{
  "role": "user|assistant",
  "content": "The actual message text",
  "type": "regular|mcp",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

### Database Features

- **Row Level Security (RLS)**: Enabled with anonymous access policies
- **Indexes**: Optimized for session_id, order, timestamp, and response_id queries
- **Permissions**: Full CRUD access granted to anonymous users (development mode)

## Usage

1. **Start a New Chat**: Click "New Chat" to create a fresh session
2. **Continue Previous Chat**: Click on any session in the sidebar to resume that conversation
3. **Automatic Persistence**: Your current session is automatically saved and restored when you refresh the page
4. **Session History**: View all your previous chats in the sidebar, sorted by most recent activity
5. **Delete Sessions**: Remove entire chat sessions and all associated messages
6. **Dual Search Modes**: Use traditional RAG search or MCP-powered database queries

## Troubleshooting

### Common Issues

1. **"Please set SUPABASE_URL and SUPABASE_ANON_KEY environment variables"**
   - Make sure your `.env` file is in the correct location
   - Verify the environment variables are set correctly

2. **Database connection errors**
   - Check your Supabase project URL and API key
   - Ensure the `openai_memory_chats` table exists with the correct schema
   - Verify RLS policies are properly configured

3. **Messages not saving**
   - Check browser console for JavaScript errors
   - Verify the API endpoints are responding correctly
   - Ensure the anon role has proper permissions

4. **Session not persisting**
   - Check localStorage in browser developer tools
   - Verify session creation API is working
   - Ensure Supabase connection is established

### Debug Mode

To enable debug logging, modify the Flask app initialization:

```python
app.run(host='127.0.0.1', port=5000, debug=True)
```

This will provide more detailed error messages and auto-reload on code changes.
