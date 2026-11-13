import pickle
import faiss
import os

# Function to validate Pickle file
def validate_pickle(pkl_file):
    try:
        with open(pkl_file, 'rb') as f:
            data = pickle.load(f)
        print("Pickle file loaded successfully!")
        # If it's a large object, print the type or a sample to inspect
        print(f"Data type: {type(data)}")
    except Exception as e:
        print(f"Error loading pickle file: {e}")

# Function to validate FAISS file
def validate_faiss(faiss_file):
    try:
        # Load the FAISS index
        index = faiss.read_index(faiss_file)
        print("FAISS index loaded successfully!")
        # Check the number of vectors in the FAISS index
        print(f"Number of vectors in the FAISS index: {index.ntotal}")
    except Exception as e:
        print(f"Error loading FAISS index: {e}")

# Main function to validate both files
def main():
    pkl_file = 'index.pkl'  # Replace with your pickle file name
    faiss_file = 'index.faiss'  # Replace with your FAISS file name

    # Validate Pickle file
    validate_pickle(pkl_file)

    # Validate FAISS file
    validate_faiss(faiss_file)

# Run the script
if __name__ == "__main__":
    main()
