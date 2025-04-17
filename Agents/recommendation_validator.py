from dotenv import load_dotenv
from recommendation_snowflake import search_and_filter, generate_recommendation
from multi_Agents.RecommenderRAG_3 import PineconeRetriever, GPT4Recommender, CourseRecommenderAgent
from pinecone import Pinecone
from sentence_transformers import SentenceTransformer
from openai import OpenAI
import os
import sys
import contextlib

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

# ---------- Silence stdout context ----------
@contextlib.contextmanager
def suppress_stdout():
    with open(os.devnull, "w") as devnull:
        old_stdout = sys.stdout
        sys.stdout = devnull
        try:
            yield
        finally:
            sys.stdout = old_stdout

# ---------- Initialize Agents ----------
retriever = PineconeRetriever(index)
gpt4 = GPT4Recommender()
rag_agent = CourseRecommenderAgent(retriever, gpt4)

# ---------- Validator Function ----------
def validate_and_compare(prompt: str) -> str:
    # Run Snowflake Agent
    snowflake_data = search_and_filter(prompt)
    snowflake_response = generate_recommendation(prompt, snowflake_data) if snowflake_data else ""

    # Run RAG Agent (silencing debug prints)
    with suppress_stdout():
        rag_response = rag_agent.recommend(prompt)
    rag_response_clean = rag_response.strip() if rag_response else ""

    # Check if both sources failed
    if not snowflake_data and (not rag_response_clean or "no relevant course information" in rag_response_clean.lower()):
        return "❌ No relevant data found in Snowflake or RAG system. Consider using the web search agent."

    # Combine responses
    combined_content = "\n\n".join(filter(None, [snowflake_response, rag_response_clean]))

    # Send to GPT-4
    full_prompt = f"""
You are a helpful college guidance assistant. A user has asked the following question:

"{prompt}"

You have access to combined information retrieved from both structured databases and document-based sources:

{combined_content}

Please structure the information in a useful and user-friendly way. Ensure the response directly answers the user's query.

Your response must:
- Only recommend courses from the colleges explicitly mentioned in the query
- Avoid vague phrases like 'refer to the catalog' or 'check the website'
- Include admission requirements if they are present in the data
- Avoid separating the sources (combine Snowflake and RAG data)
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
