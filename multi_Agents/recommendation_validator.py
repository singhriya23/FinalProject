from dotenv import load_dotenv
from recommendation_snowflake import search_and_filter, generate_recommendation
from RecommenderRAG_2 import PineconeRetriever, GPT4Recommender, CourseRecommenderAgent
from pinecone import Pinecone
from sentence_transformers import SentenceTransformer
from openai import OpenAI
import os

# ---------- Load environment ----------
load_dotenv("Agents/.env")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = "college-recommendations"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
EMBED_MODEL_NAME = "all-MiniLM-L6-v2"

# ---------- Setup ----------
embedder = SentenceTransformer(EMBED_MODEL_NAME)
pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(PINECONE_INDEX_NAME)
openai_client = OpenAI(api_key=OPENAI_API_KEY)

# ---------- Initialize Agents ----------
retriever = PineconeRetriever(index)
gpt4 = GPT4Recommender()
rag_agent = CourseRecommenderAgent(retriever, gpt4)

# ---------- Validator Function ----------
def validate_and_compare(prompt: str) -> str:
    # Run Snowflake Agent
    snowflake_data = search_and_filter(prompt)
    snowflake_response = generate_recommendation(prompt, snowflake_data) if snowflake_data else ""

    # Run RAG Agent
    rag_response = rag_agent.recommend(prompt)
    rag_response_clean = rag_response.strip() if rag_response else ""

    # Combine all content
    combined_content = "".join([
        snowflake_response if snowflake_response else "",
        "\n\n",
        rag_response_clean if rag_response_clean else ""
    ]).strip()

    if not combined_content:
        return "❌ No valid data found in either Snowflake or RAG system. Please refine your query."

    # Give final prompt to LLM to evaluate and format
    full_prompt = f"""
You are a helpful college guidance assistant. A user has asked the following question:

"{prompt}"

You have access to combined information retrieved from both structured databases and document-based sources:

{combined_content}

Please structure the information in a useful and user-friendly way. Ensure the response directly answers the user's query. Do not make vague or generic suggestions like 'check the university's catalog' or 'refer to their website.' Avoid redundancy and avoid separating by source.
"""

    response = openai_client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": full_prompt}],
        temperature=0.7
    )
    return response.choices[0].message.content.strip()

# ---------- CLI for Interactive Testing ----------
if __name__ == "__main__":
    while True:
        prompt = input("\n🔍 Enter your college/course query (or type 'exit' to quit):\n> ").strip()
        if prompt.lower() in ["exit", "quit"]:
            print("👋 Exiting validator agent.")
            break

        final_output = validate_and_compare(prompt)
        print("\n🎯 FINAL RESPONSE:\n")
        print(final_output)
