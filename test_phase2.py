"""
Phase 2: ECO Code Detection Testing
Tests the detect_opening() function against 50+ test cases
"""

import json
from opening_data import detect_opening

def run_tests():
    # Load test cases
    with open('phase2_eco_tests.json', 'r') as f:
        test_cases = json.load(f)

    results = []
    passed = 0
    failed = 0

    print("=" * 80)
    print("Phase 2: ECO Code Detection Testing")
    print("=" * 80)
    print()

    for i, test in enumerate(test_cases, 1):
        query = test['query']
        expected_eco = test['expected_eco']
        expected_name = test['expected_name']

        # Run detection
        detected_name, detected_signature, detected_eco = detect_opening(query)

        # Check if detection passed
        eco_match = detected_eco == expected_eco
        name_match = detected_name == expected_name
        passed_test = eco_match and name_match

        # Store result
        result = {
            'test_number': i,
            'query': query,
            'expected_eco': expected_eco,
            'expected_name': expected_name,
            'detected_eco': detected_eco,
            'detected_name': detected_name,
            'detected_signature': detected_signature,
            'eco_match': eco_match,
            'name_match': name_match,
            'passed': passed_test
        }
        results.append(result)

        # Update counters
        if passed_test:
            passed += 1
            status = "✅ PASS"
        else:
            failed += 1
            status = "❌ FAIL"

        # Print result
        print(f"Test {i:2d}: {status}")
        print(f"  Query: {query}")
        print(f"  Expected: {expected_name} (ECO: {expected_eco})")

        if not passed_test:
            print(f"  Detected: {detected_name} (ECO: {detected_eco})")
            if not eco_match:
                print(f"    ❌ ECO mismatch: expected {expected_eco}, got {detected_eco}")
            if not name_match:
                print(f"    ❌ Name mismatch: expected {expected_name}, got {detected_name}")

        print()

    # Calculate pass rate
    total = len(test_cases)
    pass_rate = (passed / total) * 100 if total > 0 else 0

    # Print summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total tests: {total}")
    print(f"Passed: {passed} ✅")
    print(f"Failed: {failed} ❌")
    print(f"Pass rate: {pass_rate:.1f}%")
    print()

    if pass_rate >= 90:
        print("🎉 SUCCESS: Pass rate meets 90% target!")
    else:
        print(f"⚠️  WARNING: Pass rate below 90% target (need {int(0.9 * total)} passes)")

    print("=" * 80)

    # Save results to JSON
    output = {
        'summary': {
            'total_tests': total,
            'passed': passed,
            'failed': failed,
            'pass_rate': pass_rate
        },
        'test_results': results
    }

    with open('phase2_results.json', 'w') as f:
        json.dump(output, f, indent=2)

    print()
    print("Results saved to phase2_results.json")

if __name__ == '__main__':
    run_tests()
