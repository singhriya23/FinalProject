from dotenv import load_dotenv
from multi_Agents.recommendation_snowflake import search_and_filter, generate_recommendation
from multi_Agents.RecommenderRAG_2 import PineconeRetriever, GPT4Recommender, CourseRecommenderAgent
from pinecone import Pinecone
from sentence_transformers import SentenceTransformer
import os

# ---------- Load environment ----------
load_dotenv("Agents/.env")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = "college-recommendations"
EMBED_MODEL_NAME = "all-MiniLM-L6-v2"

# ---------- Setup ----------
embedder = SentenceTransformer(EMBED_MODEL_NAME)
pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(PINECONE_INDEX_NAME)

# ---------- Initialize Agents ----------
retriever = PineconeRetriever(index)
gpt4 = GPT4Recommender()
rag_agent = CourseRecommenderAgent(retriever, gpt4)

# ---------- Validator Function (Updated Structure) ----------
def validate_and_compare(prompt: str) -> dict:
    # Run Snowflake Agent
    snowflake_data = search_and_filter(prompt)
    snowflake_response = generate_recommendation(prompt, snowflake_data) if snowflake_data else None

    # Run RAG Agent
    rag_response = rag_agent.recommend(prompt)
    rag_clean = [r.strip() for r in rag_response.split("\n") if "⚠️" not in r and r.strip()] if rag_response else []

    # Final Fallback
    if not snowflake_data and not rag_clean:
        return {
            "combined_agent_results": "❌ No valid data found in either Snowflake or RAG system. Please refine your query or use web search.",
            "snowflake_results": [],
            "rag_results": [],
        }

    merged_sections = []

    if snowflake_data:
        merged_sections.append("📊 **Structured College Recommendations (from Snowflake):**\n")
        merged_sections.append(snowflake_response.strip())

    if rag_clean:
        merged_sections.append("📘 **Relevant Course or Document Results (from RAG PDFs):**\n")
        for course in rag_clean:
            merged_sections.append(f"- {course}")

    return {
        "combined_agent_results": "\n\n".join(merged_sections),
        "snowflake_results": snowflake_data,  # Raw Snowflake data (original structure)
        "rag_results": [{"text": course, "metadata": {"source": "rag"}} for course in rag_clean]  # RAG as list of dicts
    }

# ---------- CLI for Interactive Testing ----------
if __name__ == "__main__":
    while True:
        prompt = input("\n🔍 Enter your college/course query (or type 'exit' to quit):\n> ").strip()
        if prompt.lower() in ["exit", "quit"]:
            print("👋 Exiting validator agent.")
            break

        results = validate_and_compare(prompt)
        print(f"\n✅ SOURCES USED: {'Snowflake' if results['snowflake_results'] else ''}{' + RAG' if results['rag_results'] else ''}")
        print(f"\n🎯 FINAL VALIDATED RESPONSE:\n\n{results['combined_agent_results']}")