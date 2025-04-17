import os
from dotenv import load_dotenv
from openai import OpenAI
from multi_Agents.compare_snowflake import search_compare_data, generate_comparison
from multi_Agents.compareRAG import CollegeDocumentRetriever, GPT4CollegeComparator, resolve_college, index

# ---------- Load environment ----------
load_dotenv("Agents/.env")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# ---------- Setup ----------
openai_client = OpenAI(api_key=OPENAI_API_KEY)

# ---------- Snowflake Agent ----------
def get_snowflake_response(prompt: str) -> str:
    data = search_compare_data(prompt)
    if data:
        return generate_comparison(prompt, data)
    return ""

# ---------- RAG Agent ----------
def get_rag_response(prompt: str) -> str:
    retriever = CollegeDocumentRetriever(index)
    comparator = GPT4CollegeComparator()

    # Simple extraction of two college names (first and second occurrence)
    prompt_lower = prompt.lower()
    found = [c for c in retriever.known_colleges if c.lower() in prompt_lower]
    if len(found) < 2:
        return ""

    clg1_resolved = resolve_college(found[0], retriever.known_colleges, retriever.alias_map)
    clg2_resolved = resolve_college(found[1], retriever.known_colleges, retriever.alias_map)

    if not clg1_resolved or not clg2_resolved:
        return ""

    docs1 = retriever.get_documents_for_college(clg1_resolved)
    docs2 = retriever.get_documents_for_college(clg2_resolved)
    college_docs = {clg1_resolved: docs1, clg2_resolved: docs2}

    return comparator.compare(clg1_resolved, clg2_resolved, prompt, college_docs)

# ---------- Validator Agent ----------
def compare_validate(prompt: str) -> str:
    snowflake_output = get_snowflake_response(prompt)
    rag_output = get_rag_response(prompt)

    if not snowflake_output and not rag_output:
        return ""

    combined_prompt = f"""
You are a university comparison validator.

USER PROMPT:
{prompt}

SNOWFLAKE AGENT OUTPUT:
{snowflake_output if snowflake_output else '[No result]'}

RAG AGENT OUTPUT:
{rag_output if rag_output else '[No result]'}

TASK:
Review the outputs. If either contains relevant comparison information, combine them and return a clean, helpful comparison.
If neither provides relevant data, return an empty string.
"""

    response = openai_client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": combined_prompt}],
        temperature=0.5
    )
    return response.choices[0].message.content.strip()

# ---------- CLI ----------
if __name__ == "__main__":
    prompt = input("\n> ").strip()
    result = compare_validate(prompt)
    if result:
        print("\n📊 COMPARISON RESULT:\n")
        print(result)
