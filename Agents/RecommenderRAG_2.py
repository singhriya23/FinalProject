import os, json
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

# ---------- Retriever ----------
class PineconeRetriever:
    def __init__(self, pinecone_index, top_k=8):
        self._index = pinecone_index
        self._top_k = top_k

    def get_relevant_documents(self, query: str) -> List[Document]:
        embedding = embedder.encode(query).tolist()
        result = self._index.query(
            vector=embedding,
            top_k=self._top_k,
            include_metadata=True
        )

        matches = result.get("matches", [])
        print("📄 Top Matched Chunks (by college):")
        for m in matches:
            print("-", m["metadata"].get("college_name"), ":", m["metadata"].get("source"))

        return [
            Document(
                page_content=m["metadata"].get("text", ""),  # actual course text
                metadata=m["metadata"]
            )
            for m in matches
        ]

# ---------- GPT-4 Synthesizer ----------
class GPT4Recommender:
    def __init__(self, model="gpt-4"):
        self.model = model

    def recommend(self, query: str, docs: List[Document]) -> str:
        # Build context from available docs — even if empty
        context = "\n\n".join([
            f"""College: {doc.metadata.get("college_name", "N/A")}
Source: {doc.metadata.get("source", "N/A")}
Text: {doc.page_content.strip()}"""
            for doc in docs
        ])

        prompt = f"""
You are a course recommender. A student has asked:

"{query}"

You have access to the following university course catalog content:

{context} 

Your job is to recommend specific courses.
If exact matches are not found, suggest similar courses from the base knowledge you have.
Even if the content is empty, provide a recommendation based on your knowledge.
Also if the user asks about program requirements, provide that if it is not in context give generalized recommendations

"""

        response = openai_client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        return response.choices[0].message.content.strip()

# ---------- RAG Agent ----------
class CourseRecommenderAgent:
    def __init__(self, retriever: PineconeRetriever, gpt4: GPT4Recommender):
        self.retriever = retriever
        self.gpt4 = gpt4

    def recommend(self, query: str) -> str:
        docs = self.retriever.get_relevant_documents(query)
        return self.gpt4.recommend(query, docs)

# ---------- CLI ----------
if __name__ == "__main__":
    retriever = PineconeRetriever(index)
    gpt4 = GPT4Recommender()
    agent = CourseRecommenderAgent(retriever, gpt4)

    user_query = input("🎓 Ask your course question (e.g., 'What AI courses does Yale offer?'):\n> ")
    answer = agent.recommend(user_query)

    print("\n🧠 GPT-4 Course Recommendations:\n")
    print(answer)
