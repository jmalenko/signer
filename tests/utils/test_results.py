"""Test results management - organizing and reporting image comparisons."""

from pathlib import Path
from typing import Optional
import json
from datetime import datetime

# Results directory - persists across test runs for inspection
RESULTS_DIR = Path(__file__).parent.parent / "test-results"


def get_test_results_dir() -> Path:
    """Get or create the test results directory."""
    RESULTS_DIR.mkdir(exist_ok=True)
    return RESULTS_DIR


def organize_test_output(
    test_name: str,
    actual_image: str | Path,
    expected_image: str | Path,
    diff_image: Optional[str | Path] = None,
    match: bool = True,
) -> dict:
    """
    Organize test output images in a flat structure.
    
    Creates:
        test-results/
            └── {test_name}/
                ├── {expected_base}_actual.png (actual output, named after expected file)
                ├── {expected_base}_expected.png (reference)
                ├── {expected_base}_diff.png (pixel-level diff: white=same, red=different)
                └── info.json (metadata including pass/fail status)
    
    Args:
        test_name: Name of the test (used for diff and directory)
        actual_image: Path to actual output image
        expected_image: Path to expected reference image
        diff_image: Path to diff visualization
        match: Whether images match (PASS=True, FAIL=False)
    
    Returns:
        Dictionary with paths to all saved files
    """
    results_dir = get_test_results_dir()
    test_dir = results_dir / test_name
    test_dir.mkdir(parents=True, exist_ok=True)
    
    from shutil import copy2
    
    # Extract base filename from expected image (e.g., "document1-signed" from "document1-signed.png")
    expected_image_path = Path(expected_image)
    expected_base = expected_image_path.stem  # Filename without extension
    
    # Simple result tracking - only match status and expected base name for report generation
    results = {
        "match": match,
        "expected_base": expected_base,  # Store for HTML report file lookup
    }
    
    # Copy actual image with _actual suffix, named after expected file
    if actual_image:
        dest = test_dir / f"{expected_base}_actual.png"
        copy2(actual_image, dest)
    
    # Copy expected image with _expected suffix
    if expected_image:
        dest = test_dir / f"{expected_base}_expected.png"
        copy2(expected_image, dest)
    
    # Copy diff image to test directory with name matching expected base
    if diff_image:
        dest = test_dir / f"{expected_base}_diff.png"
        copy2(diff_image, dest)
    
    # Save info file in test directory
    info_file = test_dir / "info.json"
    with open(info_file, "w") as f:
        json.dump(results, f, indent=2)
    
    return results


def create_comparison_report(output_file: Optional[str | Path] = None) -> str:
    """
    Create an HTML report of all test comparisons.
    
    Displays:
    - All test result directories from test-results/
    - Diff visualizations (white=same, red=different)
    - Side-by-side viewer for comparing actual vs expected
    
    Returns:
        Path to the generated HTML file
    """
    results_dir = get_test_results_dir()
    
    if not output_file:
        output_file = results_dir / "report.html"
    else:
        output_file = Path(output_file)
    
    # Scan results directory for test result directories (each with info.json)
    test_results = []
    if results_dir.exists():
        for test_dir in sorted(results_dir.glob("*")):
            if test_dir.is_dir() and (test_dir / "info.json").exists():
                # Only include tests that have actual image files (feature tests with JSON actions)
                # Skip tests that only have info.json but no images (unit tests, non-image tests)
                image_files = list(test_dir.glob("*_actual.png")) + list(test_dir.glob("*_expected.png"))
                if image_files:  # Only include if there are actual images
                    with open(test_dir / "info.json") as f:
                        info = json.load(f)
                    # Add test_name from directory
                    info["test_name"] = test_dir.name
                    test_results.append(info)
    
    # Generate HTML
    html = _generate_html_report(test_results, results_dir)
    
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html)
    
    return str(output_file)


