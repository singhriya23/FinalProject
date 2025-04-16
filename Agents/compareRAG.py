import os
from dotenv import load_dotenv
from typing import List
from pinecone import Pinecone
from sentence_transformers import SentenceTransformer
from langchain.schema import Document
from openai import OpenAI

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

# ---------- College Document Retriever with Top-K Limit ----------
def get_documents_by_college(college_name: str, top_k: int = 5) -> List[Document]:
    result = index.query(
        vector=[0.0] * 384,  # dummy vector just to allow filtering
        top_k=top_k,
        include_metadata=True,
        filter={"college_name": {"$eq": college_name}}
    )

    matches = result.get("matches", [])
    return [
        Document(
            page_content=m["metadata"].get("text", ""),
            metadata=m["metadata"]
        )
        for m in matches
    ]

# ---------- GPT-4 Comparator ----------
def compare_colleges_on_prompt(prompt: str, college_docs: dict) -> str:
    context = "\n\n".join([
        f"""College: {college}
Text: {' '.join([doc.page_content for doc in docs])}"""
        for college, docs in college_docs.items()
    ])

    full_prompt = f"""
You are a helpful educational assistant. A student wants to compare universities based on the following request:

"{prompt}"

Below is the course and program information for each college:

{context}

Please compare the colleges based on the student's request. Clearly list the pros/cons of each, and recommend which might be better depending on the student's goal.
"""

    response = openai_client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": full_prompt}],
        temperature=0.7
    )
    return response.choices[0].message.content.strip()

# ---------- CLI for Testing ----------
if __name__ == "__main__":
    colleges_input = input("🏫 Enter college names to compare (comma-separated):\n> ")
    colleges = [c.strip() for c in colleges_input.split(",") if c.strip()]

    prompt = input("\n🔍 What do you want to compare them on?\n> ").strip()

    college_docs = {}
    for college in colleges:
        docs = get_documents_by_college(college, top_k=5)  # Limit to top 5 documents
        if docs:
            college_docs[college] = docs
        else:
            print(f"⚠️ No documents found for {college}")

    if not college_docs:
        print("❌ No valid college data found in Pinecone.")
    else:
        result = compare_colleges_on_prompt(prompt, college_docs)
        print("\n📊 GPT-4 COMPARISON RESULT:\n")
        print(result)
