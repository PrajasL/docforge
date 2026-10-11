import sys
import os
import time

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from tests.e2e.test_all_12_tools import run_all_12_tools_tests
from tests.e2e.test_edge_cases_security import run_edge_cases_and_security_tests
from tests.e2e.test_ux_seo_accessibility import run_ux_seo_accessibility_tests

def main():
    print("=" * 70)
    print(" DOCFORGE PART 22 — COMPREHENSIVE END-TO-END E2E TEST SUITE ")
    print("=" * 70)
    start_time = time.time()
    all_passed = True
    summary = {}

    try:
        print("\n>>> SUITE 1: ALL 13 PDF TOOLS END-TO-END FLOWS")
        res1 = run_all_12_tools_tests()
        summary["all_12_tools"] = res1
    except Exception as e:
        print(f"FAILED Suite 1: {e}")
        summary["all_12_tools"] = {"error": str(e)}
        all_passed = False

    try:
        print("\n>>> SUITE 2: EDGE CASES & SECURITY")
        res2 = run_edge_cases_and_security_tests()
        summary["edge_cases_security"] = res2
    except Exception as e:
        print(f"FAILED Suite 2: {e}")
        summary["edge_cases_security"] = {"error": str(e)}
        all_passed = False

    try:
        print("\n>>> SUITE 3: UX, SEO & WCAG 2.1 AA ACCESSIBILITY")
        res3 = run_ux_seo_accessibility_tests()
        summary["ux_seo_accessibility"] = res3
    except Exception as e:
        print(f"FAILED Suite 3: {e}")
        summary["ux_seo_accessibility"] = {"error": str(e)}
        all_passed = False

    elapsed = round(time.time() - start_time, 2)
    print("\n" + "=" * 70)
    print(f" FINAL EXECUTION REPORT (Total time: {elapsed}s)")
    print("=" * 70)

    for suite_name, results in summary.items():
        print(f"\n[{suite_name.upper()}]")
        for k, v in results.items():
            print(f"  • {k}: {v}")

    if all_passed:
        print("\n>>> ALL PART 22 E2E TESTS PASSED SUCCESSFULLY! <<<")
        sys.exit(0)
    else:
        print("\n>>> SOME E2E TESTS FAILED! <<<")
        sys.exit(1)

if __name__ == "__main__":
    main()
