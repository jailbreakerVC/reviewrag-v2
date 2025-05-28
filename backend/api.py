from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import os
from langchain.chat_models import init_chat_model
from langchain_community.document_loaders import UnstructuredMarkdownLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langgraph.graph import START, StateGraph
from typing_extensions import TypedDict
from langchain import hub
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from dotenv import load_dotenv
from pathlib import Path
import hashlib
import json
import shutil
from contextlib import asynccontextmanager

# Load environment variables
load_dotenv()

# Configuration
CHROMA_DB_PATH = "./chroma_db"
SOURCE_FILE = "results.md"
COLLECTION_NAME = "reviews"
METADATA_FILE = ".metadata.json"

# Global variable to hold the RAG chain
rag_chain = None

# Pydantic models for API
class QuestionRequest(BaseModel):
    question: str
    max_results: Optional[int] = 4

class QuestionResponse(BaseModel):
    answer: str
    sources_count: int
    sources: Optional[List[str]] = None

class HealthResponse(BaseModel):
    status: str
    database_status: str
    source_file_exists: bool

class State(TypedDict):
    question: str
    context: List
    answer: str

def get_file_hash(file_path: str) -> str:
    """Get MD5 hash of a file."""
    try:
        with open(file_path, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    except FileNotFoundError:
        return ""

def should_update_database() -> bool:
    """Check if database needs updating based on source file changes."""
    if not Path(SOURCE_FILE).exists():
        return False

    current_hash = get_file_hash(SOURCE_FILE)

    if not Path(METADATA_FILE).exists():
        return True

    try:
        with open(METADATA_FILE, 'r') as f:
            metadata = json.load(f)
            return metadata.get('file_hash') != current_hash
    except:
        return True

def save_metadata():
    """Save current file hash to metadata."""
    current_hash = get_file_hash(SOURCE_FILE)
    metadata = {'file_hash': current_hash}

    with open(METADATA_FILE, 'w') as f:
        json.dump(metadata, f)

def setup_vector_store():
    """Setup Chroma vector store with persistent storage."""
    try:
        OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
        if not OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
    except Exception as e:
        raise ValueError(f"OpenAI API key configuration error: {str(e)}")

    embeddings = OpenAIEmbeddings(model="text-embedding-3-large")

    # Initialize Chroma with persistent storage
    vector_store = Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=CHROMA_DB_PATH
    )

    # Check if we need to update the database
    if should_update_database():
        print("Source file changed or first run. Updating vector database...")

        if not Path(SOURCE_FILE).exists():
            raise FileNotFoundError(f"Source file {SOURCE_FILE} not found")

        # Clear existing data
        try:
            vector_store.delete_collection()
            vector_store = Chroma(
                collection_name=COLLECTION_NAME,
                embedding_function=embeddings,
                persist_directory=CHROMA_DB_PATH
            )
        except:
            pass  # Collection might not exist yet

        # Load and split documents
        loader = UnstructuredMarkdownLoader(file_path=SOURCE_FILE)
        docs = loader.load()

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=800,
            chunk_overlap=150
        )
        all_splits = text_splitter.split_documents(docs)

        # Add documents to vector store
        vector_store.add_documents(all_splits)

        # Save metadata
        save_metadata()

        print(f"Added {len(all_splits)} documents to vector store.")
    else:
        print("Using existing vector database (no changes detected).")

    return vector_store

def create_rag_chain():
    """Create and return the RAG chain."""
    vector_store = setup_vector_store()
    model = init_chat_model("gpt-4o-mini", model_provider="openai")
    prompt = hub.pull("rlm/rag-prompt")

    def retrieve(state: State):
        retrieved_docs = vector_store.similarity_search(
            state["question"],
            k=3  # Number of documents to retrieve
        )
        return {"context": retrieved_docs}

    def generate(state: State):
        docs_content = "\n\n".join(doc.page_content for doc in state["context"])
        messages = prompt.invoke({
            "question": state["question"] + "\nAfter the answer, send a json object with the final device name",
            "context": docs_content
        })
        response = model.invoke(messages)
        return {"answer": response.content}

    graph_builder = StateGraph(State).add_sequence([retrieve, generate])
    graph_builder.add_edge(START, "retrieve")

    return graph_builder.compile()

def reset_database():
    """Reset the vector database - useful for development."""
    if Path(CHROMA_DB_PATH).exists():
        shutil.rmtree(CHROMA_DB_PATH)
        print(f"Removed {CHROMA_DB_PATH}")

    if Path(METADATA_FILE).exists():
        os.remove(METADATA_FILE)
        print(f"Removed {METADATA_FILE}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize RAG chain on startup."""
    global rag_chain
    try:
        print("Initializing RAG chain...")
        rag_chain = create_rag_chain()
        print("RAG chain initialized successfully!")
        yield
    except Exception as e:
        print(f"Failed to initialize RAG chain: {str(e)}")
        raise
    finally:
        print("Shutting down...")

# Initialize FastAPI app
app = FastAPI(
    title="RAG Question Answering API",
    description="API for asking questions about device reviews using RAG",
    version="1.0.0",
    lifespan=lifespan
)

@app.get("/", response_model=dict)
async def root():
    """Root endpoint with API information."""
    return {
        "message": "RAG Question Answering API",
        "version": "1.0.0",
        "endpoints": {
            "ask": "/ask - POST request to ask questions",
            "health": "/health - GET request for health check",
            "reset": "/reset - POST request to reset database"
        }
    }

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    global rag_chain

    return HealthResponse(
        status="healthy" if rag_chain is not None else "unhealthy",
        database_status="exists" if Path(CHROMA_DB_PATH).exists() else "missing",
        source_file_exists=Path(SOURCE_FILE).exists()
    )

@app.post("/ask", response_model=QuestionResponse)
async def ask_question(request: QuestionRequest):
    """Ask a question using the RAG system."""
    global rag_chain

    if rag_chain is None:
        raise HTTPException(status_code=503, detail="RAG chain not initialized")

    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    try:
        # Run the RAG chain
        response = rag_chain.invoke({
            "question": request.question
        })

        # Extract source information
        sources = []
        if "context" in response:
            sources = [doc.page_content[:100] + "..." if len(doc.page_content) > 100
                      else doc.page_content for doc in response["context"]]

        return QuestionResponse(
            answer=response["answer"],
            sources_count=len(response.get("context", [])),
            sources=sources
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing question: {str(e)}")

@app.post("/reset")
async def reset_database_endpoint():
    """Reset the vector database."""
    global rag_chain

    try:
        reset_database()
        # Reinitialize the RAG chain
        rag_chain = create_rag_chain()
        return {"message": "Database reset and RAG chain reinitialized successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error resetting database: {str(e)}")

@app.get("/status")
async def get_status():
    """Get detailed status information."""
    return {
        "rag_chain_initialized": rag_chain is not None,
        "database_path": CHROMA_DB_PATH,
        "database_exists": Path(CHROMA_DB_PATH).exists(),
        "source_file": SOURCE_FILE,
        "source_file_exists": Path(SOURCE_FILE).exists(),
        "metadata_file_exists": Path(METADATA_FILE).exists(),
        "openai_api_key_configured": bool(os.getenv('OPENAI_API_KEY'))
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
