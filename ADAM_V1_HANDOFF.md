# 亞當鏡像股票分析系統 V1.0｜開發交接紀錄

最後紀錄日期：2026-11-05（台灣時間）
專案：https://github.com/ts00791103-creator/adam-stock-mirror
測試網站：https://adam-b3-box-test.streamlit.app/
開發分支：release/v1.0-development
來源分支：b3-speed-test
主分支：main

## 使用者需求
將既有亞當 B3 測試版升級為可長期使用的繁體中文正式版 V1.0，保留 B3 和 main，不直接合併或覆蓋。
亞當核心方法：把前一段完整走勢左右翻轉形成未來鏡像推演路徑；短／中／長波、箱型、支撐壓力、K線圖、手機與電腦操作、圖表上下左右移動與縮放。推演不可宣稱保證未來走勢。

## 已確認、已完成
- GitHub 儲存庫：ts00791103-creator/adam-stock-mirror（公開）。
- main 與 b3-speed-test 分支分歧：B3 ahead 183 commits / behind 41 commits（2026-11-05 比對）。
- 已建立獨立分支 release/v1.0-development，來源 b3-speed-test，原兩分支未修改。
- 已讀取部分 B3 程式：app.py、box_theory.py、valuation_engine.py、requirements.txt、README.md、部分 tests 與 workflows。
- app.py 顯示「亞當理論 B3 Pro｜A 模式左右鏡像」，包含短中長波與多市場／多K線週期設定。
- requirements.txt: streamlit, yfinance, pandas, numpy, plotly。
- 已有 tests/test_mops_history.py、tests/test_filing_dates.py 等測試檔，但尚未完整執行。
- GitHub Actions 中 b3-tests.yml push 僅指定 b3-speed-test；python-check.yml push 指定 main 與 b3-speed-test，尚未納入 V1.0 分支。

## 待驗證／風險
- 尚未執行完整自動測試；不能宣稱正式版完成。
- 需檢查 V1.0 全部程式碼、分支差異、測試覆蓋率、Streamlit 部署設定。
- valuation_engine.py 的本益比歷史估值以季末後75天當作可用日（代理值，非實際公告日），需明確標示並優先驗證官方公告日期。
- 主程式與其他模組的整合、行情資料失敗處理、鏡像演算法正確性、箱型不使用未來資料、手機圖表互動仍待測試。
- B3 網站的即時可用性與正式部署尚未驗證。

## 下一步（優先順序）
1. 完整讀取 release/v1.0-development 的主程式、鏡像及圖表模組與所有測試。
2. 在 V1.0 分支新增獨立 CI：Python 語法、unittest、依賴檢查；不改動其他分支。
3. 執行／查看 CI 結果並修正失敗項目，逐項記錄證據。
4. 核實亞當鏡像短中長波、箱型支撐壓力、股價／財報資料時點與失敗保護。
5. 手機／桌機介面測試、部署候選網站；確認通過後才部署正式站。
6. 每個里程碑更新本檔案：完成事項、commit SHA、測試結果、下一步。

## 新對話交接指令（直接貼給 ChatGPT）
請繼續開發我的 GitHub 專案 ts00791103-creator/adam-stock-mirror。先讀取 release/v1.0-development 分支的 ADAM_V1_HANDOFF.md，依裡面的進度接續，保留 main 與 b3-speed-test 不動。先檢查程式與測試，任何程式修改都只在 V1.0 開發分支進行，逐階段更新交接紀錄，不能把未測試的功能說成已完成。我的目標是繁體中文亞當鏡像股票分析正式版 V1.0。
