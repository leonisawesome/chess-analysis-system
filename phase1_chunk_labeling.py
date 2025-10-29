#!/usr/bin/env python3
"""
Phase 1: Chunk Intent Labeling
Labels all chunks as method/theory/example/pgn for intent-aware reranking
"""

from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct
import json
import os
import time
from collections import Counter

# Initialize clients
openai_client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
qdrant_client = QdrantClient(path="./qdrant_validation_db")

COLLECTION_NAME = "chess_validation"
BATCH_SIZE = 16  # Process 16 chunks per API call


def label_chunk_batch(chunks):
    """
    Label a batch of chunks using GPT-5

    Returns: list of dicts with chunk_id, intent, confidence
    """

    prompt = """You are a chess content classifier. For each chunk of text, classify it into ONE of these categories:

**Categories:**
- **method**: How-to instructions, step-by-step guidance, training methods, practical advice on improvement
- **theory**: Conceptual explanations, strategic principles, positional understanding, general theory
- **example**: Annotated games, tactical problems, specific positions with analysis
- **pgn**: Move notation, game scores, variations (primarily move sequences)

**Instructions:**
1. Read each chunk carefully
2. Assign the single best-fitting category
3. Provide confidence: high/medium/low
4. Respond with JSON list

**Examples:**

Chunk: "To improve your calculation, practice visualizing 3-4 moves ahead. Start with tactical puzzles..."
Label: method, Confidence: high
(Reason: Direct how-to advice)

Chunk: "The French Defense is characterized by the pawn structure e6-d5, often leading to closed positions..."
Label: theory, Confidence: high
(Reason: Conceptual explanation)

Chunk: "1.e4 e6 2.d4 d5 3.Nc3 Bb4 4.e5 c5 5.a3 Bxc3+ 6.bxc3 Ne7 7.Qg4..."
Label: pgn, Confidence: high
(Reason: Move notation)

Chunk: "Karpov-Kasparov, 1985: After 24.Qd3, White threatens both Qh7+ and Rd1. Black defended with 24...Rf8..."
Label: example, Confidence: high
(Reason: Annotated game)

**Chunks to classify:**
"""

    for i, chunk in enumerate(chunks, 1):
        text_preview = chunk['text'][:300].replace('\n', ' ')
        prompt += f"\n{i}. {text_preview}...\n"

    prompt += """\n**Output format (JSON list):**
[
  {"chunk_num": 1, "intent": "method", "confidence": "high"},
  {"chunk_num": 2, "intent": "theory", "confidence": "medium"},
  ...
]

Output only valid JSON:"""

    try:
        response = openai_client.chat.completions.create(
            model="gpt-5",
            messages=[{"role": "user", "content": prompt}]
        )

        result_text = response.choices[0].message.content.strip()

        # Parse JSON
        if result_text.startswith('```'):
            result_text = result_text.split('```')[1]
            if result_text.startswith('json'):
                result_text = result_text[4:]

        labels = json.loads(result_text)

        # Map back to chunk IDs
        results = []
        for label in labels:
            chunk_num = label['chunk_num'] - 1  # 0-indexed
            if chunk_num < len(chunks):
                results.append({
                    'chunk_id': chunks[chunk_num]['id'],
                    'intent': label['intent'],
                    'confidence': label['confidence']
                })

        return results

    except Exception as e:
        print(f"Error labeling batch: {e}")
        # Return default labels
        return [{'chunk_id': c['id'], 'intent': 'theory', 'confidence': 'low'}
                for c in chunks]


def get_all_chunks():
    """Retrieve all chunks from Qdrant"""

    # Scroll through all points
    offset = None
    all_chunks = []

    while True:
        results, offset = qdrant_client.scroll(
            collection_name=COLLECTION_NAME,
            limit=100,
            offset=offset,
            with_payload=True,
            with_vectors=False
        )

        for point in results:
            all_chunks.append({
                'id': point.id,
                'text': point.payload.get('text', ''),
                'book_name': point.payload.get('book_name', ''),
                'chapter_title': point.payload.get('chapter_title', '')
            })

        if offset is None:
            break

    return all_chunks


