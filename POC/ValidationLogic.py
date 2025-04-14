import os
import json
from typing import List
from dotenv import load_dotenv
from langchain.schema import Document
from langchain.chat_models import ChatOpenAI

load_dotenv(dotenv_path="Agents/.env")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

OPENAI_MODEL = "gpt-4o"

# Load saved docs from JSON
def load_saved_docs(path="retriever_output.json") -> (str, List[Document]):
    with open(path, "r") as f:
        data = json.load(f)
    query = data["query"]
    docs = [Document(page_content=d["text"], metadata=d["metadata"]) for d in data["results"]]
    return query, docs

# --- Validator Agent using GPT ---
def validate_with_gpt(query: str, docs: List[Document]) -> (bool, str):
    llm = ChatOpenAI(model_name=OPENAI_MODEL, temperature=0.3, openai_api_key=OPENAI_API_KEY)

    combined_context = "\n\n".join([f"Doc {i+1}:\n{d.page_content}" for i, d in enumerate(docs)])
    validation_prompt = f"""
You are a validator agent. Your task is to assess if the following documents are relevant and useful to answer the user's query.

User Query:
"{query}"

Documents:
{combined_context}

Evaluate the documents and return a response in the following JSON format:
{{
  "verdict": "pass" or "fail",
  "reason": "Your reasoning here."
}}

Respond ONLY in valid JSON.
"""

    response = llm.predict(validation_prompt)

    try:
        result = json.loads(response)
        verdict = result.get("verdict", "").lower() == "pass"
        return verdict, result.get("reason", "No reason provided.")
    except Exception as e:
        return False, f"Failed to parse response: {str(e)}\nRaw response: {response}"

# Optional: final LLM response generator
from langchain.schema.retriever import BaseRetriever
from langchain.chains import RetrievalQA

def generate_final_answer(query: str, docs: List[Document]) -> str:
    class StaticRetriever(BaseRetriever):
        def get_relevant_documents(self, _: str) -> List[Document]:
            return docs
        async def aget_relevant_documents(self, _: str) -> List[Document]:
            return docs

    llm = ChatOpenAI(model_name=OPENAI_MODEL, temperature=0.7, openai_api_key=OPENAI_API_KEY)
    chain = RetrievalQA.from_chain_type(llm=llm, retriever=StaticRetriever())
    return chain.run(query)

# --- CLI ---
if __name__ == "__main__":
    query, docs = load_saved_docs()

    print("🤖 Validating retrieved documents with GPT...\n")
    verdict, reason = validate_with_gpt(query, docs)

    if verdict:
        print("✅ Validation PASSED:")
        print(f"🧠 Reason: {reason}\n")
        print("📣 Generating final LLM answer...\n")
        print(f"🤖 Final Answer:\n{generate_final_answer(query, docs)}\n")
    else:
        print("❌ Validation FAILED:")
        print(f"🧠 Reason: {reason}")
