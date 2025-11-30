import os
import glob
from dotenv import load_dotenv
from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pinecone import Pinecone, ServerlessSpec
from langchain_huggingface import HuggingFaceEmbeddings
import time

# Load environment variables
load_dotenv()

# Configuration
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
INDEX_NAME = "ayurwell-index"
DATA_DIR = "data"

def get_pdf_text(pdf_path):
    text = ""
    pdf_reader = PdfReader(pdf_path)
    for page in pdf_reader.pages:
        text += page.extract_text()
    return text

def get_chunks(text):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len
    )
    chunks = text_splitter.split_text(text)
    return chunks

def main():
    if not PINECONE_API_KEY:
        print("Error: Please set PINECONE_API_KEY in .env file")
        return

    # Initialize Embeddings (Local)
    print("Loading local embedding model (all-MiniLM-L6-v2)...")
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

    # Initialize Pinecone
    pc = Pinecone(api_key=PINECONE_API_KEY)

    # Check and Recreate Index if needed (Dimension mismatch)
    # all-MiniLM-L6-v2 has 384 dimensions
    TARGET_DIMENSION = 384
    
    if INDEX_NAME in pc.list_indexes().names():
        index_info = pc.describe_index(INDEX_NAME)
        if index_info.dimension != TARGET_DIMENSION:
            print(f"Index dimension mismatch ({index_info.dimension} != {TARGET_DIMENSION}). Deleting and recreating...")
            pc.delete_index(INDEX_NAME)
            time.sleep(5) # Wait for deletion
    
    if INDEX_NAME not in pc.list_indexes().names():
        print(f"Creating index: {INDEX_NAME}")
        pc.create_index(
            name=INDEX_NAME,
            dimension=TARGET_DIMENSION, 
            metric="cosine",
            spec=ServerlessSpec(
                cloud="aws",
                region="us-east-1"
            )
        )
        # Wait for index to be ready
        while not pc.describe_index(INDEX_NAME).status['ready']:
            time.sleep(1)

    index = pc.Index(INDEX_NAME)

    # Process PDFs
    pdf_files = glob.glob(os.path.join(DATA_DIR, "*.pdf"))
    if not pdf_files:
        print(f"No PDF files found in {DATA_DIR}")
        return

    print(f"Found {len(pdf_files)} PDF(s). Starting ingestion...")

    total_vectors = 0
    for pdf_path in pdf_files:
        print(f"Processing: {pdf_path}")
        raw_text = get_pdf_text(pdf_path)
        chunks = get_chunks(raw_text)
        
        vectors = []
        for i, chunk in enumerate(chunks):
            # Generate embedding locally
            embedding = embeddings.embed_query(chunk)
            
            # Create a unique ID for each chunk
            chunk_id = f"{os.path.basename(pdf_path)}_{i}"
            metadata = {
                "text": chunk,
                "source": os.path.basename(pdf_path)
            }
            vectors.append((chunk_id, embedding, metadata))
        
        # Upsert in batches of 100
        batch_size = 100
        for i in range(0, len(vectors), batch_size):
            batch = vectors[i:i+batch_size]
            index.upsert(vectors=batch)
            print(f"  Upserted batch {i//batch_size + 1}/{(len(vectors)-1)//batch_size + 1}")
        
        total_vectors += len(vectors)

    print(f"Ingestion complete! Total vectors upserted: {total_vectors}")

if __name__ == "__main__":
    main()
