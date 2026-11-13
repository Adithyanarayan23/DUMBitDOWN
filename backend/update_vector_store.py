"""
Script to update an existing FAISS vector store with new documents,
ignoring chunks that might already be present in the vector store.
"""

import os
import numpy as np
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from datasets import load_dataset
import time

# Config
DATASET_NAME = "ccdv/arxiv-summarization"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"  # Good balance of speed and quality
OUTPUT_DIR = "vector_store/"  # Make sure this matches your existing vector store path
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
SAMPLE_SIZE = 1250
SIMILARITY_THRESHOLD = 0.8  # Lowered threshold to be more selective about what's considered a duplicate

def load_dataset_sample():
    """Load and sample dataset."""
    print(f"Loading dataset {DATASET_NAME}...")
    dataset = load_dataset(DATASET_NAME, split="train")
    print(f"Loaded {len(dataset)} papers. Taking a sample of {SAMPLE_SIZE} papers.")
    return dataset.select(range(min(SAMPLE_SIZE, len(dataset))))

def prepare_documents(dataset):
    """Prepare documents by splitting into chunks."""
    documents = []
    
    # Create documents from dataset
    print(f"\nCreating documents from {len(dataset)} papers...")
    for i, paper in enumerate(dataset):
        if 'article' in paper and paper['article']:
            title = paper.get('title', 'Untitled')
            abstract = paper.get('abstract', '')
            article = paper['article']
            
            content = f"Title: {title}\n\nAbstract: {abstract}\n\nArticle: {article}"
        elif 'abstract' in paper and paper['abstract']:
            title = paper.get('title', 'Untitled')
            abstract = paper['abstract']
            
            content = f"Title: {title}\n\nAbstract: {abstract}"
        else:
            continue
        
        doc = Document(
            page_content=content,
            metadata={
                "source": paper.get("id", f"paper_{i}"),
                "title": paper.get("title", "Unknown Title")
            }
        )
        documents.append(doc)
        
        # Print progress
        if (i + 1) % 100 == 0:
            print(f"Processed {i + 1} papers...")
    
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

def is_duplicate(chunk, vector_store, embeddings):
    """Check if a chunk is a duplicate in the FAISS vector store."""
    try:
        # Get embeddings for the current chunk
        chunk_embedding = embeddings.embed_documents([chunk.page_content])[0]
        
        # Search for similar documents in the vector store
        # Using k=3 to get more context on similarity distribution
        results = vector_store.similarity_search_with_score(chunk.page_content, k=3)
        
        if results:
            # We get a tuple of (doc, score) from similarity_search_with_score
            top_result, score = results[0]
            
            # IMPORTANT: For FAISS with L2 (Euclidean) distance, smaller scores are better
            # For cosine similarity, we need to convert the score
            # This adjustment is based on how FAISS is configured in LangChain
            
            # Debug information - comment out or remove in production
            print(f"Debug - Top similarity score: {score}, Content: {top_result.page_content[:50]}...")
            
            # For L2 distance (default in FAISS), smaller is more similar
            # A reasonable threshold for L2 distance would be:
            return score < 1e-15  # Adjust this threshold based on your observations
            
            # If using cosine similarity configuration in FAISS:
            # similarity = 1 - score
            # return similarity >= SIMILARITY_THRESHOLD
    except Exception as e:
        print(f"Error checking for duplicates: {e}")
        # If there's any error, let's be safe and consider it not a duplicate
    
    return False

def update_vector_store():
    """Update an existing FAISS vector store with new chunks."""
    # Initialize embeddings
    print("\nInitializing embedding model...")
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    
    if not os.path.exists(OUTPUT_DIR):
        print(f"FAISS index not found at {OUTPUT_DIR}. Creating directory...")
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        print("Creating new vector store...")
        vector_store = FAISS.from_documents([], embeddings)
        print("Empty vector store created.")
    else:
        print(f"Loading existing FAISS vector store from {OUTPUT_DIR}...")
        try:
            vector_store = FAISS.load_local(OUTPUT_DIR, embeddings, allow_dangerous_deserialization=True)
            print(f"Loaded existing vector store with {vector_store.index.ntotal} entries.")
        except Exception as e:
            print(f"Error loading vector store: {e}")
            print("Creating new vector store...")
            vector_store = FAISS.from_documents([], embeddings)
            print("Empty vector store created.")
    
    # Added debug section to understand similarity distribution
    if vector_store.index.ntotal > 0:
        print("\nTesting similarity scoring with a few examples...")
        # Create a few test documents
        test_docs = [
            Document(page_content="This is a completely new and unrelated document about artificial intelligence."),
            # Add more test documents as needed
        ]
        for doc in test_docs:
            results = vector_store.similarity_search_with_score(doc.page_content, k=3)
            if results:
                print(f"Test document similarity scores: {[score for _, score in results]}")
    
    # Load new dataset sample and prepare documents
    dataset = load_dataset_sample()
    new_documents = prepare_documents(dataset)
    
    print(f"\nPreparing {len(new_documents)} new chunks for the vector store...")
    
    if not new_documents:
        print("No new chunks to add.")
        return
    
    # Filter out duplicate chunks
    print("Filtering out duplicate chunks (this may take a while)...")
    unique_documents = []
    skipped_count = 0
    
    # Process in batches with progress reporting
    batch_size = 100  # Adjust based on your needs
    total_batches = (len(new_documents) + batch_size - 1) // batch_size
    
    for batch_index in range(total_batches):
        start_idx = batch_index * batch_size
        end_idx = min((batch_index + 1) * batch_size, len(new_documents))
        batch_docs = new_documents[start_idx:end_idx]
        
        print(f"Processing batch {batch_index + 1}/{total_batches} ({start_idx} to {end_idx})...")
        batch_unique = 0
        batch_duplicates = 0
        
        for chunk in batch_docs:
            # Only check for duplicates if the vector store actually has content
            if vector_store.index.ntotal > 0 and is_duplicate(chunk, vector_store, embeddings):
                skipped_count += 1
                batch_duplicates += 1
            else:
                unique_documents.append(chunk)
                batch_unique += 1
        
        # Report progress after each batch
        print(f"Batch {batch_index + 1} complete. Unique in this batch: {batch_unique}, Duplicates: {batch_duplicates}")
        print(f"Running totals - Unique: {len(unique_documents)}, Duplicates: {skipped_count}")
    
    print(f"Filtered out {skipped_count} duplicate chunks.")
    if not unique_documents:
        print("No unique chunks to add.")
        return
    
    # Add unique documents to the existing FAISS index
    print(f"Adding {len(unique_documents)} unique chunks to the vector store...")
    start_time = time.time()
    
    # Process in batches to avoid memory issues
    add_batch_size = 500  # Adjust based on your system's memory
    for i in range(0, len(unique_documents), add_batch_size):
        batch = unique_documents[i:i+add_batch_size]
        print(f"Adding batch of {len(batch)} documents ({i} to {i+len(batch)-1})...")
        vector_store.add_documents(batch)
    
    end_time = time.time()
    print(f"Added {len(unique_documents)} new chunks in {end_time - start_time:.2f} seconds.")
    
    # Save the updated vector store
    print(f"Saving updated vector store to {OUTPUT_DIR}...")
    vector_store.save_local(OUTPUT_DIR)
    print("Updated vector store saved successfully!")
    print(f"Vector store now contains {vector_store.index.ntotal} entries.")

if __name__ == "__main__":
    print("=== FAISS Vector Store Updater ===")
    update_vector_store()
    print("\nDone! Your FAISS vector store has been updated.")