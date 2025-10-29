#!/usr/bin/env python3
"""
Test GPT-5 access with correct parameters
"""

from openai import OpenAI
import os

client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))

# Try different GPT-5 variants and parameter combinations
models_to_test = [
    "gpt-5",
    "gpt-5-mini",
    "gpt-5-nano",
    "o1",
    "o1-mini"
]

print("="*80)
print("TESTING GPT-5 ACCESS")
print("="*80)

for model in models_to_test:
    print(f"\nTrying {model}...")

    # Try WITHOUT max_tokens (GPT-5/o1 might not support it)
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Say 'test successful'"}]
            # No max_tokens parameter
        )
        print(f"✓ SUCCESS with {model}")
        print(f"Response: {response.choices[0].message.content}")
        print(f"This is the model to use!")
        break
    except Exception as e:
        error_msg = str(e)
        if "does not exist" in error_msg or "404" in error_msg:
            print(f"✗ Model not found: {model}")
        elif "max_tokens" in error_msg:
            print(f"⚠️  Model exists but parameter issue: {model}")
            print(f"   Error: {error_msg[:100]}")
        elif "access" in error_msg.lower():
            print(f"⚠️  Access restricted: {model}")
            print(f"   Error: {error_msg[:100]}")
        else:
            print(f"✗ Error: {error_msg[:150]}")

print("\n" + "="*80)
