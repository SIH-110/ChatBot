from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

PERSIST_DIR = "chroma_db"

def main():

    # 1. Load the same embedding model used during ingestion
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        model_kwargs={"device": "cuda"},
        encode_kwargs={"normalize_embeddings": True}
    )

    # 2. Load existing Chroma database
    vectorstore = Chroma(
        persist_directory=PERSIST_DIR,
        embedding_function=embeddings
    )

    # 3. Ask a question
    query = input("\nAsk your DOJ chatbot: ")

    # 4. Retrieve relevant documents
    results = vectorstore.similarity_search_with_score(
        query,
        k=5
    )

    print("\n" + "=" * 80)
    print("RETRIEVED RESULTS")
    print("=" * 80)

    for i, (doc, score) in enumerate(results, start=1):

        print(f"\nRESULT {i}")
        print(f"Score: {score}")
        print("-" * 80)
        print(doc.page_content[:1500])
        print("-" * 80)


if __name__ == "__main__":
    main()
    