import os
from openai import OpenAI
from qdrant_client import QdrantClient
from query_system_a import COLLECTION_NAME, QDRANT_PATH, embed_query

# Initialize
api_key = os.getenv('OPENAI_API_KEY')
openai_client = OpenAI(api_key=api_key)
qdrant_client = QdrantClient(path=QDRANT_PATH)

# Test the Italian Game query
query = "tell me about the Italian Game"
print(f"\nQUERY: {query}")
print("="*80)

# Get embedding and search
query_vector = embed_query(openai_client, query)
results = qdrant_client.search(
    collection_name=COLLECTION_NAME,
    query_vector=query_vector,
    limit=10
)

print(f"\nRETRIEVED {len(results)} CHUNKS FROM QDRANT:\n")

# Sicilian keywords to check
sicilian_keywords = ['sicilian', '1.e4 c5', 'najdorf', 'dragon', 'sveshnikov', '1...c5']
contaminated_count = 0

for i, result in enumerate(results):
    text = result.payload.get('text', '').lower()
    book = result.payload.get('book_name', 'Unknown')
    
    # Check for Sicilian content
    found = [kw for kw in sicilian_keywords if kw in text]
    
    if found:
        contaminated_count += 1
        print(f"Chunk {i+1}: ❌ CONTAMINATED")
        print(f"  Book: {book[:60]}")
        print(f"  Sicilian keywords found: {', '.join(found)}")
        print(f"  Text preview: {text[:150]}...")
    else:
        print(f"Chunk {i+1}: ✅ CLEAN (no Sicilian keywords)")
        print(f"  Book: {book[:60]}")
    print()

print("="*80)
print(f"CONTAMINATION RATE: {contaminated_count}/10 ({contaminated_count*10}%)")
print("="*80)

if contaminated_count >= 3:
    print("\n⚠️  HIGH CONTAMINATION - RAG is feeding Sicilian content to GPT-4o")
    print("→ Implement ChatGPT's hybrid approach with RAG filtering")
elif contaminated_count >= 1:
    print("\n⚠️  MODERATE CONTAMINATION - Some Sicilian chunks present")
    print("→ Consider light RAG filtering + per-section retry")
else:
    print("\n✅ RAG IS CLEAN - Problem is GPT-4o internal bias")
    print("→ Implement Gemini's per-section validation & retry")
