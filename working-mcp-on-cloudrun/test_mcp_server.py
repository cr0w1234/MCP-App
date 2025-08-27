import asyncio
import os
from fastmcp import Client

async def test_server():
    # Test the MCP server using streamable-http transport.
    # Use "/sse" endpoint if using sse transport.
    load_dotenv(override=True)
    MCP_SERVER_URL = os.getenv('MCP_SERVER_URL', 'http://localhost:8080/mcp/')
    
    async with Client(MCP_SERVER_URL) as client:
        # List available tools
        tools = await client.list_tools()
        for tool in tools:
            print(f">>> 🛠️  Tool found: {tool.name}")
        # Call add tool
        print(">>> 🪛  Calling add tool for 1 + 2")
        result = await client.call_tool("add", {"a": 1, "b": 2})
        print(result)
        print(f"<<< ✅ Result: {result[0].text}")

        # Call subtract tool
        print(">>> 🪛  Calling subtract tool for 10 - 3")
        result = await client.call_tool("subtract", {"a": 10, "b": 3})
        print(f"<<< ✅ Result: {result[0].text}")

        # Call query_demo_db tool
        print(">>> 🪛  Calling query_demo_db tool for counting number of documents")
        result = await client.call_tool("query_demo_db", {"sql": "SELECT COUNT(*) as document_count FROM documents;"})
        print(f"<<< ✅ Result: {result[0].text}")

        # Call tmdb_intelligent_call tool
        print(">>> 🪛  Calling tmdb_intelligent_call tool for searching for Inception")
        result = await client.call_tool("tmdb_intelligent_call", {"request": "Search for Inception"})
        print(f"<<< ✅ Result: {result[0].text}")
        result = await client.call_tool("tmdb_intelligent_call", {"request": "Get popular movies"})
        print(f"<<< ✅ Result: {result[0].text}")

        # Call http_get tool
        print(">>> 🪛  Calling http_get tool for getting popular movies")
        result = await client.call_tool("http_get", {"url": "https://api.themoviedb.org/3/movie/popular?api_key=5b039ea0afb5076e4e73b46c912a6b77"})
        print(f"<<< ✅ Result: {result[0].text}")


if __name__ == "__main__":
    asyncio.run(test_server())

