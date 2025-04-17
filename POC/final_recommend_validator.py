import os
from dotenv import load_dotenv
from openai import OpenAI

from recommendation_snowflake import search_and_filter, generate_recommendation
from RecommenderRAG_4 import PineconeRetriever, GPT4Recommender, CourseRecommenderAgent, index

# ---------- Load Environment ----------
load_dotenv("Agents/.env")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai_client = OpenAI(api_key=OPENAI_API_KEY)

# ---------- Wrapper for Snowflake Agent ----------
def get_snowflake_response(prompt: str) -> str:
    data = search_and_filter(prompt)
    return generate_recommendation(prompt, data)

# ---------- Wrapper for RAG Agent ----------
def get_rag_response(prompt: str) -> str:
    retriever = PineconeRetriever(index)
    gpt4 = GPT4Recommender()
    agent = CourseRecommenderAgent(retriever, gpt4)
    return agent.recommend(prompt)

# ---------- Validator Agent ----------
def validate_and_respond(prompt: str) -> str:
    snowflake_output = get_snowflake_response(prompt)
    rag_output = get_rag_response(prompt)

    # Always send both outputs to GPT-4
    combined_prompt = f"""
You are a university and course recommendation validator.

USER PROMPT:
{prompt}

SNOWFLAKE AGENT OUTPUT:
{snowflake_output if snowflake_output else '[No result]'}

RAG AGENT OUTPUT:
{rag_output if rag_output else '[No result]'}

TASK:
Read the user prompt and the outputs from both agents.

1. If **either output contains information relevant to the user prompt**, generate a clean, well-formatted answer using the data provided.
2. If **neither output is relevant to the user prompt**, return an **empty string only**. Do not explain. Do not apologize. Do not justify.

Always obey these rules exactly.
"""

    response = openai_client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": combined_prompt}],
        temperature=0.4
    )
    return response.choices[0].message.content.strip()

# ---------- CLI ----------
if __name__ == "__main__":
    prompt = input("\n💬 What kind of colleges or programs are you looking for?\n> ").strip()
    final_response = validate_and_respond(prompt)

    if final_response:
        print("\n🎓 FINAL GPT-4 RECOMMENDATION:\n")
        print(final_response)
