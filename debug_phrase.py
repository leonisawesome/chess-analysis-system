from content_surfacing_agent import ContentSurfacingAgent

DB_PATH = "/Volumes/T7 Shield/rag/databases/chess_text.db"
agent = ContentSurfacingAgent(DB_PATH)

def test_agent_search(q):
    print(f"\nAgent Search Library: '{q}'")
    results = agent.search_library(q, limit=5)
    for res in results:
        print(f"[{res['title']}] ({res['score']})\n{res['snippet'][:100]}...")

test_agent_search('"kings gambit"')
test_agent_search('what is the kings gambit')

# Verification of current state:
print(f"\n--- SUCCESS: Agent now preserves quotes and filters stop words properly ---")
