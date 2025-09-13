from flask import Flask, request, jsonify, render_template_string, send_from_directory
from pathlib import Path
import os
import uuid
import json
from datetime import datetime
from supabase import create_client, Client
from dotenv import load_dotenv

from rag_system import RAGService
# from hybrid_service import HybridRAGEmailService

# Load environment variables
load_dotenv(override=True)

app = Flask(__name__)
rag_service = RAGService()
# hybrid_service = HybridRAGEmailService()

# Initialize Supabase client
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_ANON_KEY')

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Please set SUPABASE_URL and SUPABASE_ANON_KEY environment variables")

print(SUPABASE_URL)
print(SUPABASE_KEY)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Directory where original documents (PDF, DOCX, etc.) reside. Update as needed.
DOC_DIR = Path("documents")  # make sure this folder exists and contains the source files

HTML_PAGE = """
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8" />
    <title>RAG Q&A Demo - Persistent Chat</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .container { max-width: 1200px; margin: 0 auto; }
        .main-content { display: flex; gap: 20px; }
        .chat-section { flex: 2; }
        .sidebar { flex: 1; }
        textarea { width: 100%; padding: 10px; font-size: 1rem; resize: vertical; }
        button { padding: 8px 18px; font-size: 1rem; margin-top: 8px; margin-right: 8px; }
        .session-button { 
            display: block; 
            width: 100%; 
            padding: 8px; 
            margin: 4px 0; 
            text-align: left; 
            border: 1px solid #ddd; 
            background: white; 
            cursor: pointer; 
        }
        .session-button:hover { background: #f0f0f0; }
        .session-button.active { background: #e3f2fd; border-color: #2196f3; }
        #conversation { 
            margin-top: 2rem; 
            max-height: 600px; 
            overflow-y: auto; 
            border: 1px solid #ccc; 
            padding: 20px; 
            background: #f9f9f9; 
        }
        .message { 
            margin-bottom: 20px; 
            padding: 15px; 
            border-radius: 5px; 
        }
        .user-message { 
            background: #e3f2fd; 
            border-left: 4px solid #2196f3; 
        }
        .assistant-message { 
            background: white; 
            border-left: 4px solid #4caf50; 
        }
        .message h3 { margin-top: 0; margin-bottom: 10px; }
        pre, code { background: #f4f4f4; padding: 12px; overflow-x: auto; display: block; }
        .session-info { 
            background: #f0f0f0; 
            padding: 10px; 
            margin-bottom: 10px; 
            border-radius: 5px; 
        }
        .loading { color: #666; font-style: italic; }
    </style>
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
</head>
<body>
<div class="container">
  <h2>RAG Q&A Demo - Persistent Chat</h2>
  
  <div class="main-content">
    <div class="chat-section">
      <div class="session-info">
        <strong>Current Session:</strong> <span id="current-session-id">Loading...</span>
        <button onclick="createNewSession()" style="float: right;">New Chat</button>
      </div>
      
      <form id="qa-form" onsubmit="return false;">
        <textarea id="question" rows="3" placeholder="Type your question here"></textarea>
        <br />
        <button onclick="submitQ()">Ask</button>
        <button onclick="submitMCP()">MCP Search</button>
      </form>
      <div id="conversation"></div>
    </div>
    
    <div class="sidebar">
      <h3>Previous Chats</h3>
      <div id="sessions-list">
        <div class="loading">Loading sessions...</div>
      </div>
    </div>
  </div>
</div>

<script>
// Global state
let currentSessionId = null;
let conversationHistory = [];

// Initialize the app
document.addEventListener('DOMContentLoaded', async function() {
  await initializeApp();
});

async function initializeApp() {
  // Check if there's a session ID in localStorage
  currentSessionId = localStorage.getItem('currentSessionId');
  
  if (!currentSessionId) {
    // Create a new session
    await createNewSession();
  } else {
    // Load existing session
    await loadSession(currentSessionId);
  }
  
  // Load sessions list
  await loadSessionsList();
  
  // Update UI
  updateSessionInfo();
}

async function createNewSession() {
  try {
    const response = await fetch('/api/sessions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    });
    
    if (response.ok) {
      const data = await response.json();
      currentSessionId = data.session_id;
      localStorage.setItem('currentSessionId', currentSessionId);
      clearConversation();
      updateSessionInfo();
      await loadSessionsList();
    } else {
      console.error('Failed to create session');
    }
  } catch (error) {
    console.error('Error creating session:', error);
  }
}

async function loadSession(sessionId) {
  try {
    const response = await fetch(`/api/sessions/${sessionId}/messages`);
    if (response.ok) {
      const data = await response.json();
      clearConversation();
      
      // Small delay to ensure DOM is cleared
      await new Promise(resolve => setTimeout(resolve, 10));
      
      // Load messages in order
      for (const message of data.messages) {
        let content, role, type;
        
        // Parse the content - it should be a JSON object
        if (typeof message.content === 'string') {
          try {
            const parsedContent = JSON.parse(message.content);
            content = parsedContent.content || message.content;
            role = parsedContent.role || 'assistant';
            type = parsedContent.type || 'regular';
          } catch (e) {
            // If parsing fails, treat as plain text
            content = message.content;
            role = 'assistant';
            type = 'regular';
          }
        } else {
          // If it's already an object
          content = message.content.content || JSON.stringify(message.content);
          role = message.content.role || 'assistant';
          type = message.content.type || 'regular';
        }
        
        addMessage(role, content, type, true); // Skip saving when loading from database
      }
    } else {
      console.error('Failed to load session');
    }
  } catch (error) {
    console.error('Error loading session:', error);
  }
}

async function loadSessionsList() {
  try {
    const response = await fetch('/api/sessions');
    if (response.ok) {
      const data = await response.json();
      displaySessionsList(data.sessions);
    } else {
      console.error('Failed to load sessions list');
    }
  } catch (error) {
    console.error('Error loading sessions list:', error);
  }
}

function displaySessionsList(sessions) {
  const sessionsListEl = document.getElementById('sessions-list');
  
  if (sessions.length === 0) {
    sessionsListEl.innerHTML = '<div class="loading">No previous chats</div>';
    return;
  }
  
  sessionsListEl.innerHTML = sessions.map(session => {
    const date = new Date(session.last_activity).toLocaleDateString();
    const time = new Date(session.last_activity).toLocaleTimeString();
    const isActive = session.session_id === currentSessionId;
    
    return `
      <button class="session-button ${isActive ? 'active' : ''}" 
              onclick="switchToSession('${session.session_id}')">
        <div style="font-weight: bold;">${date}</div>
        <div style="font-size: 0.8em; color: #666;">${time}</div>
        <div style="font-size: 0.8em; color: #999;">${session.session_id.substring(0, 8)}...</div>
      </button>
    `;
  }).join('');
}

async function switchToSession(sessionId) {
  currentSessionId = sessionId;
  localStorage.setItem('currentSessionId', currentSessionId);
  await loadSession(sessionId);
  updateSessionInfo();
  await loadSessionsList(); // Refresh to update active state
}

function updateSessionInfo() {
  const sessionIdEl = document.getElementById('current-session-id');
  if (currentSessionId) {
    sessionIdEl.textContent = currentSessionId.substring(0, 8) + '...';
  } else {
    sessionIdEl.textContent = 'No session';
  }
}

function clearConversation() {
  const conversationEl = document.getElementById('conversation');
  conversationEl.innerHTML = '';
  conversationHistory = [];
}

async function saveMessage(content, type = 'user', responseId = null) {
  if (!currentSessionId) return;
  
  try {
    const response = await fetch(`/api/sessions/${currentSessionId}/messages`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content, type, response_id: responseId })
    });
    
    if (!response.ok) {
      console.error('Failed to save message');
    }
  } catch (error) {
    console.error('Error saving message:', error);
  }
}

function addMessage(role, content, type = 'regular', skipSave = false, responseId = null) {
  const conversationEl = document.getElementById('conversation');
  const messageDiv = document.createElement('div');
  messageDiv.className = `message ${role}-message`;
  
  let html = `<h3>${role === 'user' ? 'You' : 'Assistant'}</h3>`;
  
  if (type === 'regular') {
    html += marked.parse(content);
  } else if (type === 'mcp') {
    html += marked.parse(content);
  }
  
  messageDiv.innerHTML = html;
  conversationEl.appendChild(messageDiv);
  conversationEl.scrollTop = conversationEl.scrollHeight;
  
  // Save message to database (unless we're loading from database)
  if (!skipSave) {
    const messageContent = {
      role: role,
      content: content,
      type: type,
      timestamp: new Date().toISOString()
    };
    saveMessage(messageContent, role, responseId);
  }
}

async function submitQ() {
  const qEl = document.getElementById('question');
  const question = qEl.value.trim();
  if (!question) return;
  
  addMessage('user', question);
  qEl.value = '';
  
  const res = await fetch('/ask', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question })
  });
  const data = await res.json();
  
  let answer = data.answer;
  if (data.references && data.references.length) {
    answer += '\\n\\n**References:**\\n';
    data.references.forEach(r => {
      const parts = r.source.split('#');
      const base = parts[0];
      let url;
      if (/^https?:\\/\\//.test(base)) {
        url = base;
      } else {
        const filePath = encodeURI(base);
        url = `/doc/${filePath}`;
      }
      const page = parseInt(parts[1]);
      if (!isNaN(page) && url.startsWith('/doc/')) {
        url += `#page=${page+1}`;
      }
      answer += `- [${r.source}](${url}): ${r.snippet.slice(0, 120)}...\\n`;
    });
  }
  
  addMessage('assistant', answer, 'regular');
}

async function submitMCP() {
  const qEl = document.getElementById('question');
  const question = qEl.value.trim();
  if (!question) return;
  
  addMessage('user', question);
  qEl.value = '';
  
  const res = await fetch('/ask_mcp', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, session_id: currentSessionId })
  });
  const data = await res.json();
  
  let answer = data.answer;
  if (data.email_references && data.email_references.length) {
    answer += '\\n\\n**Email References:**\\n';
    data.email_references.forEach(email => {
      const date = new Date(email.sent_at).toLocaleDateString();
      answer += `- **${email.subject}** (${email.from_address} – ${date}): ${email.snippet.slice(0, 150)}...\\n`;
    });
  }
  
  // The response_id will be stored by the backend after the MCP call
  addMessage('assistant', answer, 'mcp');
}
</script>
</body>
</html>
"""


