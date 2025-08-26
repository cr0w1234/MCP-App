from flask import Flask, request, jsonify, render_template_string, send_from_directory
from pathlib import Path

from rag_system import RAGService
# from hybrid_service import HybridRAGEmailService

app = Flask(__name__)
rag_service = RAGService()
# hybrid_service = HybridRAGEmailService()

# Directory where original documents (PDF, DOCX, etc.) reside. Update as needed.
DOC_DIR = Path("documents")  # make sure this folder exists and contains the source files

HTML_PAGE = """
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8" />
    <title>RAG Q&A Demo</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .container { max-width: 960px; margin: 0 auto; }
        textarea { width: 100%; padding: 10px; font-size: 1rem; resize: vertical; }
        button { padding: 8px 18px; font-size: 1rem; margin-top: 8px; }
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
    </style>
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
</head>
<body>
<div class="container">
  <h2>Ask a question</h2>
  <form id="qa-form" onsubmit="return false;">
    <textarea id="question" rows="3" placeholder="Type your question here"></textarea>
    <br />
    <button onclick="submitQ()">Ask</button>
    <button onclick="submitMCP()">MCP Search</button>
  </form>
  <div id="conversation"></div>
</div>

<script>
let conversationHistory = [];

function addMessage(role, content, type = 'regular') {
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
    body: JSON.stringify({ question })
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
    if not question:
        return jsonify({'error': 'No question provided'}), 400

    from openai import OpenAI
    import os
    import logging
    from dotenv import load_dotenv, find_dotenv

    # Configure logging for Google Cloud
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    load_dotenv(override=True)
    client = OpenAI(api_key=os.environ['OPENAI_API_KEY'])

    CLOUD_RUN_URL = "https://test-mcp-server-4-82241824210.us-central1.run.app/mcp/" # "https://test-mcp-server-4-82241824210.us-central1.run.app/mcp/" # not read only: "https://test-mcp-server-3-82241824210.us-central1.run.app/mcp/" # "https://test-mcp-server-82241824210.us-central1.run.app/mcp/" # "http://localhost:8080", "https://mcp-server-xtjhu227ga-uc.a.run.app", "https://mcp-server-82241824210.us-central1.run.app"

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

    # test_mcp_server
    resp = client.responses.create(
        model="gpt-4.1",
        tools=[
            {
                "type": "mcp",
                "server_label": "test_mcp_server",
                "server_url": CLOUD_RUN_URL,
                "allowed_tools":[
                    "query_demo_db"
                ],
                "require_approval": "never",
            },
        ],
        input=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"}
        ],
        previous_response_id=current_response_id,
    )
    current_response_id = resp.id

    # input = question

    '''# Log the tool calls and their details
    if hasattr(resp, 'tool_calls') and resp.tool_calls:
        logger.info(f"Tool calls executed: {len(resp.tool_calls)}")
        for i, tool_call in enumerate(resp.tool_calls):
            logger.info(f"Tool call {i+1}: {tool_call.function.name}")
            if hasattr(tool_call, 'function') and hasattr(tool_call.function, 'arguments'):
                logger.info(f"Tool call {i+1} arguments: {tool_call.function.arguments}")
    else:
        logger.info("No tool calls were executed")'''

    print(resp.output_text)
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