from openai import OpenAI
import os
from dotenv import load_dotenv, find_dotenv

load_dotenv(override=True)
client = OpenAI(api_key=os.environ['OPENAI_API_KEY'])

CLOUD_RUN_URL = "https://test-mcp-server-3-82241824210.us-central1.run.app/mcp/" # "https://test-mcp-server-82241824210.us-central1.run.app/mcp/" # "http://localhost:8080", "https://mcp-server-xtjhu227ga-uc.a.run.app", "https://mcp-server-82241824210.us-central1.run.app"

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