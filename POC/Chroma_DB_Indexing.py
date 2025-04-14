import os
import uuid
import fitz
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from langchain.text_splitter import RecursiveCharacterTextSplitter
from pinecone import Pinecone, ServerlessSpec

# ---------- Load .env ----------
load_dotenv(dotenv_path="Agents/.env")

# ---------- CONFIG ----------
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = "college-recommendations"
CHUNK_SIZE = 300
CHUNK_OVERLAP = 50
EMBED_MODEL = "all-MiniLM-L6-v2"
# ----------------------------

# ---------- Init Pinecone Client (v3) ----------
pc = Pinecone(api_key=PINECONE_API_KEY)

# Check/create index
if PINECONE_INDEX_NAME not in [i.name for i in pc.list_indexes()]:
    pc.create_index(
        name=PINECONE_INDEX_NAME,
        dimension=384,  # for all-MiniLM-L6-v2
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region="us-east-1")
    )

index = pc.Index(PINECONE_INDEX_NAME)

# ---------- Embedding Model ----------
embedder = SentenceTransformer(EMBED_MODEL)

# ---------- Chunking Utility ----------
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=CHUNK_SIZE,
    chunk_overlap=CHUNK_OVERLAP,
    separators=["\n\n", "\n", ".", " ", ""]
)

# ---------- PDF Reader ----------
def extract_text_from_pdf(filepath):
    doc = fitz.open(filepath)
    return "\n".join([page.get_text() for page in doc]).strip()

# ---------- Indexing ----------
def index_pdf_file(pdf_path, metadata):
    text = extract_text_from_pdf(pdf_path)
    chunks = text_splitter.split_text(text)
    base_id = os.path.splitext(os.path.basename(pdf_path))[0]

    vectors = []
    for i, chunk in enumerate(chunks):
        chunk_id = f"{base_id}_chunk_{i}_{uuid.uuid4().hex[:6]}"
        enriched_meta = {
            **metadata,
            "chunk_id": i,
            "source": os.path.basename(pdf_path),
            "text": chunk  # ✅ Needed by retriever to display content
        }
        embedding = embedder.encode(chunk).tolist()
        vectors.append({
            "id": chunk_id,
            "values": embedding,
            "metadata": enriched_meta
        })

    index.upsert(vectors=vectors)
    print(f"✅ Indexed {len(vectors)} chunks from {os.path.basename(pdf_path)}")

# ---------- Example Use ----------
if __name__ == "__main__":
    pdf_files = [
        {
            "path": "Agents/Final_Project_Datasets/Northeastern/Computer Science, MSCS _ Northeastern University Academic Catalog.pdf",
            "metadata": {
                "college_name": "NEU",
                "type": "Catalog",
                "year": "2024"
            }
        }
        
        
    ]

    for pdf in pdf_files:
        print(f"📄 Indexing {os.path.basename(pdf['path'])}")
        index_pdf_file(pdf["path"], pdf["metadata"])
