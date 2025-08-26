import os
import json
import ssl
from typing import Dict, List, Optional, Any, Tuple
import psycopg2
from psycopg2.extras import RealDictCursor
import openai
import urllib3
import requests  # Added for Groq HTTP requests
from dotenv import load_dotenv, find_dotenv
import pathlib
from datetime import datetime
import urllib3
from supabase import create_client  # NEW – Supabase Storage

# Connected to documents database (documents are vector stored)

class RAGService:
    """
    Simple Retrieval-Augmented Generation service.
    
    1. Embed the question with OpenAI.            (text-embedding-3-small)
    2. Hybrid search (vector + full-text) over `document_chunks`.
    3. If results exist, optionally ask GPT-4o-mini to answer using the context.
    
    Environment variables expected:
      DATABASE_URL         — Postgres connection string
      OPENAI_API_KEY       — OpenAI key; if missing we fall back to returning the best chunk as the answer
      IGNORE_TLS_ERRORS    — Set to '1' to ignore TLS validation (development only)
      NODE_ENV             — Environment setting
    """
    
    EMBED_MODEL = 'text-embedding-3-small'
    MAX_CHUNKS = 20
    
    def __init__(self):
        # Load .env file if present
        load_dotenv(override=True)

        # Fallback: parse key=value lines at bottom of Requirements.txt (local dev)
        self._load_env_from_requirements()

        os.environ['OPENAI_API_KEY']

        self.database_url = os.environ['DATABASE_URL']
        self.openai_api_key = os.environ['OPENAI_API_KEY']
        self.ignore_tls_errors = os.getenv('IGNORE_TLS_ERRORS') == '1'
        self.node_env = os.getenv('NODE_ENV', 'development')

        # ------------------------------------------------------------------
        # Supabase (optional) - allows for cloud document storage and access
        # ------------------------------------------------------------------
        self.supabase_url = os.environ['SUPABASE_URL']
        # Prefer service-role for signed URLs; fall back to anon/public key
        self.supabase_key = (
            os.getenv('SUPABASE_SERVICE_ROLE_KEY')
            or os.getenv('SUPABASE_KEY')
            or os.getenv('SUPABASE_ANON_KEY')
        )

        self.supabase = None
        if self.supabase_url and self.supabase_key:
            try:
                self.supabase = create_client(self.supabase_url, self.supabase_key)
            except Exception as exc:
                print(f"[WARN] Failed to init Supabase client: {exc}")
        
        # ------------------------------------------------------------------
        # Groq (optional)
        # ------------------------------------------------------------------
        # Optional Groq configuration (https://console.groq.com). If the
        # environment variable is not present we fall back to the key that
        # you provided during setup so the service "just works" without extra
        # steps. IMPORTANT: Hard-coding secrets is not recommended for real
        # production deployments.
        self.groq_api_key = os.getenv(
            'GROQ_API_KEY'
        )
        # Default to the model the user referenced; override via env if desired
        self.groq_chat_model = os.getenv(
            'GROQ_CHAT_MODEL',
            'meta-llama/llama-4-scout-17b-16e-instruct',
        )
        
        if not self.database_url:
            raise ValueError('DATABASE_URL env var not set')
            
        self.openai_client = self._create_openai_client()
    
    def _create_openai_client(self) -> Optional[openai.OpenAI]:
        """
        Helper that creates an OpenAI client which ignores TLS validation issues when the
        environment variable IGNORE_TLS_ERRORS is set (e.g. behind a corporate proxy with
        a self-signed certificate). In production this flag should never be enabled.
        """
        if not self.openai_api_key:
            return None
        
        # If the user explicitly opts-in, relax TLS rules for the OpenAI SDK.
        # This prevents the "self-signed certificate in certificate chain" error when
        # developing behind proxies that intercept HTTPS traffic.
        relax_tls = self.ignore_tls_errors or self.node_env != 'production'
        
        if relax_tls:
            # Disable SSL warnings and create unverified context
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            
            # Create custom HTTP client that ignores SSL verification
            import httpx
            http_client = httpx.Client(verify=False)
            
            return openai.OpenAI(
                api_key=self.openai_api_key,
                http_client=http_client
            )
        
        # Default: strict TLS (recommended for prod)
        return openai.OpenAI(api_key=self.openai_api_key)
    
    # Connect to postgres database
    def _get_db_connection(self) -> psycopg2.extensions.connection:
        """Create database connection with appropriate SSL settings."""
        conn_params = psycopg2.extensions.parse_dsn(self.database_url)
        
        # Handle SSL configuration
        if self.ignore_tls_errors or self.node_env != 'production':
            conn_params['sslmode'] = 'require'
            conn_params['sslcert'] = None
            conn_params['sslkey'] = None
            conn_params['sslrootcert'] = None
        
        return psycopg2.connect(**conn_params)
    
    # Index question
    async def _embed_question(self, question: str) -> Optional[List[float]]:
        """Embed the question using OpenAI's embedding model."""
        if not self.openai_client:
            return None
        
        try:
            response = self.openai_client.embeddings.create(
                model=self.EMBED_MODEL,
                input=question
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"Error embedding question: {e}")
            return None
    
    # Retrieval
    def _vector_search(self, conn: psycopg2.extensions.connection, 
                      query_vec: List[float], question: str) -> List[Dict[str, Any]]:
        """Perform vector similarity search with full-text ranking."""
        vector_sql = """
        WITH q AS (
            SELECT
                %s::vector                         AS vec,
                plainto_tsquery('english', %s)     AS tsq
        )
        SELECT
            d.bucket,
            d.object_path,
            d.filename,
            COALESCE(cp.text, '')                 AS prev,
            c.text                                AS cur,
            COALESCE(cn.text, '')                 AS nxt,
            (c.embedding <=> q.vec)               AS distance,
            ts_rank(c.tsv, q.tsq)                 AS rank,
            c.document_id,
            c.chunk_index
        FROM   public.document_chunks c
        LEFT JOIN public.document_chunks cp ON cp.document_id = c.document_id AND cp.chunk_index = c.chunk_index - 1
        LEFT JOIN public.document_chunks cn ON cn.document_id = c.document_id AND cn.chunk_index = c.chunk_index + 1
        JOIN   public.documents d ON d.id = c.document_id
        CROSS JOIN q
        WHERE  c.embedding IS NOT NULL
        ORDER  BY distance ASC, rank DESC
        LIMIT  %s;
        """
        
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(vector_sql, [json.dumps(query_vec), question, self.MAX_CHUNKS])
            return [dict(row) for row in cursor.fetchall()]
    
    def _text_search(self, conn: psycopg2.extensions.connection, 
                    question: str) -> List[Dict[str, Any]]:
        """Perform full-text search as fallback."""
        text_sql = """
        WITH q AS (
            SELECT plainto_tsquery('english', %s) AS tsq
        )
        SELECT
            d.bucket,
            d.object_path,
            d.filename,
            COALESCE(cp.text, '')                 AS prev,
            c.text                                AS cur,
            COALESCE(cn.text, '')                 AS nxt,
            NULL                                  AS distance,
            ts_rank(c.tsv, q.tsq)                 AS rank,
            c.document_id,
            c.chunk_index
        FROM   public.document_chunks c
        LEFT JOIN public.document_chunks cp ON cp.document_id = c.document_id AND cp.chunk_index = c.chunk_index - 1
        LEFT JOIN public.document_chunks cn ON cn.document_id = c.document_id AND cn.chunk_index = c.chunk_index + 1
        JOIN   public.documents d ON d.id = c.document_id
        CROSS JOIN q
        WHERE  c.tsv @@ q.tsq
        ORDER  BY rank DESC
        LIMIT  %s;
        """
        
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(text_sql, [question, self.MAX_CHUNKS])
            return [dict(row) for row in cursor.fetchall()]
    
    # Generation
    def _generate_answer(self, question: str, context: str) -> str:
        """Generate answer using OpenAI's chat completion."""
        system_prompt = (
            "You are an HR assistant. Answer the user's question strictly based on the context "
            "provided below. Cite facts with the bracketed numbers that precede each context "
            "chunk (e.g., [1], [2]). If the context does not contain the answer, reply: "
            "'I don't know based on the documents.'"
        )

        # ------------------------------------------------------------------
        # 1) Prefer Groq if GROQ_API_KEY is configured
        # ------------------------------------------------------------------
        if self.groq_api_key:
            answer = self._generate_answer_groq(system_prompt, question, context)
            if answer:
                return answer

        # ------------------------------------------------------------------
        # 2) Fallback to OpenAI
        # ------------------------------------------------------------------
        if not self.openai_client:
            return "OpenAI API key not configured."

        try:
            response = self.openai_client.chat.completions.create(
                model='gpt-4o-mini',
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Question: {question}\n\nContext:\n{context}"}
                ],
                temperature=0.2
            )
            return (
                response.choices[0].message.content.strip()
                if response.choices and response.choices[0].message.content
                else "I don't know based on the documents."
            )
        except Exception as e:
            print(f"Error generating answer (OpenAI): {e}")
            return "I don't know based on the documents."

    # ------------------------------------------------------------------
    # Groq helper
    # ------------------------------------------------------------------
    def _generate_answer_groq(
        self, system_prompt: str, question: str, context: str
    ) -> Optional[str]:
        """Generate answer using Groq's OpenAI-compatible chat API."""

        if not self.groq_api_key:
            return None

        url = "https://api.groq.com/openai/v1/chat/completions"
        payload = {
            "model": self.groq_chat_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Question: {question}\n\nContext:\n{context}"},
            ],
            "temperature": 0.2,
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.groq_api_key}",
        }

        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            if (
                data.get("choices")
                and isinstance(data["choices"], list)
                and data["choices"][0]["message"].get("content")
            ):
                return data["choices"][0]["message"]["content"].strip()
        except Exception as exc:
            print(f"Error generating answer (Groq): {exc}")

        return None
    
    def answer_question(self, question: str) -> Dict[str, Any]:
        """
        Main method to answer a question using RAG.
        
        Returns:
            Dict containing 'answer' and 'references'
        """
        verbose = os.getenv("RAG_VERBOSE") == "1"

        # 1. Indexing - Embed the question (if we have an API key)
        query_vec = None
        if self.openai_client:
            # Note: In a real async environment, you'd use await here
            # For this sync version, we'll call the sync method
            try:
                response = self.openai_client.embeddings.create(
                    model=self.EMBED_MODEL,
                    input=question
                )
                query_vec = response.data[0].embedding
                if verbose:
                    print(f"[DEBUG] Obtained question embedding of length {len(query_vec)}")
            except Exception as e:
                print(f"Error embedding question: {e}")
        
        # 2. Retrieval - Hybrid search in Postgres
        conn = self._get_db_connection()
        
        try:
            hits = []
            
            if query_vec:
                hits = self._vector_search(conn, query_vec, question)
                if verbose:
                    print(f"[DEBUG] Vector search returned {len(hits)} rows")
            
            # If we didn't run vector search or got no hits, run full-text search
            if not hits:
                hits = self._text_search(conn, question)
                if verbose:
                    print(f"[DEBUG] Full-text search returned {len(hits)} rows")
            
        finally:
            conn.close()
        
        if not hits:
            return {
                "answer": "I don't know based on the documents.",
                "references": []
            }
        
        import os as _os
        # Build context blobs -- ensure we only surface the base filename so the
        # generated /doc links remain relative to the `documents/` folder even if
        # the database row contains an absolute or nested path.

        context_blobs = []
        for i, hit in enumerate(hits):
            base_name = _os.path.basename(hit.get('filename', 'document'))
            blob = f"{hit['prev']} {hit['cur']} {hit['nxt']}".strip()
            context_blobs.append(f"[{i + 1}] ({base_name})\n{blob}")
        
        joined_context = '\n---\n'.join(context_blobs)
        
        # 3. Generation - Generate answer (if API key)
        if self.openai_client:
            answer = self._generate_answer(question, joined_context)
            if verbose:
                print("[DEBUG] GPT-4 response produced.")
        else:
            # Fallback: show the highest-ranked chunk
            answer = hits[0]['cur']
        
        # Build references – ensure unique sources and align with [n] identifiers
        seen = set()
        references = []
        for i, hit in enumerate(hits):
            key = (hit['document_id'], hit['chunk_index'])
            if key in seen:
                continue  # Skip duplicates
            seen.add(key)

            # Build a link – prefer Supabase signed URL if possible
            supa_url = self._signed_file_url(hit.get('bucket'), hit.get('object_path'))
            
            if supa_url:
                # Use Supabase URL
                base_link = supa_url
            else:
                # Fallback to local filename - but warn user
                base_link = base_name
                if hit.get('bucket') and hit.get('object_path'):
                    print(f"[WARN] Supabase Storage unavailable for {hit.get('bucket')}/{hit.get('object_path')}, using local fallback")

            references.append({
                "index": i + 1,  # Corresponds to the [n] tag in context
                "id": f"doc-{hit['document_id']}-chunk-{hit['chunk_index']}",
                "source": f"{base_link}#{hit['chunk_index']}",
                "snippet": hit['cur']
            })
        
        return {
            "answer": answer,
            "references": references
        }

    # ---------------------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------------------

    @staticmethod
    def _load_env_from_requirements(path: str = 'Requirements.txt') -> None:
        """Populate os.environ with KEY=VALUE pairs found in *Requirements.txt*.

        The project keeps a handful of environment variables (e.g. DATABASE_URL,
        OPENAI_API_KEY) at the bottom of *Requirements.txt*. This helper looks
        for lines that contain an '=' but **not** the typical version specifier
        patterns ('>=', '=='), then exports them to the current process env if
        they are not already set.
        """
        if not os.path.exists(path):
            return  # Nothing to do

        try:
            with open(path, 'r', encoding='utf-8') as fh:
                for raw in fh:
                    line = raw.strip()

                    # Ignore empty lines or comments
                    if not line or line.startswith('#'):
                        continue

                    # Skip dependency specifiers such as "package>=1.0.0" or "pkg==2.1.0"
                    if '==' in line or '>=' in line:
                        continue

                    if '=' in line:
                        key, val = line.split('=', 1)
                        key, val = key.strip(), val.strip()

                        # Only set if not already defined; respect real env vars
                        if key and (key not in os.environ):
                            os.environ[key] = val
        except Exception as exc:
            # Fail silently but give a hint for debugging
            print(f"[WARN] Failed to parse env vars from {path}: {exc}")

    # ---------------------------------------------------------------------
    # Bulk embedding helper
    # ---------------------------------------------------------------------

    def embed_missing_chunks(self, batch_size: int = 100) -> None:
        """Generate embeddings for chunks whose embedding column is NULL and save them.

        Processes the table in batches (default 100 rows) to stay within token and
        rate-limit budgets. Call via the CLI flag `--embed-missing`.
        """
        if not self.openai_client:
            print("[ERROR] OPENAI_API_KEY is not configured; cannot embed chunks.")
            return

        conn = self._get_db_connection()
        updated = 0

        try:
            while True:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT id, text
                        FROM   public.document_chunks
                        WHERE  embedding IS NULL
                        LIMIT  %s
                        """,
                        [batch_size],
                    )
                    rows = cur.fetchall()

                if not rows:
                    break

                ids, texts = zip(*rows)

                try:
                    response = self.openai_client.embeddings.create(
                        model=self.EMBED_MODEL,
                        input=list(texts),
                    )
                except Exception as exc:
                    print(f"[ERROR] Failed to create embeddings: {exc}")
                    break

                vectors = [e.embedding for e in response.data]

                with conn.cursor() as cur:
                    for chunk_id, vec in zip(ids, vectors):
                        cur.execute(
                            "UPDATE public.document_chunks SET embedding = %s WHERE id = %s",
                            [json.dumps(vec), chunk_id],
                        )
                conn.commit()

                updated += len(ids)
                print(f"[INFO] Embedded {updated} chunks so far…")

        finally:
            conn.close()

        print(f"[DONE] Embedded {updated} chunks in total.")

    # ------------------------------------------------------------------
    # Supabase helpers
    # ------------------------------------------------------------------

    def _signed_file_url(self, bucket: str, object_path: str, expires: int = 3600) -> Optional[str]:
        """Return a public URL to an object in Supabase Storage.

        For public buckets, constructs a direct public URL.
        If that fails, fall back to local file serving.
        """
        bucket = "documents"
        
        if not bucket or not object_path:
            return None

        # Get Supabase URL from environment
        supabase_url = os.getenv('SUPABASE_URL')
        if not supabase_url:
            # No Supabase URL configured, fall back to local files
            return None

        try:
            # Construct public URL for public buckets
            # Format: https://PROJECT.supabase.co/storage/v1/object/public/BUCKET/PATH
            public_url = f"{supabase_url}/storage/v1/object/public/{bucket}/{object_path}"
            return public_url

        except Exception as e:
            print(f"[WARN] Failed to construct public URL: {e}")
            # Fall back to local file serving
            return None


# Example usage
def main():
    """CLI wrapper so users can easily ask questions. Usage:

    python important.py "What is the company's vacation policy?"

    If no argument is provided the script will enter an interactive prompt.
    """

    import argparse
    import textwrap

    parser = argparse.ArgumentParser(
        prog="important.py",
        description="Query the HR document knowledge-base using retrieval-augmented generation.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent(
            """Examples:
              python important.py "How many vacation days do interns get?"
              python important.py  # <- then enter your question interactively
            """
        ),
    )
    parser.add_argument("question", nargs="*", help="Question to ask the knowledge base")
    parser.add_argument(
        "-c", "--show-context", action="store_true", help="Print the full context that GPT-4o received"
    )
    parser.add_argument(
        "--embed-missing",
        action="store_true",
        help="Populate missing embeddings for rows in public.document_chunks",
    )
    parser.add_argument(
        "--ingest-json",
        metavar="PATH",
        help="Path to a JSON file to ingest into the database",
    )

    args = parser.parse_args()

    rag = RAGService()

    # ------------------------------------------------------------------
    # Option 1: Ingest JSON file then optionally embed and exit
    # ------------------------------------------------------------------
    if args.ingest_json:
        _ingest_json(rag, args.ingest_json)

        # Immediately embed the new chunks so the doc is searchable
        print("[INFO] Embedding newly ingested chunks…")
        rag.embed_missing_chunks()

        # Exit if this was a standalone ingest command
        if not args.question:
            return

    # ------------------------------------------------------------------
    # Option 2: Populate missing embeddings then exit
    # ------------------------------------------------------------------
    if args.embed_missing:
        rag.embed_missing_chunks()
        return

    # ------------------------------------------------------------------
    # Option 3: Normal Q&A flow
    # ------------------------------------------------------------------

    # Build the question string either from CLI args or by prompting the user
    if args.question:
        question = " ".join(args.question).strip()
    else:
        try:
            question = input("Enter your question: ").strip()
        except EOFError:
            print("No question provided; exiting.")
            return

    if not question:
        print("No question provided; exiting.")
        return

    result = rag.answer_question(question)

    print("\nAnswer:\n", result["answer"])
    if args.show_context:
        print("\n---\nContext given to GPT-4o:")
        for ref in result["references"]:
            print(f"[{ref['source']}]\n{ref['snippet']}\n")

    if result["references"]:
        print("\nReferences:")
        for ref in result["references"]:
            # Show up to first 120 chars of the snippet for context
            snippet_preview = ref["snippet"].replace("\n", " ")[:120]
            print(f"- {ref['source']}: {snippet_preview}...")
    else:
        print("\n(No document references found)")


def _ingest_json(rag: "RAGService", json_path: str, chunk_size: int = 1000) -> None:
    """Simple helper that reads a JSON file, flattens it into text, and stores
    it (chunked) inside the `documents` / `document_chunks` tables.

    The JSON is pretty-printed with newlines so each key/value pair becomes
    readable context for retrieval.  Adjust `chunk_size` (in characters) if
    you want larger or smaller chunks.
    """
    p = pathlib.Path(json_path)
    if not p.exists():
        print(f"[ERROR] File not found: {json_path}")
        return

    try:
        with open(p, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except Exception as exc:
        print(f"[ERROR] Failed to read JSON: {exc}")
        return

    # Pretty-print so values and nested objects are readable lines
    pretty = json.dumps(data, indent=2, ensure_ascii=False)

    # Chunk by characters (naive but effective for plain-text retrieval)
    chunks = [
        pretty[i : i + chunk_size]
        for i in range(0, len(pretty), chunk_size)
    ]

    conn = rag._get_db_connection()
    try:
        with conn.cursor() as cur:
            # Insert into documents table – return id
            # The original file will be served by the Flask /doc route which looks for
            # files under the local `documents` directory.  Copy the source file there
            # (if it is not already present) and store **only** the basename so the
            # generated links match the actual on-disk location.

            import shutil  # local import to avoid adding a global dependency

            docs_dir = pathlib.Path("documents")
            docs_dir.mkdir(exist_ok=True)

            filename = p.name  # e.g. "handbook.json" or "policy.pdf"

            # 5a) Upload to Supabase Storage (optional)
            if rag.supabase:
                try:
                    bucket = "uploads"
                    with open(p, "rb") as fh_bin:
                        rag.supabase.storage.from_(bucket).upload(filename, fh_bin.read(), upsert=True)
                    # Supabase uses key == path; we store that as object_path
                    object_path_val = filename
                except Exception as up_exc:
                    print(f"[WARN] Failed to upload to Supabase: {up_exc}")
                    object_path_val = str(p)
            else:
                object_path_val = str(p)

            # 5b) Copy to local documents folder for offline dev
            dest_path = docs_dir / filename
            if not dest_path.exists():
                try:
                    shutil.copy(p, dest_path)
                except Exception as copy_exc:
                    print(f"[WARN] Failed to copy file to {dest_path}: {copy_exc}")

            cur.execute(
                """
                INSERT INTO public.documents (bucket, object_path, filename, mime_type, size_bytes, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                [
                    "uploads",            # bucket
                    object_path_val,       # object path inside bucket (or local path fallback)
                    filename,              # display name
                    "application/json",  # mime-type
                    p.stat().st_size,
                    datetime.utcnow(),
                ],
            )
            doc_id = cur.fetchone()[0]

            for idx, text_chunk in enumerate(chunks):
                start_pos = idx * chunk_size
                end_pos = start_pos + len(text_chunk)
                cur.execute(
                    """
                    INSERT INTO public.document_chunks (document_id, chunk_index, start_char, end_char, tokens, text)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    [doc_id, idx, start_pos, end_pos, len(text_chunk.split()), text_chunk],
                )

        conn.commit()
        print(f"[DONE] Ingested {len(chunks)} chunks into document ID {doc_id}.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()