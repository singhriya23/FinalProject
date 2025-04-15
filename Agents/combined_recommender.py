import os
from dotenv import load_dotenv
from recommendation_snowflake import search_and_filter, generate_recommendation
from RecommenderRAG import PineconeLangChainRetriever, CourseRecommenderAgent, index

load_dotenv()

# ---------------------- Setup RAG Agent ----------------------
retriever = PineconeLangChainRetriever(index)
rag_agent = CourseRecommenderAgent(retriever)

# ---------------------- Validator Function ----------------------
def validate_and_merge(prompt: str) -> str:
    # Run Snowflake Agent
    snowflake_data = search_and_filter(prompt)
    snowflake_response = generate_recommendation(prompt, snowflake_data)

    # Run RAG Agent
    rag_results = rag_agent.recommend(prompt)
    rag_clean = [r.strip() for r in rag_results if "⚠️" not in r and r.strip()]

    # Final Fallback
    if not snowflake_data and not rag_clean:
        return "❌ No valid data found in either Snowflake or RAG system. Please refine your query or use web search."

    merged_sections = []

    if snowflake_data:
        merged_sections.append("📊 **Structured College Recommendations (from Snowflake):**\n")
        merged_sections.append(snowflake_response.strip())

    if rag_clean:
        merged_sections.append("📘 **Relevant Course or Document Results (from RAG PDFs):**\n")
        for course in rag_clean:
            merged_sections.append(f"- {course}")

    return "\n\n".join(merged_sections)

# ---------------------- Main Interactive Loop ----------------------
if __name__ == "__main__":
    while True:
        prompt = input("\n📝 Enter your college/course recommendation query (or type 'exit' to quit):\n> ")
        if prompt.strip().lower() in ["exit", "quit"]:
            print("👋 Exiting validator agent. Goodbye!")
            break

        final_output = validate_and_merge(prompt)
        print("\n🎯 FINAL VALIDATED RESPONSE:\n")
        print(final_output)
