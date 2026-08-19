"""
ingest.py - Build the knowledge base for the DOJ chatbot.
 
This script loads all text files and structured JSON data from the `data/` folder,
splits them into chunks, creates embeddings using a sentence transformer model,
and stores the vectors in a Chroma vector database (persistent).
 
Usage:
    python ingest.py
 
Prerequisites:
    pip install langchain sentence-transformers chromadb
"""
 
import os
import glob
import json
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
 
# Configuration
DATA_TEXT_DIR = "data"          # folder containing .txt files
PERSIST_DIR = "chroma_db"            # where the vector store will be saved
CHUNK_SIZE = 700                     # characters per chunk
CHUNK_OVERLAP = 100                  # overlap between chunks
 
def load_text_files(directory):
    """Load and return all text from .txt files in the given directory."""
    texts = []
    if not os.path.exists(directory):
        print(f"Warning: Directory '{directory}' not found. Skipping text files.")
        return texts
 
    for filepath in glob.glob(os.path.join(directory, "*.txt")):
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if content:
                texts.append(content)
                print(f"Loaded text file: {os.path.basename(filepath)}")
    return texts
 
def load_structured_json(directory):
    """Load and return all JSON files as readable text."""
    texts = []
    if not os.path.exists(directory):
        print(f"Warning: Directory '{directory}' not found. Skipping JSON files.")
        return texts
 
    for filepath in glob.glob(os.path.join(directory, "*.json")):
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Convert JSON to a pretty string so it's understandable
            json_text = json.dumps(data, indent=2, ensure_ascii=False)
            texts.append(json_text)
            print(f"Loaded JSON file: {os.path.basename(filepath)}")
    return texts
 
def main():
    print("Starting knowledge base creation...")
 
    # 1. Load all data
    all_texts = []
    all_texts.extend(load_text_files(DATA_TEXT_DIR))
    #all_texts.extend(load_structured_json(DATA_STRUCTURED_DIR))
 
    if not all_texts:
        print("No data found! Please add text files or JSON files to the data/ folder.")
        return
 
    print(f"Total documents loaded: {len(all_texts)}")
 
    # 2. Split documents into chunks
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len,
        separators=["\n\n", "\n", " ", ""]
    )
    chunks = text_splitter.create_documents(all_texts)
    print(f"Total chunks created: {len(chunks)}")
 
    # 3. Create embeddings
    # Using a lightweight model good for semantic search
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        model_kwargs={"device": "cuda"},   # will use GPU if available (RTX laptop)
        encode_kwargs={"normalize_embeddings": True}
    )
 
    # 4. Create and persist Chroma vector store
    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=PERSIST_DIR
    )
    vectorstore.persist()
    print(f"Vector store saved to '{PERSIST_DIR}'")
 
if __name__ == "__main__":
    main()