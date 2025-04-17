import os
from dotenv import load_dotenv
from openai import OpenAI

from multi_Agents.recommendation_snowflake import search_and_filter, generate_recommendation
from multi_Agents.RecommenderRAG_4 import PineconeRetriever, GPT4Recommender, CourseRecommenderAgent, index

# ---------- Load Environment ----------
load_dotenv("Agents/.env")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai_client = OpenAI(api_key=OPENAI_API_KEY)

# ---------- Initialize Agents ----------
retriever = PineconeRetriever(index)
gpt4 = GPT4Recommender()
rag_agent = CourseRecommenderAgent(retriever, gpt4)

# ---------- Validator Agent with Code 2 Output Structure ----------
def validate_and_compare(prompt: str) -> dict:
    # Get responses from both agents
    snowflake_data = search_and_filter(prompt)
    snowflake_response = generate_recommendation(prompt, snowflake_data) if snowflake_data else None
    rag_response = rag_agent.recommend(prompt)

    # Process RAG response to match Code 2 structure
    rag_clean = []
    if rag_response and "no relevant course information" not in rag_response.lower():
        rag_clean = [r.strip() for r in rag_response.split("\n") if "⚠️" not in r and r.strip()]

    # Generate combined response using GPT-4 (Code 1 approach)
    combined_prompt = f"""
You are a university and course recommendation validator.

USER PROMPT:
{prompt}

SNOWFLAKE AGENT OUTPUT:
{snowflake_response if snowflake_response else '[No result]'}

RAG AGENT OUTPUT:
{rag_response if rag_response else '[No result]'}

TASK:
Read the user prompt and the outputs from both agents.

1. If either output contains information relevant to the user prompt, generate a clean, well-formatted answer using the data provided.
2. If neither output is relevant to the user prompt, return an empty string only.
"""
    
    gpt_response = openai_client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": combined_prompt}],
        temperature=0.4
    )
    final_response = gpt_response.choices[0].message.content.strip()

    # Return in Code 2 output structure
    return {
        "combined_agent_results": final_response if final_response else 
            "❌ No valid data found in either Snowflake or RAG system. Please refine your query or use web search.",
        "snowflake_results": snowflake_data if snowflake_data else [],
        "rag_results": [{"text": course, "metadata": {"source": "rag"}} for course in rag_clean]
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