def update_chunk_labels(labels):
    """Update Qdrant points with intent labels"""

    for label in labels:
        try:
            qdrant_client.set_payload(
                collection_name=COLLECTION_NAME,
                payload={
                    'intent': label['intent'],
                    'intent_confidence': label['confidence']
                },
                points=[label['chunk_id']]
            )
        except Exception as e:
            print(f"Error updating chunk {label['chunk_id']}: {e}")


def label_all_chunks():
    """Main function to label all chunks"""

    print("="*80)
    print("PHASE 1: CHUNK INTENT LABELING")
    print("="*80)
    print()

    # Get all chunks
    print("Retrieving all chunks from Qdrant...")
    chunks = get_all_chunks()
    print(f"Retrieved {len(chunks)} chunks")
    print()

    # Process in batches
    num_batches = (len(chunks) + BATCH_SIZE - 1) // BATCH_SIZE
    print(f"Processing {num_batches} batches ({BATCH_SIZE} chunks per batch)")
    print()

    all_labels = []

    for i in range(0, len(chunks), BATCH_SIZE):
        batch_num = i // BATCH_SIZE + 1
        batch = chunks[i:i+BATCH_SIZE]

        print(f"Batch {batch_num}/{num_batches}: Labeling {len(batch)} chunks...")

        labels = label_chunk_batch(batch)
        all_labels.extend(labels)

        # Update Qdrant
        print(f"  Updating Qdrant with labels...")
        update_chunk_labels(labels)

        # Rate limiting
        time.sleep(1)

        # Progress update
        if batch_num % 5 == 0:
            intent_counts = Counter(l['intent'] for l in all_labels)
            print(f"\n  Progress: {len(all_labels)}/{len(chunks)} chunks labeled")
            print(f"  Distribution so far: {dict(intent_counts)}")
            print()

    print("\n" + "="*80)
    print("LABELING COMPLETE")
    print("="*80)

    # Final distribution
    intent_counts = Counter(l['intent'] for l in all_labels)
    confidence_counts = Counter(l['confidence'] for l in all_labels)

    print(f"\nTotal chunks labeled: {len(all_labels)}")
    print()
    print("Intent Distribution:")
    for intent, count in sorted(intent_counts.items(), key=lambda x: -x[1]):
        percentage = count / len(all_labels) * 100
        print(f"  {intent}: {count} ({percentage:.1f}%)")

    print()
    print("Confidence Distribution:")
    for conf, count in sorted(confidence_counts.items(), key=lambda x: -x[1]):
        percentage = count / len(all_labels) * 100
        print(f"  {conf}: {count} ({percentage:.1f}%)")

    # Save results
    with open('chunk_labels.json', 'w') as f:
        json.dump(all_labels, f, indent=2)

    print()
    print("Results saved to: chunk_labels.json")

    # Spot check examples
    print()
    print("="*80)
    print("SPOT CHECK: Sample Labels")
    print("="*80)

    # Sample 10 random chunks
    import random
    sample_indices = random.sample(range(len(chunks)), min(10, len(chunks)))

    for idx in sample_indices:
        chunk = chunks[idx]
        label = all_labels[idx]

        print(f"\nChunk ID: {chunk['id']}")
        print(f"Book: {chunk['book_name']}")
        print(f"Chapter: {chunk['chapter_title']}")
        print(f"Intent: {label['intent']} (confidence: {label['confidence']})")
        print(f"Text: {chunk['text'][:200]}...")
        print("-" * 40)

    return all_labels


if __name__ == "__main__":
    labels = label_all_chunks()

    print("\n" + "="*80)
    print("NEXT STEP")
    print("="*80)
    print("\nPhase 1 complete! Proceed to Phase 2:")
    print("- Implement two-stage reranking")
    print("- Test on all 10 validation queries")
