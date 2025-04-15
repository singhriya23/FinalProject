import os
from dotenv import load_dotenv
from recommendation_snowflake import search_and_filter, generate_recommendation
from RecommenderRAG import PineconeLangChainRetriever, CourseRecommenderAgent, index
from langchain_openai import ChatOpenAI

# Load environment variables
load_dotenv()

# ---------------------- Setup LLM + Agents ----------------------
llm = ChatOpenAI(model="gpt-4", temperature=0.2)

retriever = PineconeLangChainRetriever(index)
rag_agent = CourseRecommenderAgent(retriever)

# ---------------------- Validator with Relevance Check ----------------------
def validate_and_merge_with_verification(prompt: str) -> str:
    # Run Snowflake agent
    snowflake_data = search_and_filter(prompt)
    snowflake_response = generate_recommendation(prompt, snowflake_data)

    # Run RAG agent
    rag_results = rag_agent.recommend(prompt)
    rag_clean = [r.strip() for r in rag_results if "⚠️" not in r and r.strip()]
    rag_merged = "\n".join(rag_clean)

    # Fallback if both fail
    if not snowflake_data and not rag_clean:
        return "No valid data found in either Snowflake or RAG system. Please refine your query or use web search."

    output_parts = [f"🔎 **Prompt:**\n{prompt}"]

    # ---------------------- Snowflake Relevance Check ----------------------
    snowflake_verdict = llm.invoke(f"""
You are a validator agent. Check if the following Snowflake-based recommendation aligns with the user's query.

Prompt: {prompt}

Snowflake Response:
{snowflake_response}

Respond YES or NO, then briefly explain why.
""").content.strip()

    output_parts.append("\n🧠 **Snowflake Validation:**")
    output_parts.append(snowflake_verdict)

    if "yes" in snowflake_verdict.lower():
        output_parts.append("\n📊 **Structured Recommendation (Snowflake):**")
        output_parts.append(snowflake_response.strip())

    # ---------------------- RAG Relevance Check ----------------------
    rag_verdict = llm.invoke(f"""
You are a validator agent. Check if the following document-based (RAG) recommendation aligns with the user's query.

Prompt: {prompt}

RAG Response:
{rag_merged}

Respond YES or NO, then briefly explain why.
""").content.strip()

    output_parts.append("\n📘 **RAG Validation:**")
    output_parts.append(rag_verdict)

    if "yes" in rag_verdict.lower():
        output_parts.append("\n📚 **Document-Based Recommendations (RAG):**")
        output_parts.extend([f"- {course}" for course in rag_clean])

    return "\n\n".join(output_parts)

# ---------------------- Interactive CLI ----------------------
if __name__ == "__main__":
    while True:
        prompt = input("\n📝 Enter your college/course recommendation query (or type 'exit' to quit):\n> ")
        if prompt.strip().lower() in ["exit", "quit"]:
            print("👋 Exiting validator agent. Goodbye!")
            break

        final_output = validate_and_merge_with_verification(prompt)
        print("\n🎯 FINAL VALIDATED RESPONSE:\n")
        print(final_output)
