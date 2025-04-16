from dotenv import load_dotenv
from recommendation_snowflake import search_and_filter, generate_recommendation
from RecommenderRAG_2 import PineconeRetriever, GPT4Recommender, CourseRecommenderAgent
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

# ---------- Validator Function ----------
def validate_and_compare(prompt: str) -> dict:
    # Run Snowflake Agent
    snowflake_data = search_and_filter(prompt)
    snowflake_response = generate_recommendation(prompt, snowflake_data) if snowflake_data else None

    # Run RAG Agent
    rag_response = rag_agent.recommend(prompt)
    rag_response_clean = rag_response.strip() if rag_response else None

    used_sources = []
    merged_output = []

    if snowflake_response:
        used_sources.append("Snowflake")
        merged_output.append("📊 **Structured College Recommendations (Snowflake):**")
        merged_output.append(snowflake_response)

    if rag_response_clean and "No relevant course information" not in rag_response_clean:
        used_sources.append("RAG")
        merged_output.append("📘 **Document-Based Course Suggestions (RAG):**")
        merged_output.append(rag_response_clean)

    if not used_sources:
        return {
            "source_used": "None",
            "final_output": "❌ No valid data found in either Snowflake or RAG system. Please refine your query.",
            "snowflake_output": None,
            "rag_output": None
        }

    return {
        "source_used": " and ".join(used_sources),
        "final_output": "\n\n".join(merged_output),
        "snowflake_output": snowflake_response,
        "rag_output": rag_response_clean
    }

# ---------- CLI for Interactive Testing ----------
if __name__ == "__main__":
    while True:
        prompt = input("\n🔍 Enter your college/course query (or type 'exit' to quit):\n> ").strip()
        if prompt.lower() in ["exit", "quit"]:
            print("👋 Exiting validator agent.")
            break

        results = validate_and_compare(prompt)
        print(f"\n✅ SOURCES USED: {results['source_used']}")
        print(f"\n🎯 FINAL VALIDATED RESPONSE:\n\n{results['final_output']}")
