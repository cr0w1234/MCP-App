from openai import OpenAI
import os
from dotenv import load_dotenv, find_dotenv

load_dotenv(override=True)
client = OpenAI(api_key=os.environ['OPENAI_API_KEY'])

CLOUD_RUN_URL = os.getenv('MCP_SERVER_URL', 'http://localhost:8080/mcp/')

# test_mcp_server
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
    input="Give me the list the available tools in my mcp server in json format. call the add tool on 1 and 2. now call the subtract tool on 2 and 3. how many documents are in the demo database in the documents table (also return the sql query you ran, and if there is an error ,let me know what the error is)? call the tmdb_intelligent_call tool to search for Inception",


)

print(resp.output_text)