@app.route('/')
def index():
    return render_template_string(HTML_PAGE)


@app.route('/ask', methods=['POST'])
def ask():
    payload = request.get_json(force=True)
    question = payload.get('question', '').strip()
    if not question:
        return jsonify({'error': 'No question provided'}), 400
    result = rag_service.answer_question(question)
    return jsonify(result)

# ---------------------------------------------------------------------------
# MCP search endpoint - query demo db, make api calls to tmdb
# ---------------------------------------------------------------------------
current_response_id = None
@app.route('/ask_mcp', methods=['POST'])
def ask_mcp():
    global current_response_id
    payload = request.get_json(force=True)
    question = payload.get('question', '').strip()
    session_id = payload.get('session_id')
    if not question:
        return jsonify({'error': 'No question provided'}), 400

    from openai import OpenAI
    import os
    import logging
    from dotenv import load_dotenv, find_dotenv

    # Configure logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    logger = logging.getLogger(__name__)

    load_dotenv(override=True)
    client = OpenAI(api_key=os.environ['OPENAI_API_KEY'])

    CLOUD_RUN_URL = os.getenv('MCP_SERVER_URL', 'http://localhost:8080/mcp/')

    # Log the incoming question
    logger.info(f"MCP Query Request: {question}")

    system_prompt = (
        '''You are an assistant that can query the demo database by converting the user's prompt into a series of SQL queries. Answer the user's question strictly based on the provided context regarding the demo database. Use the MCP tool.

        Do not take the user prompt too literally (e.g. if the user prompt mentions find companies that are upset, no need to literally search for the “upset” label if it doesn’t exist. Instead, use whatever related labels, information, etc. that you find fit.)
        '''
    )
    
    context = '''
# DATABASE SCHEMA OVERVIEW

## Available Tables (by Category)

### 🔔 Alert Management
- `alerts` - Main alert records
- `alert_assignments` - Alert assignments to people
- `approved_alerts` - Approved alert templates
- `tag_definitions_on_alerts` - Tags applied to alerts

### 🏢 Company & Organization
- `companies` - Company information and details
- `company_assignments` - People assigned to companies
- `teams` - Team definitions
- `team_members` - Team membership

### 📧 Email & Communication
- `emails` - Email records and metadata
- `threads` - Email thread management
- `email_anaylsis` - Email analysis results
- `email_cluster_mapping` - Email clustering
- `email_question_extractions` - Questions extracted from emails
- `tags_on_emails` - Tags applied to emails
- `notes_on_threads` - Notes on email threads

### 👥 People & Employees
- `people` - People records
- `employees` - Employee information
- `user_roles` - User role assignments
- `role_permissions` - Role-based permissions

### 💰 Payroll & Financial
- `payroll` - Payroll records
- `payroll_files` - Payroll file processing
- `payroll_import` - Imported payroll data
- `payitems` - Payroll item definitions

### 📊 Analytics & Intelligence
- `sentiment_trend_data` - Sentiment analysis trends
- `sentiment_trend_view` - Sentiment trend views
- `thread_analytics` - Thread analysis metrics
- `thread_evaluations` - Thread evaluation results
- `qa_pairs` - Q&A pairs for training
- `stored_answers` - Cached answers

### 🏷️ Tagging & Classification
- `tag_definitions` - Tag definition templates
- `dynamic_tag_definitions` - Dynamic tag definitions
- `keywords` - Keyword definitions
- `parent_clusters` - Parent clustering
- `child_cluster` - Child clustering

### 📄 Document Management
- `documents` - Document metadata
- `document_chunks` - Document text chunks
- `buckets` - Storage buckets

### ⚙️ System & Configuration
- `app_config` - Application configuration
- `prompts` - System prompts
- `assignment_types` - Assignment type definitions
- `assignments` - General assignments

### 🔧 Utility & Testing
- `test` - Test data
- `amiup` - System status

---

## DETAILED TABLE SCHEMAS

### 🔔 Alert Management

#### alerts
- `id` (integer) - Primary key
- `date` (timestamp with time zone) - Alert date
- `company` (text) - Company name
- `body` (text) - Alert content
- `status` (text) - Alert status
- `sender` (text) - Sender information
- `assignee` (text) - Assigned person
- `client_status` (text) - Client status
- `approved` (boolean) - Approval status
- `email_id` (text) - Related email ID
- `thread_id` (text) - Related thread ID
- `tags` (ARRAY) - Applied tags
- `company_id` (text) - Company reference
- `is_company_alert` (boolean) - Company-level alert flag
- `ai_approved` (boolean) - AI approval status
- `is_sent` (boolean) - Sent status

#### alert_assignments
- `id` (integer) - Primary key
- `person_id` (text) - Person reference
- `subscription_type` (character varying) - Subscription type
- `company_id` (text) - Company reference
- `tag_definition_id` (integer) - Tag definition reference
- `alert_id` (integer) - Alert reference
- `receive_emails` (boolean) - Email preference

### 🏢 Company & Organization

#### companies
- `id` (text) - Primary key
- `name` (text) - Company name
- `status` (text) - Company status
- `is_customer` (boolean) - Customer flag
- `summary` (text) - Company summary
- `num_employees` (text) - Employee count
- `client_code` (text) - Client identifier
- `company_code` (text) - Company code
- `strategicaccount` (boolean) - Strategic account flag
- `created_at` (timestamp with time zone) - Creation date
- `updated_at` (timestamp with time zone) - Last update
- `last_contacted` (date) - Last contact date
- `assignee` (text) - Assigned person
- `payroll_schema` (jsonb) - Payroll configuration

### 📧 Email & Communication

#### emails
- `id` (text) - Primary key
- `sent_at` (timestamp without time zone) - Sent date
- `subject` (text) - Email subject
- `from_address` (text) - Sender address
- `body` (text) - Email content
- `thread_id` (text) - Thread reference
- `company_id` (text) - Company reference
- `nps` (smallint) - Net Promoter Score
- `author_id` (double precision) - Author reference
- `case_id` (double precision) - Case reference
- `ai_analysis` (double precision) - AI analysis score
- `processed_at` (double precision) - Processing timestamp
- `created_at` (timestamp with time zone) - Creation date
- `updated_at` (timestamp with time zone) - Last update
- `customer_complaints` (ARRAY) - Complaint tags
- `feature_requests` (ARRAY) - Feature request tags
- `feedback` (ARRAY) - Feedback tags
- `other_topics` (ARRAY) - Other topic tags
- `cc_addresses` (ARRAY) - CC recipients
- `to_addresses` (ARRAY) - TO recipients
- `processed_for_keywords` (boolean) - Keyword processing status

#### threads
- `id` (text) - Primary key
- `subject` (text) - Thread subject
- `status` (text) - Thread status
- `company_id` (text) - Company reference
- `assignee_id` (text) - Assigned person
- `is_public` (boolean) - Public visibility
- `created_at` (timestamp with time zone) - Creation date
- `updated_at` (timestamp with time zone) - Last update

### 👥 People & Employees

#### people
- `id` (text) - Primary key
- `firstname` (text) - First name
- `lastname` (text) - Last name
- `email` (text) - Email address
- `phone` (text) - Phone number
- `title` (text) - Job title
- `is_internal` (boolean) - Internal employee flag
- `is_deleted` (boolean) - Deletion status
- `assignable` (boolean) - Assignment capability
- `can_follow_alerts` (boolean) - Alert following permission
- `tags` (jsonb) - Associated tags
- `created_at` (text) - Creation date
- `updated_at` (text) - Last update

#### employees
- `id` (text) - Primary key
- `first_name` (character varying) - First name
- `last_name` (character varying) - Last name
- `middle_name` (text) - Middle name
- `name_lookup` (ARRAY) - Name search terms
- `work_location` (character varying) - Work location
- `state_residency` (character varying) - State of residence
- `pay_group` (character varying) - Payroll group
- `pay_type` (character varying) - Payment type
- `hourly_rate` (numeric) - Hourly rate
- `emp_number` (numeric) - Employee number
- `company_code` (text) - Company reference
- `employment_status` (text) - Employment status
- `company_id` (text) - Company reference
- `date_added` (timestamp without time zone) - Hire date

### 💰 Payroll & Financial

#### payroll
- `id` (integer) - Primary key
- `session_id` (character varying) - Session identifier
- `employee_id` (text) - Employee reference
- `pay_group` (character varying) - Payroll group
- `pay_item` (character varying) - Payroll item
- `hours` (numeric) - Hours worked
- `hourly_rate` (numeric) - Hourly rate
- `total_dollar_amount` (numeric) - Total amount
- `override_rate` (numeric) - Override rate
- `date_added` (timestamp without time zone) - Entry date

#### payroll_files
- `id` (integer) - Primary key
- `company_id` (text) - Company reference
- `company_name` (text) - Company name
- `email_id` (text) - Related email
- `date` (timestamp with time zone) - File date
- `file_id` (text) - File identifier
- `original_file_name` (text) - Original filename
- `processed` (boolean) - Processing status
- `file_type` (character varying) - File type
- `file_has_payroll_data` (boolean) - Payroll data flag
- `email_body_has_payroll_data` (boolean) - Email payroll data flag
- `email_body` (text) - Email content
- `result` (jsonb) - Processing results
- `current_data` (jsonb) - Current data
- `original_data` (jsonb) - Original data
- `submission_status` (USER-DEFINED) - Submission status
- `submission_details` (jsonb) - Submission details

### 📊 Analytics & Intelligence

#### sentiment_trend_data
- `month` (date) - Month
- `average_nps` (numeric) - Average NPS score
- `nps_count` (integer) - NPS response count
- `last_updated` (timestamp with time zone) - Last update

#### thread_analytics
- `thread_id` (character varying) - Thread reference
- `total_emails` (integer) - Total email count
- `questions_extracted` (integer) - Questions extracted
- `questions_answered` (integer) - Questions answered
- `avg_resolution_time_hours` (numeric) - Average resolution time
- `participants` (jsonb) - Participant data
- `thread_start` (timestamp without time zone) - Thread start
- `thread_end` (timestamp without time zone) - Thread end
- `resolution_status` (character varying) - Resolution status
- `last_analyzed` (timestamp with time zone) - Last analysis

### 🏷️ Tagging & Classification

#### tag_definitions
- `id` (bigint) - Primary key
- `prompt_id` (bigint) - Prompt reference
- `name` (text) - Tag name
- `display_name` (text) - Display name
- `type` (text) - Tag type
- `is_alert` (boolean) - Alert tag flag
- `bucket_id` (numeric) - Bucket reference
- `function_name` (text) - Function name
- `is_company_level_tag` (boolean) - Company-level flag
- `is_active` (boolean) - Active status

#### keywords
- `id` (bigint) - Primary key
- `keyword_name` (text) - Keyword name
- `bucket_id` (bigint) - Bucket reference
- `created_at` (timestamp with time zone) - Creation date
- `updated_at` (timestamp with time zone) - Last update

### 📄 Document Management

#### documents
- `id` (uuid) - Primary key
- `bucket` (text) - Storage bucket
- `object_path` (text) - Object path
- `filename` (text) - Filename
- `mime_type` (text) - MIME type
- `size_bytes` (bigint) - File size
- `uploaded_at` (timestamp with time zone) - Upload date
- `text_content` (text) - Document content
- `owner` (uuid) - Owner reference
- `created_at` (timestamp with time zone) - Creation date

#### document_chunks
- `id` (bigint) - Primary key
- `document_id` (uuid) - Document reference
- `chunk_index` (integer) - Chunk position
- `start_char` (integer) - Start character
- `end_char` (integer) - End character
- `text` (text) - Chunk text
- `tokens` (smallint) - Token count
- `tsv` (tsvector) - Text search vector
- `embedding` (USER-DEFINED) - Vector embedding

### ⚙️ System & Configuration

#### app_config
- `key` (text) - Configuration key
- `value` (text) - Configuration value
- `description` (text) - Configuration description
- `updated_at` (timestamp with time zone) - Last update

#### prompts
- `id` (bigint) - Primary key
- `name` (text) - Prompt name
- `prompt` (text) - Prompt content
- `tag_name` (text) - Associated tag
- `required` (text) - Required fields
- `type` (text) - Prompt type
- `bucket_id` (text) - Bucket reference
- `display_names` (text) - Display names
- `created_at` (timestamp with time zone) - Creation date
- `updated_at` (timestamp with time zone) - Last update

---

## KEY RELATIONSHIPS

### Company Relationships
- `companies` ↔ `company_assignments` (via company_id)
- `companies` ↔ `employees` (via company_id)
- `companies` ↔ `alerts` (via company_id)

### Email Relationships
- `emails` ↔ `threads` (via thread_id)
- `emails` ↔ `companies` (via company_id)
- `emails` ↔ `tags_on_emails` (via email_id)

### People Relationships
- `people` ↔ `employees` (via id)
- `people` ↔ `alert_assignments` (via person_id)
- `people` ↔ `company_assignments` (via person_id)

### Payroll Relationships
- `payroll` ↔ `employees` (via employee_id)
- `payroll_files` ↔ `companies` (via company_id)
- `payroll_import` ↔ `payroll` (via session_id)

### Tagging Relationships
- `tag_definitions` ↔ `tags_on_emails` (via tag_definition_id)
- `tag_definitions` ↔ `tag_definitions_on_alerts` (via tag_definition_id)
- `keywords` ↔ `tags_on_emails` (via keyword_id)
    '''

        # Get the most recent response_id for this session
    previous_response_id = get_latest_response_id_for_session(session_id) if session_id else None
    
    # test_mcp_server
    # "allowed_tools":["query_demo_db"], under server_url
    resp = client.responses.create(
        model="gpt-4.1",
        tools=[
            {
                "type": "mcp",
                "server_label": "test_mcp_server",
                "server_url": CLOUD_RUN_URL,
                "require_approval": "never",
            },
        ],
        input=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"}
        ],
        previous_response_id=previous_response_id,
    )

    # Logging for MCP tool calls
    for output_item in resp.output:
      if getattr(output_item, "type", None) == "mcp_call":
        tool_name = output_item.name
        arguments = output_item.arguments
        logger.info(f"MCP Tool Called: {tool_name} | Arguments: {arguments}")

    print(resp)
    # print(resp.output_text) - shows mcp calls, response objects, etc.
    
    # Store the response_id for this session
    if session_id:
        store_response_id_for_session(session_id, resp.id)
    
    return jsonify({'answer': resp.output_text})


