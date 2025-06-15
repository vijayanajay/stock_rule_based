### Simplified Project Structure and Workflow (2025-06-15)
**Issue**: The project was over-engineered with a distributable package structure that required `pip install -e .` after changes, creating unnecessary friction for a personal tool.
**Root Cause**: The project was initially set up as a distributable Python package with entry points in `pyproject.toml`, which is appropriate for libraries uploaded to PyPI but adds complexity for personal tools.
**Fix**: 
1. Created a direct `run.py` script in the project root that imports and runs the application directly.
2. Removed the entry point definition from `pyproject.toml`.
3. Added a simple batch file `quickedge.bat` for easier Windows execution.
4. Updated documentation to reflect the simplified workflow.
**Prevention**: For personal tools and simple projects, prefer direct script execution over distributable package structures. Use importable module structure internally but expose a simple entry point at the root level.

---
