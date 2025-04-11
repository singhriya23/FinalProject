import os
from dotenv import load_dotenv
from typing import List
from pinecone import Pinecone
from sentence_transformers import SentenceTransformer
from langchain.schema import Document
from langchain.chat_models import ChatOpenAI
from langchain.chains import RetrievalQA
from langchain.schema.retriever import BaseRetriever

# --- Load API Keys from .env ---
load_dotenv(dotenv_path="Agents/.env")  # Adjust path if needed
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")

# --- Config ---
PINECONE_INDEX_NAME = "college-recommendations"
EMBED_MODEL_NAME = "all-MiniLM-L6-v2"
OPENAI_MODEL = "gpt-4o"  # or "gpt-4o-mini", "gpt-3.5-turbo"

# --- Initialize Embedding Model ---
embedder = SentenceTransformer(EMBED_MODEL_NAME)

# --- Initialize Pinecone Client ---
pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(PINECONE_INDEX_NAME)

# --- Custom Retriever for Pinecone ---
class PineconeLangChainRetriever(BaseRetriever):
    def __init__(self, pinecone_index, top_k=4):
        super().__init__()
        self._index = pinecone_index  # ✅ Private attribute to avoid LangChain validation issues
        self._top_k = top_k

    def get_relevant_documents(self, query: str) -> List[Document]:
        query_embedding = embedder.encode(query).tolist()
        result = self._index.query(
            vector=query_embedding,
            top_k=self._top_k,
            include_metadata=True
        )
        return [
            Document(page_content=match['metadata'].get('text', ''), metadata=match['metadata'])
            for match in result['matches']
        ]

    async def aget_relevant_documents(self, query: str) -> List[Document]:
        return self.get_relevant_documents(query)

# --- Initialize Retriever ---
retriever = PineconeLangChainRetriever(index)

# --- Initialize OpenAI LLM ---
llm = ChatOpenAI(
    temperature=0.9,
    model_name=OPENAI_MODEL,
    openai_api_key=OPENAI_API_KEY
)

# --- Create RAG Chain ---
rag_chain = RetrievalQA.from_chain_type(llm=llm, retriever=retriever)

# --- CLI Loop ---
if __name__ == "__main__":
    print("🎓 RAG Agent Ready (OpenAI + Pinecone)")
    print("Ask anything about colleges, programs, faculty... Type 'exit' to quit.\n")

    while True:
        user_input = input("You: ")
        if user_input.lower() in ["exit", "quit"]:
            print("👋 Goodbye!")
            break

        response = rag_chain.run(user_input)
        print(f"\n🤖 Agent: {response}\n")
