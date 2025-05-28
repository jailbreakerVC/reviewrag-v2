import os
from langchain.chat_models import init_chat_model
from langchain_community.document_loaders import UnstructuredMarkdownLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langgraph.graph import START, StateGraph
from typing_extensions import List, TypedDict
from langchain import hub
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from dotenv import load_dotenv
from pathlib import Path
import hashlib

load_dotenv()

CHROMA_DB_PATH = "./chroma_db"
SOURCE_FILE = "results.md"
COLLECTION_NAME = "reviews"
METADATA_FILE = ".metadata.json"

try:
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

except:
    print("NO OPEN AI API KEY FOUND")


def get_file_hash(file_path: str) -> str:
    with open(file_path, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()

def should_update_database() -> bool:
    import json

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
    import json

    current_hash = get_file_hash(SOURCE_FILE)
    metadata = {'file_hash': current_hash}

    with open(METADATA_FILE, 'w') as f:
        json.dump(metadata, f)


def setup_vector_store():
    """Setup Chroma vector store with persistent storage."""
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
            chunk_size=1000,
            chunk_overlap=200
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

class State(TypedDict):
    question:str
    context: List
    answer: str

def create_rag_chain():

    vector_store = setup_vector_store()

    model = init_chat_model("gpt-4o-mini", model_provider="openai")
    prompt = hub.pull("rlm/rag-prompt")

    def retrieve(state: State):
        retrieved_docs = vector_store.similarity_search(
            state["question"],
            k=4  # Number of documents to retrieve
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
    import shutil

    if Path(CHROMA_DB_PATH).exists():
        shutil.rmtree(CHROMA_DB_PATH)
        print(f"Removed {CHROMA_DB_PATH}")

    if Path(METADATA_FILE).exists():
        os.remove(METADATA_FILE)
        print(f"Removed {METADATA_FILE}")

if __name__ == "__main__":
    rag_chain = create_rag_chain()
    question = input("Enter the question?")
    response = rag_chain.invoke({
    "question" : f"{question}"
    })

    print(f'Context: {response["context"]}\n\n')
    print(f'Answer: {response["answer"]}\n')
    print(f'Sources used: {len(response["context"])} documents')
