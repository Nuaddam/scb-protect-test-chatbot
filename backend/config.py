from dotenv import load_dotenv
import os

load_dotenv()

# vector store settings
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_ENVIRONMENT = os.getenv("PINECONE_ENVIRONMENT", "us-east-1")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "rag-scb-index")

# openai settings
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-large")

# document source directory
DOC_SOURCE_DIR = os.getenv("DOC_SOURCE_DIR", "./documents")

