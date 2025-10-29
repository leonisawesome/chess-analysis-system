import requests
import json

# Test queries
test_queries = [
    ("Italian Game", "tell me about the Italian Game"),
    ("Ruy Lopez", "tell me about the Ruy Lopez"),
    ("King's Indian Defense", "tell me about the King's Indian Defense"),
    ("Caro-Kann Defense", "tell me about the Caro-Kann Defense")
]

print("="*80)
print("RAG CONTAMINATION ANALYSIS (Via API Endpoint)")
print("="*80)
print("\nSending diagnostic requests to Flask API...")
print("\nThis will analyze the top 10 retrieved chunks for each query.")
print("="*80)

for opening_name, query in test_queries:
    print(f"\n{'─'*80}")
    print(f"QUERY: {query}")
    print(f"EXPECTED OPENING: {opening_name}")
    print(f"{'─'*80}")
    
    # Send request to diagnostic endpoint (we'll need to add this to app.py)
    response = requests.post(
        "http://127.0.0.1:5001/diagnostic/rag",
        json={"query": query},
        timeout=30
    )
    
    if response.status_code == 200:
        data = response.json()
        
        print(f"\nRETRIEVED {data['total_chunks']} CHUNKS:\n")
        
        for chunk_info in data['chunks']:
            if chunk_info['contaminated']:
                print(f"  Chunk {chunk_info['index']}: ❌ CONTAMINATED")
                print(f"    Book: {chunk_info['book'][:50]}")
                print(f"    Found: {', '.join(chunk_info['found_keywords'])}")
                print(f"    Text preview: {chunk_info['text_preview']}...")
            else:
                print(f"  Chunk {chunk_info['index']}: ✅ Clean (no Sicilian keywords)")
        
        # Summary
        contamination_rate = data['contamination_rate']
        print(f"\n{'='*80}")
        print(f"CONTAMINATION RATE: {data['contaminated_count']}/{data['total_chunks']} ({contamination_rate:.0f}%)")
        print(f"{'='*80}")
        
        if contamination_rate > 30:
            print("⚠️  HIGH CONTAMINATION - RAG filtering recommended")
        elif contamination_rate > 10:
            print("⚠️  MODERATE CONTAMINATION - Consider filtering")
        else:
            print("✅ LOW/NO CONTAMINATION - Problem is likely internal model bias")
    else:
        print(f"❌ ERROR: API returned status {response.status_code}")
        print(f"Response: {response.text}")

print(f"\n{'='*80}")
print("DIAGNOSTIC COMPLETE")
print("="*80)
