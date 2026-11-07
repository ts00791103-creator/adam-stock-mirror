# 全台股選股階段1：實作待驗證（2026-11-05）
只在release/v1.0-development開發，正式版2369c3c不動。使用者要求每階段保存方便新對話接續。
設計已實作：官方上市上櫃公司名單＋每日行情初選，再每批10檔歷史日K複選。分開當日量與20日均量、分開未處理／無法判定／不符合、日期不一致不判定、部分來源失敗明確標示。
工作來源：market_universe.py、full_market_ui.py、app.py候選入口；tests/test_full_market.py；scripts/live_market_smoke.py；CI新增官方來源probe。
尚待本次CI與真實官方欄位驗證，再候選站操作驗收；不得宣稱已全市場通過或正式發布。原自選名單與即時價格保留。
