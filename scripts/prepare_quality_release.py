"""Build only the reviewed production overlay, never the entire dev branch."""
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"production-package"
shutil.copytree(ROOT/"production-base",OUT,ignore=shutil.ignore_patterns(".git"),dirs_exist_ok=True)
for filename in ("app.py","studio_layout.py"):
    shutil.copy2(ROOT/"release-preview/v1.0.8"/filename,OUT/filename)
for filename in ("official_history.py","verified_daily_history.py","analysis_availability.py","production_quality_preview.py"):
    shutil.copy2(ROOT/filename,OUT/filename)
for filename in ("test_production_quality_release.py","test_initial_navigation.py","test_verified_daily_history.py"):
    shutil.copy2(ROOT/"tests"/filename,OUT/"tests"/filename)
shutil.copytree(ROOT/"tests/fixtures",OUT/"tests/fixtures",dirs_exist_ok=True)
assert (OUT/"production_quality_preview.py").read_bytes()==b"PRODUCTION_MODE = True\n"+(OUT/"app.py").read_bytes()
