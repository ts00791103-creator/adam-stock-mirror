"""Read-only public-data diagnostic: never send messages or print exception payloads."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import json
import traceback
import pandas as pd
from entry_alerts import evaluate_entry_alerts
from screener_ui import screening_data

for symbol in ("2330.TW", "2308.TW", "2317.TW", "2454.TW"):
    stage = "download"
    try:
        data = screening_data(symbol).copy()
        stage = "normalize"
        now = pd.Timestamp.now(tz="Asia/Taipei")
        index = pd.to_datetime(data.index)
        if index.tz is not None:
            index = index.tz_convert("Asia/Taipei").tz_localize(None)
        data.index = index
        if now.hour < 14:
            data = data.loc[data.index.normalize() < now.tz_localize(None).normalize()]
        print(json.dumps({"symbol": symbol, "rows": len(data), "columns": str(data.columns.names)}))
        stage = "evaluate"
        day = str(data.index[-1].date())
        events = evaluate_entry_alerts(data, symbol, day)
        print(json.dumps({"symbol": symbol, "date": day, "alerts": len(events)}))
    except Exception as exc:
        frames = [{"file": Path(f.filename).name, "line": f.lineno, "function": f.name}
                  for f in traceback.extract_tb(exc.__traceback__)]
        print(json.dumps({"symbol": symbol, "stage": stage, "error_type": type(exc).__name__, "frames": frames}))

