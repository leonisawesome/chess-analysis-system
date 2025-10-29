#!/usr/bin/env python3
"""
Debug script to capture GPT-5 Stage 1 raw response
"""
import os
import json
from openai import OpenAI

# Initialize OpenAI client
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# Sample prompt (simplified version from app.py stage1_generate_outline)
query = "tell me about the Italian Game"
context = "The Italian Game begins with 1.e4 e5 2.Nf3 Nc6 3.Bc4..."

prompt = f"""You are a chess instructor creating a comprehensive guide. Based on the user's question and reference material, create a structured outline.

User Question: {query}

Reference Material:
{context}

Create a JSON outline with 5-7 sections. Each section should have:
- title: A clear section heading (e.g., "Overview", "Strategic Themes", "Main Variations", "Key Plans", "Common Tactics")
- bullets: 3-5 bullet points summarizing key information for that section
- diagram_anchor: A standard diagram position for this section

Return ONLY valid JSON in this exact format:
{{
  "sections": [
    {{"title": "Overview", "bullets": ["...", "...", "..."], "diagram_anchor": "[ANCHOR: Italian Game - 1.e4 e5 2.Nf3 Nc6 3.Bc4]"}},
    {{"title": "Strategic Themes", "bullets": ["...", "..."], "diagram_anchor": "[ANCHOR: Typical Italian pawn structure]"}},
    ...
  ]
}}"""

print("=" * 80)
print("DEBUG: GPT-5 STAGE 1 RESPONSE FORMAT INVESTIGATION")
print("=" * 80)
print()
print("Sending request to GPT-5...")
print()

try:
    response = client.chat.completions.create(
        model="gpt-chatgpt-4o-latest-20250514",
        messages=[{"role": "user", "content": prompt}],
        max_completion_tokens=1500
    )
    
    raw_response = response.choices[0].message.content
    
    print("=" * 80)
    print("RAW GPT-5 RESPONSE (FULL):")
    print("=" * 80)
    print(raw_response)
    print()
    print("=" * 80)
    print(f"Response length: {len(raw_response)} characters")
    print("=" * 80)
    print()
    
    # Try to parse as JSON
    print("Attempting direct JSON parse...")
    try:
        outline = json.loads(raw_response)
        print("✅ SUCCESS: Response is valid JSON")
        print(f"   Sections: {len(outline.get('sections', []))}")
    except json.JSONDecodeError as e:
        print(f"❌ FAIL: JSON parse error: {e}")
        print()
        
        # Try stripping markdown code fences
        print("Attempting to strip markdown code fences...")
        cleaned_response = raw_response
        if "```json" in raw_response:
            print("   Found ```json marker")
            cleaned_response = raw_response.split("```json")[1].split("```")[0]
        elif "```" in raw_response:
            print("   Found ``` marker")
            cleaned_response = raw_response.split("```")[1].split("```")[0]
        
        try:
            outline = json.loads(cleaned_response.strip())
            print("✅ SUCCESS after stripping code fences")
            print(f"   Sections: {len(outline.get('sections', []))}")
        except json.JSONDecodeError as e2:
            print(f"❌ STILL FAILS: {e2}")
    
except Exception as e:
    print(f"❌ API ERROR: {e}")

print()
print("=" * 80)
print("DEBUG COMPLETE")
print("=" * 80)
