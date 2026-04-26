import os
import json
import uuid
import time
import logging
from typing import List, Dict, Any

from dotenv import load_dotenv
from google import genai
import chromadb

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# --- Constants ---
EMBEDDING_MODEL = "models/gemini-embedding-2"
ANALYSIS_MODEL  = "gemini-2.5-flash"
MAX_RETRIES     = 3
RETRY_BACKOFF   = 2    # seconds, doubles each retry

# Rate limiting for gemini-2.5-flash (1 RPM free tier).
# The guard enforces a 61-second gap between LLM calls automatically.
# Lower this if you upgrade to a paid tier (e.g. set to 5).
LLM_MIN_INTERVAL = 61  # seconds between calls — matches free tier 1 RPM

# Embedding batch settings (embedding model has its own separate quota).
EMBED_BATCH_SIZE  = 20
EMBED_BATCH_DELAY = 2.0


class JobSuitabilityAgent:
    def __init__(self, chroma_path: str = "./chroma_db"):
        self.api_key = os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")

        self.client = genai.Client(api_key=self.api_key)

        # Tracks when the last LLM call was made for the rate limit guard.
        # Start at 0 so the very first call is never delayed.
        self._last_llm_call: float = 0.0

        self.chroma_client = chromadb.PersistentClient(path=chroma_path)
        # Chat history collection
        try:
            self.collection = self.chroma_client.get_collection(name="chat_history")
            logger.info("Loaded chat_history collection.")
        except chromadb.errors.NotFoundError:
            self.collection = self.chroma_client.create_collection(name="chat_history")
            logger.info("Created chat_history collection.")

        # Analysis collection
        try:
            self.analysis_collection = self.chroma_client.get_collection(name="analysis_results")
            logger.info("Loaded analysis_results collection.")
        except chromadb.errors.NotFoundError:
            self.analysis_collection = self.chroma_client.create_collection(name="analysis_results")
            logger.info("Created analysis_results collection.")

    # ------------------------------------------------------------------
    # Rate Limit Guard
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_retry_delay(error: Exception) -> float:
        """
        Extract the server-recommended retry delay from a 429 error.

        The Gemini API includes a retryDelay field in the error details
        (e.g. '19.29s'). Using this value instead of our own backoff means
        we wait exactly as long as the server needs — no more, no less.
        Falls back to LLM_MIN_INTERVAL if parsing fails.
        """
        import re
        error_str = str(error)
        match = re.search(r"retryDelay.*?([0-9]+(?:\.[0-9]+)?)s", error_str)
        if match:
            return float(match.group(1)) + 2  # +2s buffer
        return float(LLM_MIN_INTERVAL)

    def _llm_call(self, prompt: str) -> str:
        """
        Call gemini-2.5-flash with a proactive rate-limit guard AND
        server-driven retry delays.

        Two-layer protection:
        1. PROACTIVE: checks time since last call before sending — prevents
           the request from being made if we're still within LLM_MIN_INTERVAL.
        2. REACTIVE: if a 429 arrives anyway (e.g. daily quota pressure),
           reads the server's own retryDelay from the error body and waits
           exactly that long before retrying. Our old fixed backoff (2s, 4s)
           was far shorter than the server's required wait (16-19s), which
           is why all 3 retries kept failing immediately.
        """
        elapsed = time.time() - self._last_llm_call
        if elapsed < LLM_MIN_INTERVAL:
            wait = LLM_MIN_INTERVAL - elapsed
            logger.info(f"Rate limit guard: waiting {wait:.0f}s before next LLM call...")
            time.sleep(wait)

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = self.client.models.generate_content(
                    model=ANALYSIS_MODEL,
                    contents=prompt
                )
                self._last_llm_call = time.time()
                return response.text
            except Exception as e:
                error_str = str(e)
                is_rate_limit = "429" in error_str or "RESOURCE_EXHAUSTED" in error_str

                if is_rate_limit:
                    wait = self._parse_retry_delay(e)
                    logger.warning(
                        f"Rate limit on attempt {attempt}. "
                        f"Server says wait {wait:.0f}s — honouring that delay..."
                    )
                else:
                    wait = float(RETRY_BACKOFF ** attempt)
                    logger.warning(f"LLM attempt {attempt} failed: {e}. Retrying in {wait:.0f}s...")

                if attempt < MAX_RETRIES:
                    time.sleep(wait)

        raise RuntimeError(f"LLM call failed after {MAX_RETRIES} retries.")

    # ------------------------------------------------------------------
    # Embedding
    # ------------------------------------------------------------------

    def get_embedding(self, text: str, task_type: str = "retrieval_query") -> List[float]:
        """Embed a single text. Embedding model has its own separate quota."""
        return self._embed_batch([text], task_type)[0]

    def _embed_batch(self, texts: List[str], task_type: str) -> List[List[float]]:
        """Embed multiple texts in ONE API call."""
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = self.client.models.embed_content(
                    model=EMBEDDING_MODEL,
                    contents=texts,
                    config={"task_type": task_type}
                )
                return [e.values for e in response.embeddings]
            except Exception as e:
                wait = RETRY_BACKOFF ** attempt
                logger.warning(f"Batch embed attempt {attempt} failed: {e}. Retrying in {wait}s...")
                time.sleep(wait)

        raise RuntimeError(f"Embedding failed after {MAX_RETRIES} retries.")

    # ------------------------------------------------------------------
    # Ingestion
    # ------------------------------------------------------------------

    def ingest_chat_history(self, json_path: str):
        """Load a ChatGPT export JSON and store all user messages in ChromaDB."""
        if not os.path.exists(json_path):
            raise FileNotFoundError(f"Chat history not found: {json_path}")

        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        logger.info(f"Ingesting {len(data)} conversations...")

        texts, ids, metadatas = [], [], []

        for conv in data:
            title   = conv.get("title", "Untitled")
            mapping = conv.get("mapping", {})

            for msg_id, node in mapping.items():
                msg = node.get("message")
                if not msg:
                    continue
                if msg.get("author", {}).get("role") != "user":
                    continue
                parts = msg.get("content", {}).get("parts", [])
                if not parts or not isinstance(parts[0], str):
                    continue
                text = parts[0].strip()
                if text:
                    texts.append(text)
                    ids.append(str(uuid.uuid4()))
                    metadatas.append({"chat_title": title, "role": "user"})

        if not texts:
            logger.warning("No user messages found in the chat history.")
            return

        total = len(texts)
        logger.info(
            f"Embedding {total} messages in batches of {EMBED_BATCH_SIZE} "
            f"(~{-(-total // EMBED_BATCH_SIZE)} API calls)..."
        )
        embeddings = []
        for batch_start in range(0, total, EMBED_BATCH_SIZE):
            batch_texts = texts[batch_start : batch_start + EMBED_BATCH_SIZE]
            batch_vecs  = self._embed_batch(batch_texts, task_type="retrieval_document")
            embeddings.extend(batch_vecs)
            done = min(batch_start + EMBED_BATCH_SIZE, total)
            logger.info(f"  {done}/{total} embedded...")
            if done < total:
                time.sleep(EMBED_BATCH_DELAY)

        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas
        )
        logger.info(f"Ingestion complete. {len(texts)} messages stored.")

    # ------------------------------------------------------------------
    # Context Retrieval — zero LLM calls
    # ------------------------------------------------------------------

    def retrieve_context(self, job_prompt: str, n_results: int = 15) -> str:
        """
        Embed the job description directly and search ChromaDB.

        The old pipeline had a separate 'generate_keywords' LLM call here,
        which consumed the only available API call per minute before the
        analysis could run. Embedding the job description directly gives
        equivalent semantic retrieval with zero LLM calls — the embedding
        model runs on its own separate quota.
        """
        query_vec = self.get_embedding(job_prompt, task_type="retrieval_query")

        results = self.collection.query(
            query_embeddings=[query_vec],
            n_results=n_results
        )

        docs = results.get("documents", [[]])[0]
        if not docs:
            logger.warning("No relevant context found in ChromaDB.")
            return ""

        return "\n---\n".join(docs)

    # ------------------------------------------------------------------
    # Suitability Analysis — the only LLM call in the pipeline
    # ------------------------------------------------------------------

    def perform_suitability_analysis(self, job_prompt: str, context: str) -> Dict[str, Any]:
        prompt = f"""
    You are an expert recruiter analyzing a candidate's background.

    Target Job: {job_prompt}

    Context from User's Chat History:
    {context}

    Tasks:
    1. Extract the user's name, surname, age, and city from context if available; use "Unknown" as placeholder.
    2. Analyze their suitability for the target job based solely on the provided messages.
    3. Assign a suitability score from 0 to 100.

    Return EXACTLY this JSON and nothing else:
    {{
        "candidate": {{
            "name": "Name",
            "surname": "Surname",
            "age": 0,
            "city": "City"
        }},
        "analysis": {{
            "profession": "Identified Job Title",
            "suitability_score": 75,
            "description": "Detailed analysis",
            "soft_skill": "Soft skill analysis"
        }}
    }}
        """.strip()

        raw = ""
        try:
            raw = self._llm_call(prompt)
            text = raw.replace("```json", "").replace("```", "").strip()
            result = json.loads(text)

            # 🔥 NEW: Save to ChromaDB
            doc_text = json.dumps(result)

            embedding = self.get_embedding(doc_text, task_type="retrieval_document")

            self.analysis_collection.add(
                ids=[str(uuid.uuid4())],
                embeddings=[embedding],
                documents=[doc_text],
                metadatas=[{
                    "job": job_prompt,
                    "type": "analysis"
                }]
            )

            logger.info("Analysis saved to ChromaDB.")

            return result

        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse analysis JSON: {e}\nRaw: {raw[:300]}")
            return {"error": "Failed to parse structured result.", "raw": raw}
        except RuntimeError as e:
            return {"error": str(e)}

# ------------------------------------------------------------------
# Pipeline
# ------------------------------------------------------------------

def run_pipeline(
    job_description: str,
    data_path: str = "data/conversations.json"
) -> Dict[str, Any]:
    agent = JobSuitabilityAgent()

    if agent.collection.count() == 0:
        logger.info("Database empty — starting ingestion...")
        agent.ingest_chat_history(data_path)
        if agent.collection.count() == 0:
            raise RuntimeError(
                "Ingestion completed but the database is still empty. "
                "Check that conversations.json contains valid user messages."
            )

    # Step 1: embed job description and retrieve context — no LLM call
    logger.info("Step 1: Retrieving relevant context from ChromaDB...")
    context = agent.retrieve_context(job_description)

    # Step 2: the one and only LLM call — rate limit guard handles timing
    logger.info("Step 2: Analysing suitability (1 RPM guard active)...")
    result = agent.perform_suitability_analysis(job_description, context)

    return result
