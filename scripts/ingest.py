import argparse

from app.services.ingestion_service import ingest_documents


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest docs into FAISS for Net-RAG")
    parser.add_argument("--input-dir", required=True, help="Path to docs directory")
    args = parser.parse_args()

    result = ingest_documents(args.input_dir)
    print(result)


if __name__ == "__main__":
    main()
