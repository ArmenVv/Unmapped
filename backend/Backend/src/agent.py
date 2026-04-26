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

EMBEDDING_MODEL = "models/gemini-embedding-2"
ANALYSIS_MODEL = "gemini-2.5-flash"
MAX_RETRIES = 3
RETRY_BACKOFF = 2
LLM_MIN_INTERVAL = 61
EMBED_BATCH_SIZE = 20
EMBED_BATCH_DELAY = 2.0


class JobSuitabilityAgent:
    def __init__(self, chroma_path: str = "./chroma_db"):
        self.api_key = os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")

        self.client = genai.Client(api_key=self.api_key)
        self._last_llm_call: float = 0.0

        self.chroma_client = chromadb.PersistentClient(path=chroma_path)

        try:
            self.collection = self.chroma_client.get_collection(name="chat_history")
            logger.info("Loaded existing chat_history collection.")
        except chromadb.errors.NotFoundError:
            self.collection = self.chroma_client.create_collection(name="chat_history")
            logger.info("Created chat_history collection.")

        try:
            self.candidates_collection = self.chroma_client.get_collection(name="candidate_profiles")
            logger.info("Loaded existing candidate_profiles collection.")
        except chromadb.errors.NotFoundError:
            self.candidates_collection = self.chroma_client.create_collection(name="candidate_profiles")
            logger.info("Created candidate_profiles collection.")

    @staticmethod
    def _parse_retry_delay(error: Exception) -> float:
        import re
        error_str = str(error)
        match = re.search(r"retryDelay.*?([0-9]+(?:\.[0-9]+)?)s", error_str)
        if match:
            return float(match.group(1)) + 2
        return float(LLM_MIN_INTERVAL)

    def _llm_call(self, prompt: str) -> str:
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
                        f"Rate limit on attempt {attempt}. Server says wait {wait:.0f}s..."
                    )
                else:
                    wait = float(RETRY_BACKOFF ** attempt)
                    logger.warning(f"LLM attempt {attempt} failed: {e}. Retrying in {wait:.0f}s...")

                if attempt < MAX_RETRIES:
                    time.sleep(wait)

        raise RuntimeError(f"LLM call failed after {MAX_RETRIES} retries.")

    def get_embedding(self, text: str, task_type: str = "retrieval_query") -> List[float]:
        return self._embed_batch([text], task_type)[0]

    def _embed_batch(self, texts: List[str], task_type: str) -> List[List[float]]:
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

    def ingest_chat_history(self, json_path: str):
        if not os.path.exists(json_path):
            raise FileNotFoundError(f"Chat history not found: {json_path}")

        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        logger.info(f"Ingesting {len(data)} conversations...")

        texts, ids, metadatas = [], [], []

        for conv in data:
            title = conv.get("title", "Untitled")
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
        logger.info(f"Embedding {total} messages in batches of {EMBED_BATCH_SIZE}...")

        embeddings = []
        for batch_start in range(0, total, EMBED_BATCH_SIZE):
            batch_texts = texts[batch_start: batch_start + EMBED_BATCH_SIZE]
            batch_vecs = self._embed_batch(batch_texts, task_type="retrieval_document")
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
        logger.info(f"Ingestion complete. {len(texts)} messages stored in chat_history.")

    def retrieve_context(self, job_prompt: str, n_results: int = 15) -> str:
        query_vec = self.get_embedding(job_prompt, task_type="retrieval_query")

        results = self.collection.query(
            query_embeddings=[query_vec],
            n_results=n_results
        )

        docs = results.get("documents", [[]])[0]
        if not docs:
            logger.warning("No relevant context found in chat_history.")
            return ""

        return "\n---\n".join(docs)

    def perform_suitability_analysis(self, job_prompt: str, context: str) -> Dict[str, Any]:
        prompt = f"""
You are an expert recruiter analyzing a candidate's background.

Target Job:
{job_prompt}

Context from User's Chat History:
{context}

Tasks:
1. Extract the user's name, surname, age, and city from context if available. Use "Unknown" if unavailable.
2. Analyze their suitability for the target job based only on the provided context.
3. Assign a suitability score from 0 to 100, with formula ((LowLevelSkills) + (MiddleLevelSkills*10) + (HighLevelSkills*30))* (messages_count)/100.

Return EXACTLY this JSON and nothing else:
{{
    "candidate": {{
        "name": "Name or Unknown",
        "surname": "Surname or Unknown",
        "age": 0,
        "city": "City or Unknown"
        "job_fining": "Short description of Target Job (maximum 20 word)"
    }},
    "analysis": {{
        "profession": "Identified Job Title",
        "suitability_score": 75,
        "skills": ["skill1", "skill2"],
        "big_projects": ["big_projects1", "big_projects2"] or [],
        "experience_level": "Short summary of relevant experience level",
        "description": "Detailed rough analysis based on the chat history (70 word maximum)"
    }}
}}
""".strip()

        raw = ""
        try:
            raw = self._llm_call(prompt)
            text = raw.replace("```json", "").replace("```", "").strip()
            return json.loads(text)
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse analysis JSON: {e}\nRaw: {raw[:300]}")
            return {"error": "Failed to parse structured result.", "raw": raw}
        except RuntimeError as e:
            return {"error": str(e)}

    def store_candidate_profile(self, result: Dict[str, Any]) -> Dict[str, Any]:
        if "error" in result:
            return result

        candidate = result.get("candidate", {})
        analysis = result.get("analysis", {})

        candidate_id = str(uuid.uuid4())

        skills = analysis.get("skills", []) or []
        strengths = analysis.get("strengths", []) or []
        weaknesses = analysis.get("weaknesses", []) or []

        profile_text = f"""
        Candidate ID: {candidate_id}
        Name: {candidate.get("name", "Unknown")} {candidate.get("surname", "Unknown")}
        Age: {candidate.get("age", "Unknown")}
        City: {candidate.get("city", "Unknown")}
        Job Target: {candidate.get("job_fining", "Unknown")}
        Profession: {analysis.get("profession", "Unknown")}
        Suitability Score: {analysis.get("suitability_score", 0)}
        Experience Level: {analysis.get("experience_level", "Unknown")}
        Skills: {", ".join(analysis.get("skills", [])) if analysis.get("skills") else "None"}
        Big Projects: {", ".join(analysis.get("big_projects", [])) if analysis.get("big_projects") else "None"}
        Description: {analysis.get("description", "")}
        """.strip()

        embedding = self.get_embedding(profile_text, task_type="retrieval_document")

        self.candidates_collection.add(
            ids=[candidate_id],
            embeddings=[embedding],
            documents=[profile_text],
            metadatas=[{
                "candidate_id": candidate_id,

                # --- PERSONAL INFO ---
                "name": str(candidate.get("name", "Unknown")),
                "surname": str(candidate.get("surname", "Unknown")),
                "age": int(candidate.get("age", 0) or 0),
                "city": str(candidate.get("city", "Unknown")),
                "job_target": str(candidate.get("job_fining", "Unknown")),

                # --- ANALYSIS ---
                "profession": str(analysis.get("profession", "Unknown")),
                "suitability_score": float(analysis.get("suitability_score", 0) or 0),
                "experience_level": str(analysis.get("experience_level", "Unknown")),
                "description": str(analysis.get("description", "")),

                # --- STRUCTURED DATA (IMPORTANT) ---
                "skills": analysis.get("skills", []),
                "big_projects": analysis.get("big_projects", []),

                # Optional: keep raw JSON for debugging
                "raw_analysis": json.dumps(analysis),
            }]
        )

        result["candidate_id"] = candidate_id
        result["stored_in_database"] = True
        return result