# ---------------------------------------------------------------------------
# MCP email-only search endpoint
# ---------------------------------------------------------------------------

'''
@app.route('/ask_mcp', methods=['POST'])
def ask_mcp():
    payload = request.get_json(force=True)
    question = payload.get('question', '').strip()
    if not question:
        return jsonify({'error': 'No question provided'}), 400

    hybrid_result = hybrid_service.generate_email_only_answer(question)

    result = {
        'answer': hybrid_result.answer,
        'email_references': [
            {
                'id': email.id,
                'subject': email.subject,
                'from_address': email.from_address,
                'sent_at': email.sent_at,
                'snippet': email.snippet,
                'thread_id': email.thread_id
            }
            for email in hybrid_result.email_references
        ]
    }

    return jsonify(result)
'''

# ---------------------------------------------------------------------------
# Helper functions for response_id management
# ---------------------------------------------------------------------------

def get_latest_response_id_for_session(session_id):
    """Get the most recent response_id for a session."""
    try:
        result = supabase.table('openai_memory_chats').select('response_id').eq('session_id', session_id).not_.is_('response_id', 'null').order('order', desc=True).limit(1).execute()
        if result.data and result.data[0]['response_id']:
            return result.data[0]['response_id']
        return None
    except Exception as e:
        print(f"Error getting latest response_id: {e}")
        return None

