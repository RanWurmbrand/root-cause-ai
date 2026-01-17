# test_code_applier_first.py

import tempfile
from pathlib import Path

def test_first_orphan():
    # The actual file content
    file_content = '''    const solutionServerGroup = view
          .locator('.pf-v6-c-form__group')
          .filter({ has: view.getByText('Solution Server', { exact: true }) })
          .first();

     const solutionServerInput = solutionServerGroup.locator('#feature-solution-server');
    const solutionServerLabel = solutionServerGroup.locator('label[for="feature-solution-server"]');'''

    # Big block from AI (like the problematic patch)
    old_lines = [
        "          .first();",
        "",
        "     const solutionServerInput = solutionServerGroup.locator('#feature-solution-server');",
        "    const solutionServerLabel = solutionServerGroup.locator('label[for=\"feature-solution-server\"]');",
    ]

    new_lines = [
        "          .first();",
        "",
        "     const solutionServerInput = solutionServerGroup.locator('#feature-solution-server');",
        "    const solutionServerLabel = solutionServerGroup.locator('label.pf-v6-c-switch[for=\"feature-solution-server\"]');",
    ]

    with tempfile.NamedTemporaryFile(mode='w', suffix='.ts', delete=False) as f:
        f.write(file_content)
        temp_path = Path(f.name)

    from core.code_applier import CodeApplier
    applier = CodeApplier.__new__(CodeApplier)
    result = applier._find_and_replace_in_file(temp_path, old_lines, new_lines)

    actual = temp_path.read_text()
    temp_path.unlink()

    print(f"Success: {result}")
    print(f"\n--- Actual ---\n{actual}")
    
    # Check .first() is not orphaned
    if ".first();" in actual:
        lines = actual.splitlines()
        for i, line in enumerate(lines):
            if line.strip() == ".first();":
                if i == 0 or not lines[i-1].strip():
                    print(f"\n❌ ERROR: .first() is orphaned on line {i+1}")
                    return
        print(f"\n✓ .first() is properly attached")

if __name__ == "__main__":
    test_first_orphan()