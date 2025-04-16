from dotenv import load_dotenv
from compareRAG import get_documents_by_college, compare_colleges_on_prompt
from compare_snowflake import search_compare_data, generate_comparison
from openai import OpenAI
import os

load_dotenv("Agents/.env")
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ---------------------- Validator Function ----------------------
def validate_and_compare_colleges(prompt: str, colleges: list[str]) -> dict:
    # ----------- RAG Agent -----------
    rag_docs = {
        college: get_documents_by_college(college, top_k=5)
        for college in colleges
    }
    rag_docs = {k: v for k, v in rag_docs.items() if v}
    rag_response = compare_colleges_on_prompt(prompt, rag_docs) if rag_docs else None

    # ----------- Snowflake Agent -----------
    snowflake_data = search_compare_data(prompt)
    snowflake_response = generate_comparison(prompt, snowflake_data) if snowflake_data else None

    # ----------- Merge & Report -----------
    sources_used = []
    merged_sections = []

    if snowflake_response and "No valid comparison" not in snowflake_response:
        sources_used.append("Snowflake")
        merged_sections.append("\U0001F4CA **Structured Comparison (from Snowflake):**\n" + snowflake_response)

    if rag_response and "No documents found" not in rag_response:
        sources_used.append("RAG")
        merged_sections.append("\U0001F4D8 **Unstructured Comparison (from RAG PDFs):**\n" + rag_response)

    if not sources_used:
        return {
            "source_used": "None",
            "final_output": (
                "❌ No valid comparison data found from Snowflake or RAG.\n"
                "If you were asking about deadlines, salaries, or rankings, make sure those fields exist for the colleges you're comparing."
            ),
            "snowflake_output": snowflake_response,
            "rag_output": rag_response
        }

    return {
        "source_used": " and ".join(sources_used),
        "final_output": "\n\n".join(merged_sections),
        "snowflake_output": snowflake_response,
        "rag_output": rag_response
    }

# ---------------------- CLI Interface ----------------------
if __name__ == "__main__":
    colleges_input = input("\U0001F3EB Enter college names to compare (comma-separated):\n> ")
    colleges = [c.strip() for c in colleges_input.split(",") if c.strip()]

    prompt = input("\n\U0001F50D What do you want to compare them on?\n> ").strip()

    results = validate_and_compare_colleges(prompt, colleges)
    print(f"\n✅ SOURCES USED: {results['source_used']}")
    print(f"\n\U0001F3AF FINAL VALIDATED COMPARISON:\n\n{results['final_output']}")
