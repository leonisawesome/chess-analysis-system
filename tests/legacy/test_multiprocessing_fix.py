"""
Test multiprocessing-safe detector compilation fix
Validates that the detector works correctly in worker processes
"""
import sys
import os
import multiprocessing as mp
sys.path.insert(0, '/Users/leon/Downloads/python/chess-analysis-system/chess_rag_system')

def worker_task(args):
    """Worker function that tests detector in subprocess"""
    content, worker_id = args
    try:
        from analysis.instructional_detector import InstructionalLanguageDetector
        print(f'Worker {worker_id} (PID {os.getpid()}): Initializing detector...')
        detector = InstructionalLanguageDetector()
        compiled_count = len(detector._compiled) if hasattr(detector, '_compiled') else 0
        print(f'Worker {worker_id}: Compiled {compiled_count} patterns')
        if compiled_count == 0:
            return {'worker': worker_id, 'error': 'No patterns compiled', 'score': 0.0}
        score = detector.analyze_instructional_language([content])
        print(f'Worker {worker_id}: Score {score:.3f}')
        return {'worker': worker_id, 'pid': os.getpid(), 'compiled_count': compiled_count, 'score': score, 'error': None}
    except Exception as e:
        print(f'Worker {worker_id} failed: {e}')
        import traceback
        traceback.print_exc()
        return {'worker': worker_id, 'error': str(e), 'score': 0.0}

def test_multiprocessing_detector():
    """Test detector across multiple processes"""
    print('=== MULTIPROCESSING DETECTOR TEST ===')
    test_content = 'In the Semi-Slav, the idea is to improve the worst piece while preventing counterplay. After Nf3, we can overprotect the center and build pressure.'
    tasks = [(test_content, i) for i in range(3)]
    try:
        mp.set_start_method('spawn', force=True)
        print(f'Main process PID: {os.getpid()}')
        print('Starting 3 worker processes...')
        with mp.Pool(processes=3) as pool:
            results = pool.map(worker_task, tasks)
        print('\n=== RESULTS ===')
        success_count = 0
        total_score = 0.0
        for result in results:
            if result.get('error'):
                print(f"❌ Worker {result['worker']}: ERROR - {result['error']}")
            else:
                print(f"✅ Worker {result['worker']} (PID {result['pid']}): {result['compiled_count']} patterns, score {result['score']:.3f}")
                success_count += 1
                total_score += result['score']
        if success_count == 3:
            avg_score = total_score / success_count
            print(f'\n🎯 SUCCESS: All 3 workers completed successfully')
            print(f'📊 Average score: {avg_score:.3f} (target: >0.6)')
            if avg_score >= 0.6:
                print('🎉 MULTIPROCESSING TEST PASSED - Pattern detection works in all workers!')
                assert True
            else:
                print('⚠️  Scores too low - pattern detection may have issues')
                assert False
        else:
            print(f'\n❌ FAILURE: Only {success_count}/3 workers succeeded')
            assert False
    except Exception as e:
        print(f'\n❌ MULTIPROCESSING TEST FAILED: {e}')
        import traceback
        traceback.print_exc()
        assert False
if __name__ == '__main__':
    print('MULTIPROCESSING DETECTOR COMPILATION TEST')
    print('Tests the comprehensive fix for multiprocessing pattern compilation')
    print('=' * 70)
    success = test_multiprocessing_detector()
    if success:
        print('\n🎯 MULTIPROCESSING FIX VALIDATED - READY FOR FULL EVS EVALUATION')
        exit(0)
    else:
        print('\n❌ MULTIPROCESSING ISSUES DETECTED - NEEDS FURTHER DEBUGGING')
        exit(1)