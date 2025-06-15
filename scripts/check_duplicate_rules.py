#!/usr/bin/env python3
"""CI check to prevent duplicate rule configuration files.

This script fails if multiple rule configuration files are detected,
ensuring config/rules.yaml remains the single canonical source.
"""

import sys
from pathlib import Path
from typing import List


def find_rule_files(root_dir: Path) -> List[Path]:
    """Find all potential rule configuration files."""
    rule_files = []
    
    # Search for rules.yaml files
    for file_path in root_dir.rglob("rules.yaml"):
        # Skip test files and temporary directories
        if any(part.startswith('.') or part in ['__pycache__', 'tests', 'temp'] 
               for part in file_path.parts):
            continue
        rule_files.append(file_path)
    
    # Also check for common alternate names
    for pattern in ["*rules*.yaml", "*rules*.yml", "rule_*.yaml", "rule_*.yml"]:
        for file_path in root_dir.rglob(pattern):
            if any(part.startswith('.') or part in ['__pycache__', 'tests', 'temp'] 
                   for part in file_path.parts):
                continue
            if file_path not in rule_files:
                rule_files.append(file_path)
    
    return sorted(rule_files)


def main() -> int:
    """Main CI check function."""
    project_root = Path(__file__).parent.parent
    canonical_path = project_root / "config" / "rules.yaml"
    
    print("🔍 Checking for duplicate rule configuration files...")
    
    rule_files = find_rule_files(project_root)
    
    if not rule_files:
        print("❌ ERROR: No rule configuration files found!")
        return 1
    
    if len(rule_files) == 1:
        if rule_files[0] == canonical_path:
            print(f"✅ SUCCESS: Single canonical rule file found: {rule_files[0].relative_to(project_root)}")
            return 0
        else:
            print(f"❌ ERROR: Rule file found in wrong location: {rule_files[0].relative_to(project_root)}")
            print(f"   Expected: {canonical_path.relative_to(project_root)}")
            return 1
    
    # Multiple files found
    print(f"❌ ERROR: Multiple rule configuration files detected ({len(rule_files)} files):")
    for file_path in rule_files:
        print(f"   - {file_path.relative_to(project_root)}")
    
    print(f"\n💡 Solution: Keep only the canonical file: {canonical_path.relative_to(project_root)}")
    print("   Remove or merge other rule configuration files to prevent conflicts.")
    
    return 1


if __name__ == "__main__":
    sys.exit(main())
