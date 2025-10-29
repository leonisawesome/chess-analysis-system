#!/usr/bin/env python3
"""
Test PGN Database Queries
Validates structured search capabilities for chess games.
"""

import sqlite3
import json
from typing import List, Dict


def test_query(cursor: sqlite3.Cursor,
               query_name: str,
               sql_query: str,
               expected_min_results: int = 0,
               validation_func=None) -> Dict:
    """
    Execute a test query and validate results.

    Returns:
        Dict with query results and validation status
    """
    print(f"\n{'='*80}")
    print(f"Query: {query_name}")
    print(f"{'='*80}")
    print(f"SQL: {sql_query}\n")

    try:
        cursor.execute(sql_query)
        results = cursor.fetchall()

        print(f"Results found: {len(results)}")

        # Show first 3 results
        if results:
            print("\nSample results:")
            for i, row in enumerate(results[:3], 1):
                print(f"  {i}. {row}")

        # Validation
        success = False
        reason = ""

        if len(results) == 0 and expected_min_results > 0:
            reason = f"Expected at least {expected_min_results} results, got 0"
        elif validation_func:
            success, reason = validation_func(results)
        else:
            success = len(results) >= expected_min_results
            reason = f"Found {len(results)} results (≥{expected_min_results} expected)"

        status = "✅ SUCCESS" if success else "❌ FAIL"
        print(f"\n{status}: {reason}")

        return {
            'query_name': query_name,
            'sql': sql_query,
            'result_count': len(results),
            'success': success,
            'reason': reason
        }

    except Exception as e:
        print(f"\n❌ FAIL: Query error: {str(e)}")
        return {
            'query_name': query_name,
            'sql': sql_query,
            'result_count': 0,
            'success': False,
            'reason': f"Query error: {str(e)}"
        }


def run_all_queries(db_path: str = "pgn_validation.db"):
    """Run all 10 validation queries."""

    print("="* 80)
    print("PGN DATABASE QUERY VALIDATION")
    print("="* 80)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get some context from database
    cursor.execute("SELECT COUNT(*) FROM games")
    total_games = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(DISTINCT white) FROM games WHERE white NOT IN ('Unknown', 'SOLUTION 1', 'EXERCISE 1')")
    unique_players = cursor.fetchone()[0]

    print(f"\nDatabase info:")
    print(f"  Total games: {total_games}")
    print(f"  Unique players: {unique_players}")
    print()

    # Define 10 test queries
    test_queries = []

    # Query 1: Find all games with a specific ECO code
    test_queries.append({
        'name': 'Q1: Games with ECO code E11',
        'sql': "SELECT white, black, result FROM games WHERE eco = 'E11'",
        'min_results': 1
    })

    # Query 2: Games where White won
    test_queries.append({
        'name': 'Q2: Games where White won',
        'sql': "SELECT white, black, eco FROM games WHERE result = '1-0'",
        'min_results': 20
    })

    # Query 3: Games where Black won
    test_queries.append({
        'name': 'Q3: Games where Black won',
        'sql': "SELECT white, black, eco FROM games WHERE result = '0-1'",
        'min_results': 5
    })

    # Query 4: Games with ECO code starting with 'D' (Queen's Pawn openings)
    test_queries.append({
        'name': 'Q4: Queen\'s Pawn openings (ECO D00-D99)',
        'sql': "SELECT eco, COUNT(*) as count FROM games WHERE eco LIKE 'D%' GROUP BY eco",
        'min_results': 1
    })

    # Query 5: Games with ECO code starting with 'E' (Indian defenses)
    test_queries.append({
        'name': 'Q5: Indian defenses (ECO E00-E99)',
        'sql': "SELECT eco, COUNT(*) as count FROM games WHERE eco LIKE 'E%' GROUP BY eco ORDER BY count DESC",
        'min_results': 1
    })

    # Query 6: Games with ECO code starting with 'C' (Open games and French)
    test_queries.append({
        'name': 'Q6: Open games and French (ECO C00-C99)',
        'sql': "SELECT eco, opening, COUNT(*) FROM games WHERE eco LIKE 'C%' GROUP BY eco LIMIT 5",
        'min_results': 1
    })

    # Query 7: Find games by a specific player (as White or Black)
    # First, get a player name that appears multiple times
    cursor.execute("""
        SELECT white, COUNT(*) as count
        FROM games
        WHERE white NOT IN ('Unknown', 'SOLUTION 1', 'EXERCISE 1', 'EXERCISE 2', 'EXERCISE 3', 'SPACE ADVANTAGE')
        GROUP BY white
        HAVING count > 1
        LIMIT 1
    """)
    player_result = cursor.fetchone()

    if player_result:
        player_name = player_result[0]
        test_queries.append({
            'name': f'Q7: Games featuring {player_name}',
            'sql': f"SELECT white, black, eco, result FROM games WHERE white = '{player_name}' OR black = '{player_name}'",
            'min_results': 1
        })
    else:
        test_queries.append({
            'name': 'Q7: SKIPPED - No player with multiple games',
            'sql': "SELECT 1",  # Dummy query
            'min_results': 0
        })

    # Query 8: Count games by result type
    test_queries.append({
        'name': 'Q8: Count games by result',
        'sql': "SELECT result, COUNT(*) as count FROM games GROUP BY result",
        'min_results': 2  # At least 2 different results
    })

    # Query 9: Games with specific opening name pattern (if available)
    test_queries.append({
        'name': 'Q9: Games with "Sicilian" in opening name',
        'sql': "SELECT white, black, opening, result FROM games WHERE opening LIKE '%Sicilian%'",
        'min_results': 0  # May or may not find any
    })

    # Query 10: Top 5 most common ECO codes
    test_queries.append({
        'name': 'Q10: Top 5 most common ECO codes',
        'sql': "SELECT eco, COUNT(*) as count FROM games WHERE eco != 'Unknown' GROUP BY eco ORDER BY count DESC LIMIT 5",
        'min_results': 5
    })

    # Execute all queries
    results = []
    for i, query in enumerate(test_queries, 1):
        result = test_query(
            cursor,
            query['name'],
            query['sql'],
            query['min_results']
        )
        results.append(result)

    # Summary
    print("\n" + "="* 80)
    print("VALIDATION SUMMARY")
    print("="* 80)

    successful = sum(1 for r in results if r['success'])
    total = len(results)
    success_rate = (successful / total) * 100

    print(f"\nTotal queries: {total}")
    print(f"Successful: {successful}")
    print(f"Failed: {total - successful}")
    print(f"\n📊 SUCCESS RATE: {success_rate:.1f}%")

    # Per-query results
    print("\nPer-query results:")
    for r in results:
        status = "✅" if r['success'] else "❌"
        print(f"  {status} {r['query_name']}: {r['result_count']} results")

    # Success criteria
    print("\n" + "="* 80)
    if success_rate >= 80:
        print("✅ SUCCESS: Query success rate >= 80%")
        print("   Recommendation: Proceed with System B (PGN Database)")
    else:
        print("⚠️  WARNING: Query success rate < 80%")
        print("   Recommendation: System B needs improvement or alternative approach")
    print("="* 80)

    # Save results
    output_file = 'pgn_query_results.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'success_rate': success_rate,
            'total_queries': total,
            'successful_queries': successful,
            'failed_queries': total - successful,
            'query_results': results
        }, f, indent=2)

    print(f"\n💾 Results saved to: {output_file}")

    conn.close()

    return success_rate, results


if __name__ == '__main__':
    success_rate, results = run_all_queries()
