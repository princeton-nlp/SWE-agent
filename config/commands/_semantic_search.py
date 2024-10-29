import sys
import os
from pathlib import Path
import torch
from transformers import AutoTokenizer, AutoModel
import numpy as np

def load_model():
    # Using a smaller model for efficiency, can be changed to more powerful ones
    model_name = "sentence-transformers/all-MiniLM-L6-v2"
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModel.from_pretrained(model_name)
    return tokenizer, model

def get_embedding(text, tokenizer, model):
    inputs = tokenizer(text, padding=True, truncation=True, return_tensors="pt")
    with torch.no_grad():
        outputs = model(**inputs)
    return outputs.last_hidden_state.mean(dim=1).squeeze().numpy()

def semantic_search(query, directory):
    tokenizer, model = load_model()
    query_embedding = get_embedding(query, tokenizer, model)

    results = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.startswith('.'):
                continue

            filepath = Path(root) / file
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Get embedding for file content
                content_embedding = get_embedding(content[:512], tokenizer, model)  # Limit content length

                # Calculate similarity
                similarity = np.dot(query_embedding, content_embedding) / (
                    np.linalg.norm(query_embedding) * np.linalg.norm(content_embedding)
                )

                results.append((filepath, similarity))
            except:
                continue

    # Sort by similarity and return top results
    results.sort(key=lambda x: x[1], reverse=True)

    # Print top 5 results
    print(f"\nTop semantic matches for query: '{query}'")
    for filepath, score in results[:5]:
        rel_path = os.path.relpath(filepath, directory)
        print(f"{rel_path} (score: {score:.3f})")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python _semantic_search.py <query> <directory>")
        sys.exit(1)

    query = sys.argv[1]
    directory = sys.argv[2]
    semantic_search(query, directory)