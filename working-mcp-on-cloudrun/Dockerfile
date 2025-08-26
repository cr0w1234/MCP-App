# Use the official Python image
FROM python:3.13-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install the project into /app
COPY . /app
WORKDIR /app

# Allow statements and log messages to immediately appear in the logs
ENV PYTHONUNBUFFERED=1
ENV TMDB_API_KEY=5b039ea0afb5076e4e73b46c912a6b77
ENV TMDB_ACCOUNT_ID=22184932
ENV TMDB_SESSION_ID=7bb02c73e85cfb294516354febeff557
ENV DATABASE_URL=postgresql://readonly.cvzlylxhvthjvmjuluqe:5abEF039ea0af@aws-0-us-east-1.pooler.supabase.com:5432/postgres


# Install dependencies
RUN uv sync

EXPOSE 8080

# Run the FastMCP server
CMD ["uv", "run", "readonly-db-mcp-server.py"]