"""Production entrypoint: run the verified core UI without experimental panels."""
from pathlib import Path
import runpy

runpy.run_path(
    str(Path(__file__).with_name("app.py")),
    init_globals={"PRODUCTION_MODE": True},
    run_name="__main__",
)
