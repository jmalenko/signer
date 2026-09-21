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

import json
import sys
import webbrowser
from pathlib import Path
from shutil import copy2

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.utils.test_results import create_comparison_report, get_test_results_dir


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
            
            # Check for multi-page results
            page_files = sorted([f for f in test_dir.glob("*_actual-p*.png")])
            if page_files:
                print(f"    Pages: {len(page_files)}")
                for page_file in page_files:
                    page_num = page_file.stem.split('-p')[-1]
                    print(f"      Page {page_num}: ✓ actual, expected, diff")
            else:
                # Single-page display
                if (test_dir / f"{info.get('expected_base', test_dir.name)}_actual.png").exists():
                    print("    ✓ actual.png")
                if (test_dir / f"{info.get('expected_base', test_dir.name)}_expected.png").exists():
                    print("    ✓ expected.png")
                if (test_dir / f"{info.get('expected_base', test_dir.name)}_diff.png").exists():
                    print("    ✓ diff.png")


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
    
    Supports both single-page and multi-page results.
    For multi-page, copies all page files (e.g., *-p1.png, *-p2.png, etc.)
    """
    results_dir = get_test_results_dir()
    test_dir = results_dir / test_name
    
    if not test_dir.exists():
        print(f"❌ No results found for test '{test_name}'")
        return
    
    # Check for multi-page results (e.g., actual_actual-p1.png, actual_actual-p2.png, etc.)
    actual_pages = sorted([f for f in test_dir.glob("*_actual-p*.png")])
    
    if actual_pages:
        # Multi-page copy
        print(f"✓ Copying {len(actual_pages)} pages for test '{test_name}':")
        for actual_page in actual_pages:
            # Convert actual_actual-p1.png → actual_expected-p1.png
            expected_page = actual_page.parent / actual_page.name.replace("_actual-", "_expected-")
            
            # Backup original expected if it exists
            if expected_page.exists():
                backup = expected_page.with_stem(expected_page.stem + "-backup")
                copy2(expected_page, backup)
            
            # Copy actual to expected
            copy2(actual_page, expected_page)
            page_num = actual_page.stem.split('-p')[-1]
            print(f"  Page {page_num}: {actual_page.name} → {expected_page.name}")
    else:
        # Single-page copy (legacy)
        actual = test_dir / "actual.png"
        expected = test_dir / "expected.png"
        
        if not actual.exists():
            print(f"❌ No actual results found for test '{test_name}'")
            return
        
        # Backup original expected
        if expected.exists():
            backup = expected.with_stem(expected.stem + "-backup")
            copy2(expected, backup)
            print(f"  Backup created: {backup.name}")
        
        # Copy actual to expected
        copy2(actual, expected)
        print(f"✓ Copied actual.png → expected.png for test '{test_name}'")


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