def store_response_id_for_session(session_id, response_id):
    """Store a response_id for the most recent message in a session."""
    try:
        # Get the most recent message for this session
        result = supabase.table('openai_memory_chats').select('id').eq('session_id', session_id).order('order', desc=True).limit(1).execute()
        if result.data:
            message_id = result.data[0]['id']
            # Update the message with the response_id
            supabase.table('openai_memory_chats').update({'response_id': response_id}).eq('id', message_id).execute()
    except Exception as e:
        print(f"Error storing response_id: {e}")

# ---------------------------------------------------------------------------
# Session and Message Persistence Endpoints
# ---------------------------------------------------------------------------

@app.route('/api/sessions', methods=['POST'])
def create_session():
    """Create a new chat session and return the session ID."""
    try:
        session_id = str(uuid.uuid4())
        return jsonify({'session_id': session_id}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/sessions', methods=['GET'])
def get_sessions():
    """Get all chat sessions with their metadata."""
    try:
        # Get unique sessions with their latest message timestamp
        result = supabase.table('openai_memory_chats').select('session_id, timestamp').execute()
        
        if not result.data:
            return jsonify({'sessions': []})
        
        # Group by session_id and get the latest timestamp for each
        sessions = {}
        for message in result.data:
            session_id = message['session_id']
            timestamp = message['timestamp']
            if session_id not in sessions or timestamp > sessions[session_id]['last_activity']:
                sessions[session_id] = {
                    'session_id': session_id,
                    'last_activity': timestamp
                }
        
        # Convert to list and sort by last activity (newest first)
        sessions_list = list(sessions.values())
        sessions_list.sort(key=lambda x: x['last_activity'], reverse=True)
        
        return jsonify({'sessions': sessions_list})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/sessions/<session_id>/messages', methods=['GET'])
def get_session_messages(session_id):
    """Get all messages for a specific session."""
    try:
        result = supabase.table('openai_memory_chats').select('*').eq('session_id', session_id).order('order').execute()
        return jsonify({'messages': result.data})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/sessions/<session_id>/messages', methods=['POST'])
def save_message(session_id):
    """Save a message to the database."""
    try:
        payload = request.get_json(force=True)
        content = payload.get('content')
        message_type = payload.get('type', 'user')  # 'user' or 'assistant'
        response_id = payload.get('response_id')  # Optional response_id
        
        if not content:
            return jsonify({'error': 'Content is required'}), 400
        
        # Get the next order number for this session
        order_result = supabase.table('openai_memory_chats').select('order').eq('session_id', session_id).order('order', desc=True).limit(1).execute()
        next_order = 1
        if order_result.data:
            next_order = order_result.data[0]['order'] + 1
        
        # Insert the message
        message_data = {
            'session_id': session_id,
            'content': content,
            'order': next_order,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Add response_id if provided
        if response_id:
            message_data['response_id'] = response_id
        
        result = supabase.table('openai_memory_chats').insert(message_data).execute()
        
        if result.data:
            return jsonify({'message_id': result.data[0]['id']}), 201
        else:
            return jsonify({'error': 'Failed to save message'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/sessions/<session_id>', methods=['DELETE'])
def delete_session(session_id):
    """Delete a chat session and all its messages."""
    try:
        # Delete all messages for this session
        result = supabase.table('openai_memory_chats').delete().eq('session_id', session_id).execute()
        return jsonify({'deleted': True}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ---------------------------------------------------------------------------
# Static file delivery for original docs (local mode)
# ---------------------------------------------------------------------------


@app.route('/doc/<path:subpath>')
def doc(subpath: str):
    """Serve files from the documents folder while preventing path traversal.

    We allow nested paths such as `policies/handbook.pdf` but reject absolute
    paths or any component that attempts to traverse outside `DOC_DIR`.
    """
    from flask import abort
    import os

    safe_path = Path(subpath)

    # Reject absolute paths or any ".." traversal
    if safe_path.is_absolute() or any(part in ("..", "") for part in safe_path.parts):
        abort(400)

    # Check if file exists
    full_path = DOC_DIR / safe_path
    if not full_path.exists():
        # List what files ARE available for debugging
        available_files = []
        try:
            for root, dirs, files in os.walk(DOC_DIR):
                for file in files:
                    rel_path = os.path.relpath(os.path.join(root, file), DOC_DIR)
                    available_files.append(rel_path)
        except:
            pass
        
        error_msg = f"File not found: {subpath}\n\nAvailable files:\n" + "\n".join(available_files[:10])
        return error_msg, 404

    return send_from_directory(DOC_DIR, str(safe_path), as_attachment=False)


if __name__ == '__main__':
    # Production NOTE: use a proper WSGI server. For local demo, Flask is fine.
    app.run(host='127.0.0.1', port=5000, debug=False) 