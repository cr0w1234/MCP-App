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
    input="Give me the list the available tools in my mcp server in json format. how many documents are in the demo database in the documents table. let me know which tool you called)?",


)

print(resp.output_text)