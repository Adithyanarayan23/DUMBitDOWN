"""
Script to load scientific papers dataset, create embeddings, and build FAISS index.
"""
import os
from datasets import load_dataset
from langchain_community.embeddings import HuggingFaceEmbeddings
try:
    from langchain.text_splitter import RecursiveCharacterTextSplitter
except ImportError:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
import time

# Configuration
DATASET_NAME = "ccdv/pubmed-summarization"  # Much smaller scientific papers dataset
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"  # Good balance of speed and quality
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
OUTPUT_DIR = "vector_store"  # Must match Settings.vector_store_path / API load path
SAMPLE_SIZE = 1250   # Adjust based on your needs and compute resources

def load_research_papers():
    """Load scientific papers from HuggingFace dataset with retry logic."""
    print(f"Loading dataset {DATASET_NAME}...")
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            dataset = load_dataset(
                DATASET_NAME, 
                split="train", 
                trust_remote_code=True,
                num_proc=4  # Parallel processing
            )
            print(f"Loaded {len(dataset)} papers. Taking a sample of {SAMPLE_SIZE} papers.")
            
            # Take a sample to work with
            sample_dataset = dataset.select(range(min(SAMPLE_SIZE, len(dataset))))
            return sample_dataset
            
        except Exception as e:
            print(f"Attempt {attempt+1}/{max_retries} failed: {e}")
            if attempt < max_retries - 1:
                print("Retrying in 5 seconds...")
                time.sleep(5)
            else:
                print("Max retries reached. Please check your connection.")
                return None

def prepare_documents(dataset):
    """Convert scientific papers dataset to LangChain documents and split into chunks."""
    if dataset is None:
        print("No dataset available to process.")
        return []
    
    documents = []
    
    # Create documents from dataset
    print(f"\nCreating documents from {len(dataset)} papers...")
    print("Note: Re-ingest only needed when changing embedding settings or SAMPLE_SIZE.")
    print("Scholar title-search links work without re-ingest for demos.")
    for i, paper in enumerate(dataset):
        # For armanc/scientific_papers, use article and abstract fields
        if 'article' in paper and paper['article']:
            # Format with title, abstract, and article text
            title = paper.get('title', 'Untitled')
            abstract = paper.get('abstract', '')
            article = paper['article']
            
            content = f"Title: {title}\n\nAbstract: {abstract}\n\nArticle: {article}"
        elif 'abstract' in paper and paper['abstract']:
            # Fallback to just title and abstract if article isn't available
            title = paper.get('title', 'Untitled')
            abstract = paper['abstract']
            
            content = f"Title: {title}\n\nAbstract: {abstract}"
        else:
            # Skip papers with no usable content
            continue
        
        # Create LangChain document with metadata
        paper_id = paper.get("id") or paper.get("article_id") or f"paper_{i}"
        title = paper.get("title", "Unknown Title")
        abstract = paper.get("abstract", "") or ""
        snippet_src = abstract or content
        snippet = snippet_src[:300] + ("..." if len(snippet_src) > 300 else "")

        doc = Document(
            page_content=content,
            metadata={
                "id": str(paper_id),
                "source": str(paper_id),
                "title": title,
                "section": paper.get("section", "Unknown Section"),
                "snippet": snippet,
                "abstract": abstract[:500] if abstract else None,
            },
        )
        documents.append(doc)
        
        # Print progress
        if (i + 1) % 100 == 0:
            print(f"Processed {i + 1} papers...")
    
    if not documents:
        print("No valid documents created. Check dataset content.")
        return []
    
    # Split documents into chunks
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""]
    )
    
    print("Splitting documents into chunks...")
    splits = text_splitter.split_documents(documents)
    print(f"Created {len(splits)} document chunks")
    
    return splits

def create_vector_store(documents):
    """Create and save FAISS vector store."""
    if not documents:
        print("No documents to create vector store from.")
        return None
    
    print("\nInitializing embedding model...")
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    
    print(f"Creating FAISS index with {len(documents)} document chunks...")
    start_time = time.time()
    vector_store = FAISS.from_documents(documents, embeddings)
    end_time = time.time()
    print(f"FAISS index created in {end_time - start_time:.2f} seconds")
    
    # Create output directory if it doesn't exist
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Save the vector store
    print(f"Saving vector store to {OUTPUT_DIR}...")
    vector_store.save_local(OUTPUT_DIR)
    print("Vector store saved successfully!")
    
    return vector_store

def test_retrieval(vector_store):
    """Test the retrieval functionality."""
    if vector_store is None:
        print("No vector store available for testing.")
        return
    
    print("\nTesting retrieval functionality...")
    query = "The impact of climate change on biodiversity"
    print(f"Query: '{query}'")
    
    try:
        docs = vector_store.similarity_search(query, k=3)
        
        print("\nRetrieved documents:")
        for i, doc in enumerate(docs):
            print(f"\n--- Document {i+1} ---")
            print(f"Source: {doc.metadata.get('source', 'Unknown')}")
            print(f"Title: {doc.metadata.get('title', 'Unknown')}")
            print(f"Content preview: {doc.page_content[:150]}...")
    except Exception as e:
        print(f"Error during retrieval test: {e}")

if __name__ == "__main__":
    print("=== Scientific Papers FAISS Index Builder ===")
    print(f"Using dataset: {DATASET_NAME}")
    
    # Load dataset
    dataset = load_research_papers()
    
    # Prepare documents
    document_chunks = prepare_documents(dataset)
    
    # Create and save vector store
    vector_store = create_vector_store(document_chunks)
    
    # Test retrieval
    test_retrieval(vector_store)
    
    print("\nDone! Your FAISS index is ready to use.")