class EmployerAgent(JobSuitabilityAgent):
    def search_candidates(self, employer_prompt: str, n_results: int = 5) -> Dict[str, Any]:
        if self.candidates_collection.count() == 0:
            return {
                "error": "No candidate profiles found. First run candidate analysis and store profiles."
            }

        query_vec = self.get_embedding(employer_prompt, task_type="retrieval_query")

        results = self.candidates_collection.query(
            query_embeddings=[query_vec],
            n_results=n_results
        )

        docs = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]

        if not docs:
            return {"error": "No suitable candidates found."}

        candidates_context = "\n---\n".join(docs)

        prompt = f"""
You are an AI employer assistant.

Employer is looking for:
{employer_prompt}

Candidate database search results:
{candidates_context}

Tasks:
1. Choose the most suitable candidates.
2. Describe their skills and experience.
3. Explain why each candidate fits or does not fully fit.
4. Give a final hiring suggestion to the employer.



Return EXACTLY this JSON and nothing else:
{{
    "matches": [
        {{
            "candidate_id": "Candidate ID from database",
            "name": "Candidate name",
            "profession": "Candidate profession and level",
            "match_score": 85,
            "skills": ["skill1", "skill2"],
            "experience": "Relevant experience, based on big projects",
            "why_good_fit": "Why this person fits the employer request",
            "concerns": "Weak points or risks"
        }}
    ]
}}
""".strip()

        raw = ""
        try:
            raw = self._llm_call(prompt)
            text = raw.replace("```json", "").replace("```", "").strip()
            llm_result = json.loads(text)
            llm_result["raw_database_results"] = metadatas
            return llm_result
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse employer JSON: {e}\nRaw: {raw[:300]}")
            return {
                "error": "Failed to parse employer search result.",
                "raw": raw,
                "raw_database_results": metadatas,
            }
        except RuntimeError as e:
            return {"error": str(e)}


def run_pipeline(
    job_description: str,
    data_path: str = "data/conversations.json"
) -> Dict[str, Any]:
    agent = JobSuitabilityAgent()

    if agent.collection.count() == 0:
        logger.info("chat_history database empty — starting ingestion...")
        agent.ingest_chat_history(data_path)
        if agent.collection.count() == 0:
            raise RuntimeError(
                "Ingestion completed but the database is still empty. "
                "Check that conversations.json contains valid user messages."
            )

    logger.info("Step 1: Retrieving relevant context from chat_history...")
    context = agent.retrieve_context(job_description)

    logger.info("Step 2: Analysing suitability...")
    result = agent.perform_suitability_analysis(job_description, context)

    logger.info("Step 3: Storing final candidate profile in candidate_profiles...")
    result = agent.store_candidate_profile(result)

    return result


def run_employer_search(employer_prompt: str, n_results: int = 5) -> Dict[str, Any]:
    agent = EmployerAgent()
    return agent.search_candidates(employer_prompt, n_results=n_results)
