import asyncio
import logging
import os
from fastmcp import FastMCP 
import json
import re
from typing import Any, Dict, List, Optional
import urllib.parse
import urllib.request
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)
logging.basicConfig(format="[%(levelname)s]: %(message)s", level=logging.INFO)

mcp = FastMCP("MCP Server on Cloud Run", stateless_http=True)

load_dotenv(override=True)

# Database configuration
from psycopg2.pool import SimpleConnectionPool
import threading

DB_URL = os.getenv('DATABASE_URL')

# Connection pool for better connection management
connection_pool = None
pool_lock = threading.Lock()


@mcp.tool()
def pg_query(sql: str) -> str:
    """Execute SQL queries against the Demo PostgreSQL database"""
    if not sql or not sql.strip():
        raise ValueError("SQL query is required")
    
    conn = None
    cursor = None
    
    try:
        # Get connection from pool
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("BEGIN READ ONLY")
        cursor.execute(sql)
        
        # Enhanced read-only validation
        sql_upper = sql.strip().upper()

        results = cursor.fetchall()
        cursor.execute("COMMIT")

        json_results = []
        for row in results:
            json_results.append(dict(row))
        
        return json.dumps(json_results, indent=2, default=str)

    except Exception as e:
        if conn:
            conn.rollback()
        raise e
    finally:
        if cursor:
            cursor.close()
        if conn:
            return_db_connection(conn)

@mcp.tool()
def pg_explain(sql: str) -> List[Dict[str, Any]]:
    """Return EXPLAIN (FORMAT JSON) for a query as JSON from PostgreSQL."""
    
    # Describes the query and returns the explanation as JSON, without actually executing the query
    if not sql or not sql.strip():
        raise ValueError("SQL query is required")

    # Allow any statement but wrap with EXPLAIN

    explain_query = f"EXPLAIN (FORMAT JSON) {sql}"

    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("BEGIN READ ONLY")
        cur.execute(explain_query)
        result = _fetch_all_dicts(cur)
        cur.execute("COMMIT")
        return result
    except Exception as e:
        logger.error(f"pg_explain error: {e}")
        raise
    finally:
        if cur:
            try:
                cur.close()
            except Exception:
                pass
        if conn:
            return_db_connection(conn)


def get_db_connection():
    """Get a database connection from the pool"""
    global connection_pool
    
    with pool_lock:
        if connection_pool is None:
            initialize_connection_pool()
        
        try:
            conn = connection_pool.getconn()
            # Test if connection is still valid
            conn.cursor().execute("SELECT 1")
            return conn
        except Exception as e:
            logger.warning(f"Connection from pool failed, creating new one: {e}")
            # If connection is bad, create a new one
            conn_params = psycopg2.extensions.parse_dsn(DB_URL)
            return psycopg2.connect(**conn_params)

def return_db_connection(conn):
    """Return a database connection to the pool"""
    global connection_pool
    
    try:
        if connection_pool is not None:
            connection_pool.putconn(conn)
        else:
            conn.close()
    except Exception as e:
        logger.warning(f"Error returning connection to pool: {e}")
        try:
            conn.close()
        except:
            pass

def initialize_connection_pool():
    """Initialize the database connection pool"""
    global connection_pool
    
    try:
        conn_params = psycopg2.extensions.parse_dsn(DB_URL)
        # Create a pool with 5-20 connections
        connection_pool = SimpleConnectionPool(5, 20, **conn_params)
        logger.info("Database connection pool initialized")
    except Exception as e:
        logger.error(f"Failed to initialize connection pool: {e}")
        raise

def cleanup_connection_pool():
    """Clean up the database connection pool"""
    global connection_pool
    
    if connection_pool:
        connection_pool.closeall()
        logger.info("Database connection pool closed")

def _ensure_select_only(sql: str) -> None:
    """Ensure the SQL is a single, read-only statement.

    - Must start with SELECT or WITH
    - Forbid semicolons to prevent multiple statements
    """
    sql_stripped = sql.strip()
    upper = sql_stripped.upper()
    if not (upper.startswith("SELECT") or upper.startswith("WITH")):
        raise ValueError("Only SELECT/CTE queries are allowed (read-only).")
    if ";" in sql_stripped:
        raise ValueError("Multiple statements are not allowed.")

def _fetch_all_dicts(cur) -> List[Dict[str, Any]]:
    rows = cur.fetchall()
    return [dict(row) for row in rows]


if __name__ == "__main__":
    # Initialize connection pool on startup
    initialize_connection_pool()
    logger.info(f"🚀 MCP server started on port {os.getenv('PORT', 8080)}")
    
    try:
        # Could also use 'sse' transport, host="0.0.0.0" required for Cloud Run.
        asyncio.run(
            mcp.run_async(
                transport="streamable-http",
                host="0.0.0.0",
                port=os.getenv("PORT", 8080),
            )
        )
    finally:
        # Clean up connection pool on shutdown
        cleanup_connection_pool()