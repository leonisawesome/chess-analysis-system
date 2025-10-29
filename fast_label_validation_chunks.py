#!/usr/bin/env python3
"""
Fast labeling: Label only chunks that appear in validation query results
This is much faster than labeling all 580 chunks
"""

from openai import OpenAI
from qdrant_client import QdrantClient
import numpy as np
import json
import os
from collections import Counter

# Initialize
openai_client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
qdrant_client = QdrantClient(path="./qdrant_validation_db")

EMBEDDING_MODEL = "text-embedding-3-small"
COLLECTION_NAME = "chess_validation"

QUERIES = [
    "How do I improve my calculation in the middlegame?",
    "What are the main ideas in the French Defense?",
    "When should I trade pieces in the endgame?",
    "How do I create weaknesses in my opponent's position?",
    "What is the best way to study chess openings?",
    "How do I defend against aggressive attacks?",
    "What endgame principles should beginners learn first?",
    "How do I improve my positional understanding?",
    "When is it correct to sacrifice material?",
    "How do I convert a winning position?",
]


def embed(text):
    response = openai_client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=text
    )
    return np.array(response.data[0].embedding)


def get_validation_chunks():
    """Get all chunks that appear in top 40 for any validation query"""

    all_chunk_ids = set()

    for query in QUERIES:
        vector = embed(query)
        results = qdrant_client.search(
            collection_name=COLLECTION_NAME,
            query_vector=vector.tolist(),
            limit=40
        )

        for result in results:
            all_chunk_ids.add(result.id)

    # Retrieve full chunk data
    chunks = []
    for chunk_id in all_chunk_ids:
        point = qdrant_client.retrieve(
            collection_name=COLLECTION_NAME,
            ids=[chunk_id]
        )[0]

        chunks.append({
            'id': point.id,
            'text': point.payload.get('text', ''),
            'book_name': point.payload.get('book_name', ''),
            'chapter_title': point.payload.get('chapter_title', '')
        })

    return chunks


def label_chunk_batch(chunks):
    """Label a batch of chunks"""

    prompt = """Classify each chunk as: method/theory/example/pgn

**Categories:**
- **method**: How-to instructions, practical advice, training methods
- **theory**: Concepts, principles, strategic understanding
- **example**: Annotated games, positions with analysis
- **pgn**: Move notation, variations

Chunks:
"""

    for i, chunk in enumerate(chunks, 1):
        text_preview = chunk['text'][:250].replace('\n', ' ')
        prompt += f"{i}. {text_preview}...\n"

    prompt += """\nJSON format:
[{"chunk_num": 1, "intent": "method", "confidence": "high"}, ...]

Output:"""

    try:
        response = openai_client.chat.completions.create(
            model="gpt-5",
            messages=[{"role": "user", "content": prompt}]
        )

        result_text = response.choices[0].message.content.strip()
        if result_text.startswith('```'):
            result_text = result_text.split('```')[1]
            if result_text.startswith('json'):
                result_text = result_text[4:]

        labels = json.loads(result_text)

        results = []
        for label in labels:
            chunk_num = label['chunk_num'] - 1
            if chunk_num < len(chunks):
                results.append({
                    'chunk_id': chunks[chunk_num]['id'],
                    'intent': label['intent'],
                    'confidence': label['confidence']
                })
        return results

    except Exception as e:
        print(f"Error: {e}")
        return [{'chunk_id': c['id'], 'intent': 'theory', 'confidence': 'low'}
                for c in chunks]


def main():
    print("="*80)
    print("FAST LABELING: Validation Chunks Only")
    print("="*80)

    # Get chunks that appear in validation queries
    print("Collecting chunks from validation queries...")
    chunks = get_validation_chunks()
    print(f"Found {len(chunks)} unique chunks across all queries")
    print()

    # Label in batches of 16
    BATCH_SIZE = 16
    all_labels = []

    for i in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[i:i+BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1
        total_batches = (len(chunks) + BATCH_SIZE - 1) // BATCH_SIZE

        print(f"Batch {batch_num}/{total_batches}: Labeling {len(batch)} chunks...")

        labels = label_chunk_batch(batch)
        all_labels.extend(labels)

        # Update Qdrant
        for label in labels:
            qdrant_client.set_payload(
                collection_name=COLLECTION_NAME,
                payload={
                    'intent': label['intent'],
                    'intent_confidence': label['confidence']
                },
                points=[label['chunk_id']]
            )

    print("\n" + "="*80)
    print("LABELING COMPLETE")
    print("="*80)

    # Distribution
    intent_counts = Counter(l['intent'] for l in all_labels)
    print(f"\nLabeled {len(all_labels)} chunks")
    print("\nIntent Distribution:")
    for intent, count in sorted(intent_counts.items(), key=lambda x: -x[1]):
        pct = count / len(all_labels) * 100
        print(f"  {intent}: {count} ({pct:.1f}%)")

    # Save
    with open('validation_chunk_labels.json', 'w') as f:
        json.dump(all_labels, f, indent=2)

    print("\nSaved to: validation_chunk_labels.json")
    print("\nReady to run Phase 2 testing!")


if __name__ == "__main__":
    main()
