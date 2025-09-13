# Persistent Chat RAG System

This enhanced version of the RAG system includes persistent chat functionality using Supabase as the backend database. Users can now:

- Create new chat sessions
- Return to previous chat sessions
- Have their chat history persist across browser refreshes
- View a list of all previous chat sessions

## Features

### Session Management
- **Automatic Session Creation**: New sessions are created automatically when needed
- **Session Persistence**: Sessions are stored in localStorage and restored on page reload
- **Session History**: View all previous chat sessions with timestamps
- **Session Switching**: Click on any previous session to load its chat history

### Message Persistence
- **Automatic Saving**: All user messages and assistant responses are automatically saved
- **Order Preservation**: Messages maintain their chronological order within each session
- **Rich Content Storage**: Full message content including markdown formatting is preserved

## Setup Instructions

### 1. Database Setup

Create a Supabase table with the following schema:

```sql
CREATE TABLE openai_chats (
    id SERIAL PRIMARY KEY,
    session_id TEXT NOT NULL,
    content JSONB NOT NULL,
    "order" INTEGER NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX idx_openai_chats_session_id ON openai_chats(session_id);
CREATE INDEX idx_openai_chats_order ON openai_chats(session_id, "order");
CREATE INDEX idx_openai_chats_timestamp ON openai_chats(timestamp);
```

### 2. Environment Variables

Create a `.env` file in the `rag-mcp-server` directory with the following variables:

```env
# Supabase Configuration
SUPABASE_URL=your_supabase_project_url
SUPABASE_ANON_KEY=your_supabase_anon_key

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key

# MCP Server Configuration (optional)
MCP_SERVER_URL=http://localhost:8080/mcp/
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the Application

```bash
python persistence_ui.py
```

The application will be available at `http://localhost:5000`.

## API Endpoints

### Session Management

- `POST /api/sessions` - Create a new chat session
- `GET /api/sessions` - Get all chat sessions with metadata
- `DELETE /api/sessions/<session_id>` - Delete a session and all its messages

### Message Management

- `GET /api/sessions/<session_id>/messages` - Get all messages for a session
- `POST /api/sessions/<session_id>/messages` - Save a new message

## Testing

Run the test script to verify the persistence functionality:

```bash
python test_persistence.py
```

This will test:
- Session creation
- Message saving
- Message loading
- Session listing

## Database Schema Details

### openai_chats Table

| Column | Type | Description |
|--------|------|-------------|
| `id` | SERIAL PRIMARY KEY | Unique message identifier |
| `session_id` | TEXT | Unique session identifier (UUID) |
| `content` | JSONB | Message content with role, text, and metadata |
| `order` | INTEGER | Message order within the session (1, 2, 3, ...) |
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

## Usage

1. **Start a New Chat**: Click "New Chat" to create a fresh session
2. **Continue Previous Chat**: Click on any session in the sidebar to resume that conversation
3. **Automatic Persistence**: Your current session is automatically saved and restored when you refresh the page
4. **Session History**: View all your previous chats in the sidebar, sorted by most recent activity

## Troubleshooting

### Common Issues

1. **"Please set SUPABASE_URL and SUPABASE_ANON_KEY environment variables"**
   - Make sure your `.env` file is in the correct location
   - Verify the environment variables are set correctly

2. **Database connection errors**
   - Check your Supabase project URL and API key
   - Ensure the table exists with the correct schema

3. **Messages not saving**
   - Check browser console for JavaScript errors
   - Verify the API endpoints are responding correctly

### Debug Mode

To enable debug logging, modify the Flask app initialization:

```python
app.run(host='127.0.0.1', port=5000, debug=True)
```

This will provide more detailed error messages and auto-reload on code changes.