def _generate_html_report(test_results: list, results_dir: Path) -> str:
    """Generate HTML content for test comparison report (supports multi-page results)."""
    import re
    
    # Build test summary list at top
    # First, group results by test name (handling page suffixes)
    grouped_results = {}
    page_pattern = r'(.+)_page(\d+)$'
    
    for result in test_results:
        test_name = result["test_name"]
        match = re.match(page_pattern, test_name)
        
        if match:
            # This is a page result - group it under parent test
            parent_name = match.group(1)
            page_num = match.group(2)
            
            # Check if parent already exists and is single-page - convert it to multi-page
            if parent_name in grouped_results and grouped_results[parent_name]["type"] == "singlepage":
                # Convert existing single-page entry to multi-page (keep parent card, just remove from page list)
                grouped_results[parent_name] = {
                    "type": "multipage",
                    "match": grouped_results[parent_name]["match"],
                    "pages": {}
                }
            elif parent_name not in grouped_results:
                grouped_results[parent_name] = {
                    "type": "multipage",
                    "match": True,  # Will be recalculated after all pages are added
                    "pages": {}
                }
            
            grouped_results[parent_name]["pages"][page_num] = {
                "test_name": test_name,
                "result": result,
                "match": result.get("match", True)
            }
        else:
            # Regular single-page result
            if test_name not in grouped_results:
                grouped_results[test_name] = {
                    "type": "singlepage",
                    "match": result.get("match", True),
                    "result": result
                }
    
    # Recalculate parent test match status - parent fails if ANY page fails
    for test_name_key, group in grouped_results.items():
        if group["type"] == "multipage":
            # Parent test passes only if ALL pages pass
            group["match"] = all(page_info["match"] for page_info in group["pages"].values())
    
    test_list_items = ""
    test_cards = ""
    
    for test_name_key in sorted(grouped_results.keys()):
        group = grouped_results[test_name_key]
        match = group["match"]
        status_class = "status-pass" if match else "status-fail"
        status_text = "✓ PASS" if match else "✗ FAIL"
        
        if group["type"] == "multipage":
            # Multi-page: create parent item and nested page items
            test_list_items += f"""
        <li class="test-list-item {status_class} test-list-parent">
            <a href="#{test_name_key}" class="test-link">
                <span class="status-badge {status_class}">{status_text}</span>
                <span class="test-name" style="user-select: text;">{test_name_key}</span>
            </a>
            <ul class="nested-page-list">
"""
            for page_num in sorted(group["pages"].keys(), key=lambda x: int(x)):
                page_info = group["pages"][page_num]
                page_match = page_info["match"]
                page_status_class = "status-pass" if page_match else "status-fail"
                page_status_text = "✓" if page_match else "✗"
                test_list_items += f"""                <li class="test-list-item {page_status_class} test-list-page">
                    <a href="#{page_info['test_name']}" onclick="showPageFromList('{page_info['test_name']}'); return false;" class="test-link page-link">
                        <span class="status-badge {page_status_class}">{page_status_text}</span>
                        <span class="test-name" style="user-select: text;">Page {page_num}</span>
                    </a>
                </li>
"""
            test_list_items += """            </ul>
        </li>
        """
        else:
            # Single-page: regular item
            result = group["result"]
            test_list_items += f"""
        <li class="test-list-item {status_class}">
            <a href="#{test_name_key}" class="test-link">
                <span class="status-badge {status_class}">{status_text}</span>
                <span class="test-name" style="user-select: text;">{test_name_key}</span>
            </a>
        </li>
        """
    
    # Now add cards for all results
    for result in test_results:
        test_name = result["test_name"]
        
        # Skip parent tests that have multipage variants - only show individual page cards
        if grouped_results.get(test_name, {}).get("type") == "multipage" and not re.match(page_pattern, test_name):
            continue
        
        match = result.get("match", True)
        status_class = "status-pass" if match else "status-fail"
        status_text = "✓ PASS" if match else "✗ FAIL"
        
        test_dir = results_dir / test_name
        expected_base = result.get("expected_base", test_name)
        
        page_files = sorted([f for f in test_dir.glob(f"{expected_base}_actual-p*.png")])
        
        if page_files:
            # Multi-page card
            page_tabs = ""
            page_contents = ""
            
            for page_file in page_files:
                page_num = page_file.stem.split('-p')[-1]
                expected_file = test_dir / f"{expected_base}_expected-p{page_num}.png"
                diff_file = test_dir / f"{expected_base}_diff-p{page_num}.png"
                
                active_class = "active" if page_num == sorted([f.stem.split('-p')[-1] for f in page_files])[0] else ""
                page_tabs += f'<button class="page-tab {active_class}" onclick="showPage(event, \'{test_name}-page{page_num}\')" data-page="{page_num}">Page {page_num}</button>'
                
                actual_rel = f"{test_name}/{page_file.name}" if page_file.exists() else ""
                expected_rel = f"{test_name}/{expected_file.name}" if expected_file.exists() else ""
                diff_rel = f"{test_name}/{diff_file.name}" if diff_file.exists() else ""
                
                display_style = "display: block;" if page_num == sorted([f.stem.split('-p')[-1] for f in page_files])[0] else "display: none;"
                page_content = f"""
                <div id="{test_name}-page{page_num}" class="page-content" style="{display_style}">
                    <div class="image-comparison">
                        <div class="image-item">
                            <h4>Expected</h4>
                            {f'<img src="{expected_rel}" alt="Expected P{page_num}" class="comparison-image clickable-image" data-full-src="{expected_rel}">' if expected_rel else '<p>N/A</p>'}
                        </div>
                        <div class="image-item">
                            <h4>Actual</h4>
                            {f'<img src="{actual_rel}" alt="Actual P{page_num}" class="comparison-image clickable-image" data-full-src="{actual_rel}">' if actual_rel else '<p>N/A</p>'}
                        </div>
                        <div class="image-item">
                            <h4>Diff (Red = Different)</h4>
                            {f'<img src="{diff_rel}" alt="Diff P{page_num}" class="comparison-image clickable-image" data-full-src="{diff_rel}">' if diff_rel else '<p>N/A</p>'}
                        </div>
                    </div>
                </div>
                """
                page_contents += page_content
            
            card = f"""
            <div class="test-card" id="{test_name}">
                <div class="test-header">
                    <h2 class="test-name-header" style="user-select: text;">{test_name}</h2>
                    <span class="status-badge {status_class}">{status_text}</span>
                </div>
                <div class="page-tabs-container">
                    {page_tabs}
                </div>
                {page_contents}
            </div>
            """
            test_cards += card
        else:
            # Single-page card
            actual_file = test_dir / f"{expected_base}_actual.png"
            expected_file = test_dir / f"{expected_base}_expected.png"
            diff_file = test_dir / f"{expected_base}_diff.png"
            
            actual_rel = f"{test_name}/{actual_file.name}" if actual_file.exists() else ""
            expected_rel = f"{test_name}/{expected_file.name}" if expected_file.exists() else ""
            diff_rel = f"{test_name}/{diff_file.name}" if diff_file.exists() else ""
            
            # Check if this is an image-based test or a non-image test
            has_images = actual_rel or expected_rel or diff_rel
            
            if has_images:
                # Image comparison card
                card = f"""
            <div class="test-card" id="{test_name}">
                <div class="test-header">
                    <h2 class="test-name-header" style="user-select: text;">{test_name}</h2>
                    <span class="status-badge {status_class}">{status_text}</span>
                </div>
                <div class="image-comparison">
                    <div class="image-item">
                        <h4>Expected</h4>
                        {f'<img src="{expected_rel}" alt="Expected" class="comparison-image clickable-image" data-full-src="{expected_rel}">' if expected_rel else '<p>N/A</p>'}
                    </div>
                    <div class="image-item">
                        <h4>Actual</h4>
                        {f'<img src="{actual_rel}" alt="Actual" class="comparison-image clickable-image" data-full-src="{actual_rel}">' if actual_rel else '<p>N/A</p>'}
                    </div>
                    <div class="image-item">
                        <h4>Diff (Red = Different)</h4>
                        {f'<img src="{diff_rel}" alt="Diff" class="comparison-image clickable-image" data-full-src="{diff_rel}">' if diff_rel else '<p>N/A</p>'}
                    </div>
                </div>
            </div>
            """
            else:
                # Non-image test card (e.g., feature tests that only report pass/fail)
                status_detail = "All assertions passed" if match else "Test failed"
                card = f"""
            <div class="test-card" id="{test_name}">
                <div class="test-header">
                    <h2 class="test-name-header" style="user-select: text;">{test_name}</h2>
                    <span class="status-badge {status_class}">{status_text}</span>
                </div>
                <div class="non-image-test">
                    <p>{status_detail}</p>
                </div>
            </div>
            """
            test_cards += card
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test Comparison Report</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: #f5f7fa;
                padding: 40px 20px;
            }}
            .container {{
                max-width: 1200px;
                margin: 0 auto;
            }}
            h1 {{
                color: #2c3e50;
                margin-bottom: 30px;
                text-align: center;
            }}
            h2 {{
                color: #34495e;
                margin-bottom: 20px;
            }}
            .test-card {{
                background: white;
                border-radius: 8px;
                padding: 25px;
                margin-bottom: 25px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.08);
                transition: box-shadow 0.2s;
            }}
            .test-card:hover {{
                box-shadow: 0 4px 16px rgba(0,0,0,0.12);
            }}
            .test-list {{
                display: flex;
                flex-direction: column;
                gap: 10px;
                margin-bottom: 30px;
                padding: 20px;
                background: white;
                border-radius: 8px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            }}
            .test-list-item {{
                list-style: none;
            }}
            .test-link {{
                display: flex;
                align-items: center;
                gap: 12px;
                padding: 10px 12px;
                text-decoration: none;
                color: inherit;
                border-radius: 4px;
                transition: background 0.2s;
            }}
            .test-link:hover {{
                background: #f0f0f0;
            }}
            .test-list-item.status-pass .test-link {{
                border-left: 3px solid #27ae60;
            }}
            .test-list-item.status-fail .test-link {{
                border-left: 3px solid #e74c3c;
            }}
            .status-badge {{
                display: inline-block;
                padding: 4px 10px;
                border-radius: 3px;
                font-size: 0.85em;
                font-weight: 600;
                white-space: nowrap;
            }}
            .status-badge.status-pass {{
                background: #d4edda;
                color: #155724;
            }}
            .status-badge.status-fail {{
                background: #f8d7da;
                color: #721c24;
            }}
            .test-list-parent {{
                margin-bottom: 8px;
            }}
            .nested-page-list {{
                list-style: none;
                margin-top: 8px;
                margin-left: 20px;
                padding: 8px 0;
                border-left: 2px solid #ddd;
                padding-left: 16px;
            }}
            .test-list-page {{
                margin-bottom: 6px;
            }}
            .test-list-page .test-link {{
                padding: 8px 10px;
                font-size: 0.95em;
                border-left: 2px solid #bbb;
            }}
            .test-list-page .test-link:hover {{
                border-left-color: #666;
            }}
            .page-link {{
                cursor: pointer;
            }}
            .test-card h2 {{
                margin: 0;
                color: #2c3e50;
            }}
            .test-header {{
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 15px;
                margin-bottom: 12px;
                padding-bottom: 12px;
                border-bottom: 2px solid #e0e0e0;
            }}
            .test-name-header {{
                margin: 0;
                font-size: 1.3em;
                color: #2c3e50;
                flex: 1;
            }}
            .mismatch-info {{
                color: #e74c3c;
                font-weight: 600;
                margin: 8px 0 0 0;
                font-size: 0.95em;
            }}
            .timestamp {{
                color: #7f8c8d;
                font-size: 0.85em;
                margin-bottom: 12px;
            }}
            .image-comparison {{
                display: grid;
                grid-template-columns: 1fr 1fr 1fr;
                gap: 20px;
                margin-top: 15px;
            }}
            .page-tabs-container {{
                display: flex;
                gap: 10px;
                margin-top: 12px;
                padding: 0;
                border-bottom: 2px solid #e0e0e0;
                flex-wrap: wrap;
            }}
            .page-tab {{
                padding: 10px 16px;
                border: none;
                background: transparent;
                cursor: pointer;
                font-size: 0.95em;
                color: #666;
                border-bottom: 3px solid transparent;
                transition: all 0.2s;
            }}
            .page-tab:hover {{
                color: #2c3e50;
                background: #f9f9f9;
            }}
            .page-tab.active {{
                color: #2980b9;
                border-bottom-color: #2980b9;
            }}
            .page-content {{
                margin-top: 15px;
            }}
            .image-item {{
                text-align: center;
            }}
            .image-item h4 {{
                margin: 0 0 12px 0;
                font-size: 0.95em;
                color: #34495e;
                font-weight: 600;
            }}
            .comparison-image {{
                max-width: 100%;
                max-height: 400px;
                border: 1px solid #ddd;
                border-radius: 4px;
                background: #fafafa;
            }}
            .clickable-image {{
                cursor: pointer;
                transition: transform 0.2s;
            }}
            .clickable-image:hover {{
                transform: scale(1.02);
                box-shadow: 0 0 8px rgba(0,0,0,0.2);
            }}
            .non-image-test {{
                padding: 20px;
                background: #f9f9f9;
                border-radius: 4px;
                margin-top: 15px;
                text-align: center;
                font-size: 1em;
            }}
            .non-image-test p {{
                margin: 0;
                color: #555;
            }}
            /* Modal for full-size image viewing */
            .modal {{
                display: none;
                position: fixed;
                z-index: 1000;
                left: 0;
                top: 0;
                width: 100%;
                height: 100%;
                background-color: rgba(0, 0, 0, 0.9);
            }}
            .modal.open {{
                display: flex;
                align-items: center;
                justify-content: center;
            }}
            .modal-content {{
                max-width: 90%;
                max-height: 90%;
                object-fit: contain;
            }}
            .modal-close {{
                position: absolute;
                top: 20px;
                right: 30px;
                font-size: 40px;
                font-weight: bold;
                color: white;
                cursor: pointer;
            }}
            .modal-close:hover {{
                color: #bbb;
            }}
            @media (max-width: 768px) {{
                .image-comparison {{
                    grid-template-columns: 1fr;
                    gap: 15px;
                }}
                body {{
                    padding: 20px 10px;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📊 Test Comparison Report</h1>
            
            <div class="test-list-section">
                <h2 style="margin-top: 0; color: #2c3e50; margin-bottom: 15px;">Test Cases</h2>
                <ul class="test-list">
                    {test_list_items}
                </ul>
            </div>
            
            <div class="results">
                {test_cards}
            </div>
        </div>
        
        <!-- Image Modal -->
        <div id="imageModal" class="modal">
            <span class="modal-close">&times;</span>
            <img class="modal-content" id="modalImage" src="" alt="Full-size image">
        </div>
        
        <script>
            const modal = document.getElementById('imageModal');
            const closeBtn = document.querySelector('.modal-close');
            const clickableImages = document.querySelectorAll('.clickable-image');
            
            clickableImages.forEach(img => {{
                img.addEventListener('click', function() {{
                    modal.classList.add('open');
                    document.getElementById('modalImage').src = this.getAttribute('data-full-src');
                }});
            }});
            
            closeBtn.addEventListener('click', function() {{
                modal.classList.remove('open');
            }});
            
            modal.addEventListener('click', function(e) {{
                if (e.target === modal) {{
                    modal.classList.remove('open');
                }}
            }});
            
            // Close on Escape key
            document.addEventListener('keydown', function(e) {{
                if (e.key === 'Escape' && modal.classList.contains('open')) {{
                    modal.classList.remove('open');
                }}
            }});
            
            // Show/hide page tabs
            function showPage(event, pageId) {{
                // Prevent default link behavior
                if (event && event.preventDefault) {{
                    event.preventDefault();
                }}
                
                // Get the test card - could be from tab button or from list link
                let card;
                if (event && event.target) {{
                    card = event.target.closest('.test-card');
                }}
                
                // If not found from event, extract test name from pageId and find card
                if (!card) {{
                    const testName = pageId.split('-page')[0];
                    card = document.getElementById(testName);
                }}
                
                if (!card) return;
                
                // Hide all page contents in this card
                const pages = card.querySelectorAll('.page-content');
                pages.forEach(page => {{
                    page.style.display = 'none';
                }});
                
                // Remove active class from all tabs
                const tabs = card.querySelectorAll('.page-tab');
                tabs.forEach(tab => {{
                    tab.classList.remove('active');
                }});
                
                // Show the selected page
                const selectedPage = document.getElementById(pageId);
                if (selectedPage) {{
                    selectedPage.style.display = 'block';
                    // Mark the corresponding tab as active if it exists
                    const pageNum = pageId.split('-page')[1];
                    const activeTab = card.querySelector(`[data-page="${{pageNum}}""]`);
                    if (activeTab) {{
                        activeTab.classList.add('active');
                    }}
                }}
            }}
            
            // Navigate to a page from the list and scroll to it
            function showPageFromList(testName) {{
                // Scroll to the test card
                const card = document.getElementById(testName);
                if (card) {{
                    card.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
                }}
            }}
        </script>
    </body>
    </html>
    """
    
    return html
