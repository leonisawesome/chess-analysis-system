import os
from openai import OpenAI
from qdrant_client import QdrantClient
from query_system_a import COLLECTION_NAME, QDRANT_PATH, embed_query

# Initialize clients
api_key = os.getenv('OPENAI_API_KEY')
openai_client = OpenAI(api_key=api_key)
qdrant_client = QdrantClient(path=QDRANT_PATH)

# Test queries
test_queries = [
    ("Italian Game", "tell me about the Italian Game"),
    ("Ruy Lopez", "tell me about the Ruy Lopez"),
    ("King's Indian Defense", "tell me about the King's Indian Defense"),
    ("Caro-Kann Defense", "tell me about the Caro-Kann Defense")
]

print("="*80)
print("RAG CONTAMINATION ANALYSIS")
print("="*80)

for opening_name, query in test_queries:
    print(f"\n{'─'*80}")
    print(f"QUERY: {query}")
    print(f"EXPECTED OPENING: {opening_name}")
    print(f"{'─'*80}")
    
    # Embed query
    query_vector = embed_query(openai_client, query)
    
    # Search Qdrant (top 10 chunks)
    results = qdrant_client.search(
        collection_name=COLLECTION_NAME,
        query_vector=query_vector,
        limit=10
    )
    
    # Analyze results for Sicilian contamination
    sicilian_keywords = ['sicilian', '1.e4 c5', 'najdorf', 'dragon', 'sveshnikov']
    contaminated_chunks = 0
    
    print(f"\nRETRIEVED {len(results)} CHUNKS:\n")
    
    for i, result in enumerate(results):
        payload = result.payload
        text = payload.get('text', '').lower()
        book = payload.get('book_name', 'Unknown')
        
        # Check for Sicilian keywords
        found_keywords = [kw for kw in sicilian_keywords if kw in text]
        
        if found_keywords:
            contaminated_chunks += 1
            print(f"  Chunk {i+1}: ❌ CONTAMINATED")
            print(f"    Book: {book[:50]}")
            print(f"    Found: {', '.join(found_keywords)}")
            print(f"    Text preview: {text[:100]}...")
        else:
            print(f"  Chunk {i+1}: ✅ Clean (no Sicilian keywords)")
    
    # Summary
    contamination_rate = (contaminated_chunks / len(results)) * 100
    print(f"\n{'='*80}")
    print(f"CONTAMINATION RATE: {contaminated_chunks}/{len(results)} ({contamination_rate:.0f}%)")
    print(f"{'='*80}")
    
    if contamination_rate > 30:
        print("⚠️  HIGH CONTAMINATION - RAG filtering recommended")
    elif contamination_rate > 10:
        print("⚠️  MODERATE CONTAMINATION - Consider filtering")
    else:
        print("✅ LOW/NO CONTAMINATION - Problem is likely internal model bias")

print(f"\n{'='*80}")
print("DIAGNOSTIC COMPLETE")
print("="*80)
