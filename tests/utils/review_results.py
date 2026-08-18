#!/usr/bin/env python
"""
Helper script to inspect and manage test results.

Usage:
    python tests/utils/review_results.py [command] [test_name]

Commands:
    report          - Generate HTML report of all results
    list            - List all test results
    open            - Open HTML report in default browser
    copy-to-expected - Copy actual result to expected reference (requires test_name)
"""

import sys
from pathlib import Path
import json
import webbrowser
from shutil import copy2

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.utils.test_results import get_test_results_dir, create_comparison_report


def list_results():
    """List all test results."""
    results_dir = get_test_results_dir()
    results = sorted([d for d in results_dir.glob("*") if d.is_dir()])
    
    if not results:
        print("No test results found.")
        return
    
    print(f"\n📊 Test Results in {results_dir}:")
    print("-" * 60)
    
    for test_dir in results:
        info_file = test_dir / "info.json"
        if info_file.exists():
            with open(info_file) as f:
                info = json.load(f)
            
            files = info.get("files", {})
            file_count = len([k for k in files.keys() if k != "info"])
            print(f"\n  {test_dir.name}")
            print(f"    Timestamp: {info.get('timestamp', 'N/A')}")
            print(f"    Files: {file_count}")
            
            if files.get("actual"):
                print(f"    ✓ actual.png")
            if files.get("expected"):
                print(f"    ✓ expected.png")
            if files.get("diff"):
                print(f"    ✓ diff.png")
            if files.get("side-by-side"):
                print(f"    ✓ side-by-side.png")


def generate_report():
    """Generate HTML report."""
    report_path = create_comparison_report()
    print(f"✓ Report generated: {report_path}")
    return report_path


def open_report():
    """Open HTML report in default browser."""
    report_path = generate_report()
    webbrowser.open(f"file://{Path(report_path).absolute()}")
    print("✓ Report opened in browser")


def copy_to_expected(test_name):
    """Copy actual result to expected reference.
    
    This is useful when you've verified the changes are correct
    and want to make them the new reference.
    """
    results_dir = get_test_results_dir()
    test_dir = results_dir / test_name
    
    actual = test_dir / "actual.png"
    expected = test_dir / "expected.png"
    
    if not actual.exists():
        print(f"❌ No actual.png found for test '{test_name}'")
        return
    
    # Backup original expected
    if expected.exists():
        backup = expected.with_stem(expected.stem + "-backup")
        copy2(expected, backup)
        print(f"  Backup created: {backup.name}")
    
    # Copy actual to expected
    copy2(actual, expected)
    print(f"✓ Copied actual.png → expected.png for test '{test_name}'")
    
    # Also update reference in fixtures if it exists
    fixture_expected = Path(__file__).parent.parent / "fixtures" / f"{test_name}_actions-expected" / f"{test_name.split('_')[0]}-signed.png"
    if fixture_expected.exists():
        copy2(expected, fixture_expected)
        print(f"✓ Also updated fixture: {fixture_expected.name}")


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Test Results Manager")
        print(__doc__)
        return
    
    command = sys.argv[1]
    
    if command == "report":
        generate_report()
    elif command == "open":
        open_report()
    elif command == "list":
        list_results()
    elif command == "copy-to-expected":
        if len(sys.argv) < 3:
            print("Usage: python review_results.py copy-to-expected <test_name>")
            print("\nAvailable tests:")
            list_results()
            return
        copy_to_expected(sys.argv[2])
    else:
        print(f"Unknown command: {command}")
        print(__doc__)


if __name__ == "__main__":
    main()
