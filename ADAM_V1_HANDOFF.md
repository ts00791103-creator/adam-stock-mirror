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

## 2026-11-05｜V1.0 CI 建立紀錄
- 已在 release/v1.0-development 新增 .github/workflows/v1-validation.yml。
- Commit: 8923ba0234f6406518dd1fa6fb8d869eb4efa8a5。
- push / PR（目標為 V1.0 分支）與手動觸發，Python 3.11，安裝 requirements.txt 及解析依賴，compileall，unittest discover。
- 已檢查原 B3 workflow：b3-tests.yml 和 b3-mops-tests.yml 主要限定 b3-speed-test；python-check.yml 限定 main/b3-speed-test。故另建 V1.0 專用 CI，不修改原有 workflow。
- 注意：CI 檔案已提交，但此處尚未取得 GitHub Actions 執行結果，**不能宣稱測試通過**。
- 下一步：查看 GitHub Actions 中 Adam V1.0 validation 的實際執行狀態和錯誤日誌；修正失敗測試，再進行演算法與資料來源檢查。

## 2026-11-05｜CI 第 2 次失敗與修正
- 使用者提供 GitHub Actions「Adam V1.0 validation #2」截圖：安裝依賴與語法檢查通過，30 tests 執行，errors=1。
- 失敗案例：tests/test_filing_dates.py 的 test_valid_official_url_is_not_verified。
- traceback：filing_dates.py 中 moment.date() <= quarter_end 發生 TypeError。
- 原因：測試以 patch('filing_dates.date') 模擬當日日期，連帶攔截 date(year, month, day) 建立季末日期，使 quarter_end 變成 mock 物件。
- 修正：filing_dates.py 改用 datetime(year, month, day).date() 建立季度結束日；保留 date.today() 可測試性及官方公告日保守驗證規則。
- 修正 commit：151e4ad78a24e547a558a89164caff2c33d0ec57。
- 尚未確認修正後 GitHub Actions 是否通過；下一步查看新 CI 結果。

## 2026-11-05｜CI 通過、開始核心演算法驗證
- 使用者提供 GitHub Actions 截圖：Adam V1.0 validation #3（39秒）與 #4（30秒）均為綠色通過。此前 #1、#2 失敗。
- 已閱讀 app.py 第 374–550 行的 find_pivots、future_index、mirror_wave。現行 A 模式為反轉已確認波段的收盤價序列，並平移至最新收盤價作為鏡像起點。
- 已確認 find_pivots 需要左右 span 根 K 棒才能確認轉折，因此最近幾根 K 棒的轉折有確認延遲；這是後續介面必須清楚提示的特性。
- 注意 future_index 對日K使用工作日、週K固定7天、月K月初、分K固定時間間隔，尚未考慮台股休市日與盤中休息，投影日期應標示「示意」而非真實交易時段。
- 新增 tests/test_box_theory.py：資料不足、上破、下破、箱體過寬等離線回歸測試。Commit: ebae4df57e940ef1ef5e201aca0d9ff5236cac8f。
- 新測試提交後的 GitHub Actions 尚未確認，不能宣稱新測試已通過。
- 下一步：確認新 CI 結果；為 mirror_wave 加入不依賴 Streamlit 的單元測試，檢查左右鏡像方向、價格起點、短中長波、轉折確認延遲與時間軸。

## 2026-11-05｜箱型測試綠燈、鏡像測試新增
- 使用者回報新增箱型測試後的最新 CI 顯示綠色；依使用者確認記錄，尚未直接取得該次 Actions job 日誌。
- 新增 tests/test_mirror_wave.py，commit e585974e3b2954cc0128199cff976b128f73a6a4。
- 使用 AST 只載入 app.py 中的純計算函式，不啟動 Streamlit UI；測試 A 模式左右翻轉（不倒置價格）、最新收盤價對齊、轉折不足保護、短中長波 span/lookback/門檻、轉折確認延遲與日K週末排除。
- 新增測試後的 CI 結果仍待確認；不可宣稱已通過。
- 下一步：查看 GitHub Actions 最新 Adam V1.0 validation；失敗則依日誌修正；通過後補充交易日曆與圖表整合測試。

## 2026-11-05｜鏡像 CI 綠燈，開始手機圖表資料測試
- 使用者回報新增 tests/test_mirror_wave.py 後的 GitHub Actions 最新狀態為綠色（未直接取得 job logs）。
- 檢查 mobile_chart.py：採用 TradingView Lightweight Charts 4.2.3，將 K 線、鏡像、箱型序列轉換成時間戳；包含可視區間 sessionStorage 邏輯。
- 新增 tests/test_mobile_chart_data.py，驗證時間戳與數值、NaN/Infinity/None 排除、空序列，commit 225b578bf81fc0c55664af6905026cd0a9b491aa。
- 靜態檢查發現手機圖表 handleScroll 設定 vertTouchDrag:false，且提示文字為「單指左右拖曳」；使用者要求的上下左右移動尚未獲得實機驗證。不可宣稱已完成。
- 時間軸：future_index 的日 K 只排除週末，未排除交易所休市日；週 K、月 K、分 K 尚需實際市場行事曆驗證。
- 新增測試的 CI 結果待確認；下一步視結果修正，並規劃交易時段與圖表操作驗收。

## 2026-11-05｜手機圖表測試錯誤修正
- 使用者提供 GitHub Actions 錯誤截圖：Run offline regression tests，Ran 42 tests，FAILED(errors=3)。
- 三項錯誤：test_empty_series、test_invalid_values_are_excluded、test_timestamps_and_values，均因 TypeError: _points() takes 2 positional arguments ...。
- 原因：tests/test_mobile_chart_data.py 的 setUpClass 將純函式直接存成類別屬性 cls.points，使用 self.points 呼叫時被 Python descriptor 自動綁定 self，造成額外參數。
- 修正：改成 cls.points = staticmethod(load_points())，避免綁定；未修改 mobile_chart.py 正式功能。
- 修正 commit：868521143f0b6637b733dd8f5946ec65ed540ca6。
- 修正後 GitHub Actions 尚待驗證，不可宣稱已通過。

## 2026-11-05｜手機圖表資料測試修正後綠燈
- 使用者提供 GitHub Actions 畫面：Adam V1.0 validation #11（31秒）與 #12（30秒）均為綠色成功；#9 與 #10 為紅色失敗。
- 確認 tests/test_mobile_chart_data.py 的 staticmethod 修正後，現有 CI 已通過；這僅證明目前 CI 所覆蓋的測試通過，不代表實際手機拖曳／縮放與交易日曆已驗收。
- 下一步：完善交易時段／交易日曆的預測日期標示，測試手機 K 線圖左右拖曳、上下平移、縮放與視窗記憶；保留 main 和 b3-speed-test 不動。

## 2026-11-05｜第四階段手機圖表觸控操作
- mobile_chart.py：將 #chart touch-action:pan-y 改為 touch-action:none，Lightweight Charts handleScroll 的 vertTouchDrag 改為 true，並更新繁體中文操作提示。
- 修改 commit：0bfce0b7963e26663b1395440b463cb6319f0d78。
- 新增 tests/test_mobile_chart_gestures.py，靜態檢查雙軸拖曳設定、觸控事件及 sessionStorage 視窗記憶；commit 939ac9729cec8bc8a0a3c7a7e43f0f2cab715874。
- 此為 V1.0 分支設定修改，沒有部署到 B3；靜態測試不等於實機操作驗收，且 touch-action:none 可能影響頁面手勢滾動，須在候選站手機實測。
- 新增測試的 CI 結果待確認；下一步依 GitHub Actions 狀態處理，之後安排獨立候選版部署及實機手勢驗收。

## 2026-11-05｜候選站部署準備
- 使用者回報最新 GitHub CI 為綠色。
- 已確認 requirements.txt 為 Streamlit/yfinance/pandas/numpy/plotly，app.py 為主程式；README.md 只有簡短專案描述；沒有 .streamlit/config.toml（非部署必要）。
- 新增 V1_DEPLOY_GUIDE.md，記錄 Streamlit Community Cloud 第二個獨立 App 的 repository/branch/app.py 設定、候選站建議名稱與手機驗收清單。Commit b77476421e9fc9a43533acf205fcfb36c02e0775。
- **尚未實際部署候選網站**，候選 URL 未確認。部署需要在使用者 Streamlit 帳號建立獨立 App；不能宣稱已上線。
- 下一步：使用者建立第二個 Streamlit App 後提供實際 URL，再驗收並修正；絕不覆蓋 B3。

## 2026-11-05｜候選站已部署（使用者截圖確認）
- 使用者在 Streamlit 部署畫面設定 repository=ts00791103-creator/adam-stock-mirror、branch=release/v1.0-development、main file=app.py、App URL=adam-v1-candidate，並完成 Deploy。
- 使用者提供候選站載入截圖：繁體中文 UI 可見，台灣股票/ETF、2308 台達電（上市）、日K、10y、三波同圖控制項均顯示；無可見啟動錯誤。
- 候選站預期網址：https://adam-v1-candidate.streamlit.app/ （以使用者部署畫面與截圖為依據）。
- 目前只驗證啟動畫面；尚未確認 K 線是否成功繪製、鏡像結果、手機四向拖曳、雙指縮放、視窗記憶、資料正確性。
- 截圖標題仍是「亞當理論 B3 Pro｜A 模式左右鏡像」，候選版命名需後續調整，但不要改動 B3/main。

## 2026-11-05｜候選站圖表首次驗收截圖
- 使用者提供 2308 台達電候選站圖表截圖，畫面顯示「最新資料 2026-11-05／收盤價 1,130.00」、K線、成交量、布林通道、藍色箱型、短中長波鏡像標籤，確認圖表已成功渲染。
- 尚未確認資料源行情真實性、價格軸/時間軸與鏡像線精確性；截圖價格軸有約 2,000 元歷史區域，需核對資料。
- 尚未完成四向拖曳、雙指縮放、移動不跳位等手機實機驗收。下一步請使用者在圖表上實測拖曳並回報結果。

## 2026-11-05｜手機實機手勢驗收回報
- 使用者在 V1.0 候選站確認：左右拖曳正常、雙指縮放正常；上下拖曳不行、繞圈移動不行。
- 原 mobile_chart.py 雖已設 vertTouchDrag:true / touch-action:none，但這些設定並不保證價格軸可平移；目前只有水平時間軸操作成功。不得標記四向拖曳已完成。
- 後續需設計/驗證真正的垂直價格軸平移（包括與雙指縮放、成交量副軸、布林線、箱型覆蓋層及 viewport 記憶相容），在 V1.0 候選站實機確認後才可驗收。不要修改 B3/main。

## 2026-11-05｜手機垂直平移首次修正（待驗收）
- mobile_chart.py 新增單指觸控 Y 位移對應右側價格軸 scaleMargins（上/下 margin 總和固定），以有限範圍上下平移；斜向觸控仍由原生圖表處理 X 軸，Y 軸由自訂事件處理；雙指交由原生 pinch。Commit 2042448dcb7cdd8868daa6f67ff17481f222fa39。
- 以 sessionStorage 的 v1-price-shift-<viewportKey> 記憶價格軸位置；保留原有水平 logical range 記憶及箱型重畫。
- tests/test_mobile_chart_gestures.py 增加垂直平移設定及雙指縮放保留的靜態測試；commit eae0ddcd2b44e32c2cd5c013d6f1936ae436345f。
- **重要限制**：這是以價格軸 scaleMargins 做有界平移，不是無限自由拖曳；尚未實機驗收，也未確認最新 GitHub Actions 結果。若操作仍不符合期待，需要重新設計價格軸座標映射。
- 下一步請使用者等待候選站自動部署更新，確認 GitHub Actions 綠燈，再用 2308 日K 測試上下、斜向/繞圈、左右、雙指縮放、位置保持。

## 2026-11-05｜垂直平移第二次實機測試失敗
- 使用者在候選站再次測試後回報：左右可移動，上下仍然不行。上一版透過 scaleMargins 做垂直平移的方法未達驗收標準，不應宣稱修好。
- 下一階段需要採用可真正控制價格座標/價格軸可視範圍的圖表架構，並實機驗證上下、斜向、繞圈、縮放與記憶；不可再僅修改 vertTouchDrag 或 margins 後宣稱完成。
- 目前 B3/main 保持不變，候選版尚未驗收完成。

## 2026-11-05｜第三次手機垂直平移修正（待 CI／實機驗收）
- 原本 scaleMargins 平移實機無效，改採 Lightweight Charts v4 同一右側價格軸上的兩條透明 line series，透過 setData 更新上下 autoscale 錨點，讓價格與座標對應可移動。此法會影響 autoscale 顯示範圍，需檢查指標/鏡像/箱型不被過度壓縮。
- 手指單指垂直位移更新 priceShift；左右拖曳與原生雙指縮放保留；使用新 sessionStorage key v1-price-pan-v2- 避免舊版狀態干擾。mobile_chart.py commit b2e88c0a907edadae9f1a69106a7939f6c382980。
- 更新 tests/test_mobile_chart_gestures.py 靜態檢查兩條錨點與新平移邏輯；commit a4da426eeed7e3a4fae4b1a643122afda65f3e94。
- **未確認 CI／實機成功**；待候選站自動部署後測試 2308 日K 上下、斜向、繞圈、左右、雙指縮放、位置記憶。如仍無效，應改用可明確控制價格座標的自訂繪圖實作。

## 2026-11-05｜第三次上下拖曳實機仍失敗，加入診斷按鈕
- 使用者回報第三版 invisible autoscale anchors 仍無法上下拖曳。
- 為區分 iOS 觸控事件與圖表價格軸移動問題，於 mobile_chart.py 新增 ↑ K線上移、↓ K線下移、垂直歸位三個明確按鈕，直接調整同一 priceShift；commit 1408f2a2318f017ba67e0d90d2ee9a78469f29a1。
- 按鈕只是診斷/暫時控制，不代表單指上下拖曳已修好。CI 和手機效果均待驗證。
- 若按鈕有效但手勢無效，問題偏向 iOS iframe/Lightweight Charts 觸控事件；若按鈕也無效，需替換價格軸平移機制，可能改用自訂 Canvas 圖表。

## 2026-11-05｜第四次垂直移動修正：視覺層平移（待驗收）
- 使用者回報第三次方案與上下按鈕仍無法上下移動。
- mobile_chart.py 改為對 chartElement 及 box-overlay 同步套用 translateY(px)，單指上下拖曳與 ↑/↓/歸位按鈕共用 bounded panY（±120px），sessionStorage key v1-visual-pan-y-；commit 6212afa5061c2f545d528f3e58cfb83df9d12949。
- tests/test_mobile_chart_gestures.py 同步修改靜態測試；commit 0bed0fd4beb7ad7bb49f106c6cbf9da2557611ea。
- 重要：此為畫面平移的診斷/過渡方案，會移動座標軸並在邊緣產生空白，不是正確的價格軸可視範圍重算。不可宣稱最終完成。CI 和手機驗收待確認。
- 若這版按鈕也完全不動，應先確認候選站部署更新及 iframe 是否有 JS 錯誤，再進一步修改。

## 2026-11-05｜垂直控制按鈕無反應：可見性診斷
- 使用者確認新增三個上下移動按鈕沒有反應。
- 已檢查 mobile_chart.py，按鈕原先放在 480px 圖表之後，手機可能因 iframe 高度、頁面捲動而難以辨識；目前無瀏覽器主控台證據，不能斷定 JS 是否執行。
- 將三個控制按鈕移到 K 線圖**上方**，並加入「垂直位移：N px」即時狀態文字，讓使用者可分辨 click 事件未觸發或圖表 transform 沒效果；提高 iframe 高度至 675。commit bc3a13423f086842bcfc8d29c848534bf1c77523。
- 此次僅改診斷介面，並未完成真正價格座標的自由拖曳。需待 CI 與使用者實測，且不改 B3/main。

## 2026-11-05｜依使用者要求移除上下按鈕，改為直接手勢
- 使用者明確要求「不要按鈕也能上下移動」。已移除 ↑/↓/歸位三個診斷按鈕及狀態文字。
- mobile_chart.py 改在 chart-wrap 捕捉 touchstart/move/end（capture:true），垂直觸控位移套用 chartElement 與 box-overlay 同步 translate3d；原生左右時間軸拖曳及 pinch 保留。commit 3f0737f2d0a19bba7fd7177e1bcea1f76254ffaf。
- 更新 tests/test_mobile_chart_gestures.py 對應新實作及無按鈕檢查。commit 071a1e2b85d48f3b457f87560138bd7996519784。
- **尚未確認 CI 和手機實測**；視覺平移是有限範圍且會移動價格軸標籤，仍非正式價格軸重算。若手機仍無法上下移動，需改用不同圖表引擎或自訂畫布。不得宣稱完成。

## 2026-11-05｜依使用者要求暫停上下平移，進入鏡像正確性／介面整理階段
- 使用者明確要求暫時不做上下移動，直接下一階段。不要再要求使用者測試上下／繞圈；該功能保留為未完成事項。
- app.py 首頁名稱改為「亞當鏡像分析 V1.0｜候選測試版」，並於最上方新增提示：鏡像是歷史路徑反向排列情境，非即時行情／價格預測；未來日期僅示意，尚未完整排除休市與盤中休市。
- 修改 commits c3d73757f9c47c84548a4c9d4290a5709b828f0f、e372d1d08bc389a67f4ad5290a811991c7be422d（後者修正前者文字換行造成的 Python 語法問題）。
- 尚未確認 GitHub Actions 最新 CI；正式鏡像演算法、交易日曆與財務估價仍待後續核驗。B3/main 保持不變。

## 2026-11-05｜第五階段：鏡像顯示空間與三波資訊
- 使用者提供 2308 日K 截圖，右側鏡像延伸靠近邊界，三波不易分辨。已在 mobile_chart.py 加入每波鏡像未來根數 mirrorSummary，在圖表上方分別顯示短中長波根數；根據最長鏡像預留右側時間軸空間（最少 12、最多 80 根）。commit 342452d1962860d835a331cb7a5be41499040880。
- 更新 tests/test_mobile_chart_gestures.py 的靜態驗證，commit ae5dbbd5ea5d77b3c1f4233dfa07dee28876c32e。
- **待驗證**：CI 最新狀態、候選站實際畫面、預留右側空間是否過大。已儲存的舊 viewport 會優先恢復，可能需要手動調整圖表顯示範圍才能看見新預設。此階段尚未證明三波演算法完全正確，也未完成正式版。
- 上下移動／繞圈依使用者要求暫緩，勿再要求測試；main、b3-speed-test 不變。

## 2026-11-05｜第五階段：三波鏡像獨立顯示
- 根據 2308 日K 截圖，三波線重疊不易辨識。mobile_chart.py 現為短波虛線(style=2)、中波點線(style=1)、長波實線(style=0)；三波鏡像各自標註 mirrorWave，圖表上方各波根數標籤可點擊切換該波鏡像的顯示/隱藏（含鍵盤 Enter/空白）。commit c0d2fe604cb7cf61114305b7df3a3e8bdc26acf8。
- tests/test_mobile_chart_gestures.py 加入三波獨立顯示與線型的靜態測試。commit 5bcfb6dadf00bc224c3aa839e9aa5072746ae551。
- 未改動鏡像價格公式；若三波算出相同價位，線條仍會在數學上重疊，可單獨切換檢查。最新 CI 與手機互動效果尚待確認。上下/繞圈暫緩，B3/main 不動。

## 2026-11-05｜手機實測：長波鏡像獨立切換通過
- 使用者確認點選「長波鏡像」後，紅色鏡像虛線消失。這驗證了長波顯示／隱藏的手機點擊行為；不代表短、中波切換或三波演算法已驗證。
- 右側預留空間在使用者截圖中已足夠，暫停擴張。上下移動／繞圈依要求暫緩。
- 下一階段：以已知測試數列核對 find_pivots、mirror_wave 的短中長波轉折點、左右反轉、最新收盤價銜接及未來時間軸；先寫自動化驗證，再考慮更動正式演算法。

## 2026-11-05｜第六階段：鏡像公式離線測試擴充
- tests/test_mirror_wave.py 新增五項測試：上漲歷史波段反轉成下跌鏡像、最新收盤價錨定、最後兩個已確認轉折點選取、平坦歷史波段保持平坦、短中長波參數與歷史長度獨立。commit a79365440bcc8943fcbc538301b87064de17142f。
- 原 mirror_wave 算法未修改；測試使用 Mock pivots，能驗證映射與接續，但不能取代真實資料轉折點品質檢驗。GitHub Actions 結果尚未確認。
- 使用者已驗收長波點選隱藏成功。上下/繞圈暫緩。main、b3-speed-test 不動。

## 2026-11-05｜第七階段：實際轉折點選取測試
- 使用者回報第六階段 GitHub Actions 綠色。
- tests/test_mirror_wave.py 新增 3 項不以 Mock 取代轉折點的測試：實際高低點交替與最小幅度、過小回檔過濾、使用 find_pivots 真實輸出餵入 mirror_wave 並核對鏡像價格/時間軸。commit 98fbc8728fd6cf6938682dc8b076a2c3c1cd889c。
- 這些是人工合成的已知價序列，非外部市場行情；下一步應驗證真實股票數據與長波歷史窗口。此批 CI 尚待確認。沒有改動生產演算法、main 或 b3-speed-test。

## 2026-11-05｜第八階段第一批：長波資料長度邊界測試
- 使用者回報第七階段 CI 綠色。
- tests/test_mirror_wave.py 新增三項：800 根資料的長波應使用最後 650 根、20 根短資料不能捏造長波轉折、長波確認轉折區間的鏡像長度與時間軸長度一致。commit 30f7d8183042916394dd034966ff0d20c39d29c7。
- 尚未實際以外部真實股價歷史資料進行重播；短於 650 根的資料目前會使用可取得的資料，不代表已強制滿 650 根才准顯示。須另行評估是否增加『歷史不足』提示。最新 CI 待驗證。main、b3-speed-test 未更動。

## 2026-11-05｜第八階段第二批：資料不足提示
- 使用者確認前一批長波邊界測試 CI 綠色。
- app.py 在每個短/中/長波鏡像計算前，依 WAVES[name] 的 lookback (100/260/650 根) 與實際 len(df) 比較；不足時顯示警告，列出可用根數/參考根數，明示若有結果也僅是有限資料暫定鏡像。commit 213f14ddf968611be2873290d075d0ada8b2f1a9。
- 新增 tests/test_wave_history_warning.py，靜態檢查警告在計算前、根數與訊息、三波設定不變。commit c43cabad2d5c06bfe84538b61e6c53d06dbe5bd9。
- 目前沒有強制禁止不足 650 根的長波計算，僅明示警告；沒有更動原鏡像公式。最新 CI 尚待確認，真實市場歷史回放仍未執行。main/b3-speed-test 不變，上下移動繼續暫緩。

## 2026-11-05｜第九階段：行情 OHLC 品質檢查
- 使用者回報第八階段第二批 CI 綠色。
- app.py 新增 audit_ohlc_data(df)；分析前檢查時間排序、重複時間、OHLC 缺欄、NaN/Inf、非正數價格、High/Low 與 Open/Close 的關係；若異常，顯示錯誤並停止分析，不自行猜測補價。commit 0f4b95b7232d84e30e1197f98671b629634704ec。
- tests/test_market_data_quality.py 新增 7 項離線測試，包括品質閘門位置。commit 86a8dd8bd66f7faaedb436932ea2f13fd6db933c。最新 CI 尚待確認。
- yfinance get_data 既有的排序、去重、dropna Close 行為保持不變；品質閘門在其後，因此不能檢出已被 get_data 丟棄的原始缺漏。真實行情回放尚未完成。main、b3-speed-test 不變。

## 2026-11-05｜第九階段第二批：Yahoo 原始行情整理前揭露
- 使用者回報第九階段第一批 CI 綠色。
- app.py 新增 raw_quote_summary(df)，在 dropna/sort/dedup 前計數收盤價 NaN/Inf、重複時間、未排序；透過 df.attrs['raw_quote_notes'] 傳回，在分析時 st.warning 呈現。commit 699f4a6e2366512a209319853c639f77daa6e6f3。
- tests/test_raw_quote_summary.py 新增 5 項離線測試（正常、NaN/Inf、重複、未排序、揭露先於清洗）。commit 53a38b7e373af09819f36c9dd5031e39dc43991a。
- 僅 Yahoo get_data 管線保留這些整理前提示；期交所 CSV/API 管線仍由整理後的 audit_ohlc_data 檢查。Yahoo 原始異常提示不代表行情已完整修復；沒有改動鏡像公式。CI 尚待確認，真實股票行情回放未完成。main/b3-speed-test 未更動。

## 2026-11-05｜第十階段第一批：Yahoo 下載管線整合測試
- 使用者回報第九階段第二批 CI 綠色。
- 新增 tests/test_yahoo_download_pipeline.py：以 mock yf.download 執行 app.py 原始 get_data、raw_quote_summary、audit_ohlc_data（AST 去除 Streamlit cache decorator），覆蓋資料亂序/重複/NaN 的清洗與警示、Yahoo MultiIndex 欄位、10 分K 跨日不混合、Inf 品質閘門、空資料。commit 503d047c800ce39cd7ac3587869e5ec31813b65b。
- 本次僅新增測試，未更動正式運算或下載邏輯。這是模擬 Yahoo 回應的管線整合測試，不是網路實際下載或真實股票歷史回放；最新 CI 待確認。main、b3-speed-test 未更動。

## 2026-11-05｜第十階段第二批：真實台股 Yahoo 行情抽查工具
- 使用者回報第十階段第一批 CI 綠色。
- 新增 scripts/live_tw_quotes_smoke.py，下載 2330.TW 與 2308.TW 近兩年日K，逐一驗證 OHLC、日期順序、重複、有限值、價格合理關係、至少100根，輸出日期與收盤。commit 9aba0525e3166383c25c7b974bf6c0d193896748。
- 新增獨立手動觸發 workflow .github/workflows/v1-live-quotes.yml，與既有 v1-validation.yml 離線測試分離，避免網路故障讓離線測試變紅。commit 46e506d3b0d072e41bb6f5fac82521ea0119fc3a。
- 尚未執行 live workflow，不能宣稱真實行情已驗收；注意 GitHub workflow_dispatch 若工作流程尚未存在於 default branch，Actions UI 可能無法提供手動執行按鈕。切勿為此直接修改 main，應先評估替代方式。main/b3-speed-test 未動。

## 2026-11-05｜真實行情工作流程停用的替代驗證
- 使用者手機截圖顯示 v1-live-quotes.yml「已手動禁用此工作流程」，且尚無運行，不能宣稱真實行情測試通過。
- 為避免使用者在手機操作停用工作流程，已將 scripts/live_tw_quotes_smoke.py 加入既有 .github/workflows/v1-validation.yml 的最後一步，continue-on-error: true，timeout-minutes: 3。commit 6f26e2e87ec38085b742a0eca39fd1842c0d682c。
- 注意：此步驟失敗不會使整體 workflow 紅色；必須檢查 Actions 中 Optional live Taiwan quote smoke check 的 PASS/FAIL 訊息，才能判斷真實資料是否驗證成功。main、b3-speed-test 未更動。

## 2026-11-05｜第十階段真實行情驗證通過（使用者提供 GitHub Actions 日誌截圖）
- GitHub Actions Optional live Taiwan quote smoke check 於 UTC 2026-11-05T11:06:55 執行，兩檔 PASS。
- 2330.TW：486 根日K，最後日期 2026-11-05，收盤 2240.00。
- 2308.TW：486 根日K，最後日期 2026-11-05，收盤 1130.00。
- 此結果確認真實 Yahoo 下載與資料品質檢查通過，但尚未驗證鏡像投影結果；兩年資料 486 根，不足長波參考設定 650 根，長波應顯示資料不足警示。下一步應使用較長 period（例如 5y）做短中長波實際鏡像測試。

## 2026-11-05｜第十一階段：真實台股亞當鏡像驗證（待執行）
- 已由使用者提供 GitHub 日誌確認第十階段真實行情 PASS（2330.TW、2308.TW，486 根，2026-11-05）。
- 新增 scripts/live_tw_mirror_smoke.py，下載兩檔 5y 日K，需至少650根，透過 AST 執行 app.py 原始 find_pivots/future_index/internal_turns/mirror_wave，逐一測試短中長波的時間左右翻轉公式、錨定最新收盤、日期遞增、長度及有限數值。轉折不足時輸出 NO_PIVOTS，不視為鏡像成功。commit f954d490fb2b84eae99a9c70f697bdf49a2d5e6f。
- 已將 Optional live Taiwan Adam mirror projection check (non-blocking) 加入既有 .github/workflows/v1-validation.yml，commit 94bb3252592cdf7b7fb02f0691bfa7f1f0736d70。
- 本批尚未取得 GitHub CI 日誌。因 continue-on-error，主 workflow 綠色不等於鏡像真實測試 PASS，需檢視此步驟輸出。main/b3-speed-test 未動。

## 2026-11-05｜第十一階段真實行情鏡像測試通過（使用者 GitHub Actions 截圖）
- 2330.TW 1212 根日K，最後日期 2026-11-05，收盤 2240；短波 PASS（12根，鏡像 2240→2440）、中波 PASS（14根，2240→2035）、長波 PASS（49根，2240→1855）。
- 2308.TW 1212 根日K，最後日期 2026-11-05，收盤 1130；短波 PASS（6根，1130→915）、中波 PASS（15根，1130→700）、長波 PASS（15根，1130→700）。
- 六項 PASS 證實實際行情下鏡像公式、起點錨定、日期與數值一致性；不代表鏡像預測準確或 UI 完全驗收。
- 後續優先：檢查台達電中長波是否選到相同轉折區間，並清楚呈現歷史轉折區間起迄日期與實際歷史價格，避免使用者誤解。main/b3-speed-test 不變。

## 2026-11-05｜第十二階段第一批：鏡像歷史來源對照表
- app.py 新增 wave_source_rows(waves, interval)，在圖表前顯示短中長波歷史起迄日期、歷史起迄價、鏡像終點及共用來源波段；當起迄時間完全相同，明示鏡像並非獨立來源。commit c6266514f9f1fb2c11402ac4337b1990f085007e。
- 新增 tests/test_wave_source_rows.py 四項離線測試：日期價格、重複來源、不同來源、圖表前呈現。commit 170beb6dc73530e9c85b5e19ea64b40a0a96330f。
- 原 mirror_wave 計算與圖表互動未更動。最新 CI 尚待確認。main/b3-speed-test 未動。

## 2026-11-05 Phase 12 mobile source cards
User confirmed CI green. app.py commit 4ae29818f9fc5f299add74ad40378f85b2269102 renders vertical wave source cards and expandable full table. Test commit f072e3b535256daf74c940d955fb17b61939a94e adds mobile presentation assertion. No changes to mirror math or chart controls. Next: release readiness checks. main and b3-speed-test remain unchanged.

## Phase 13 release readiness guard (2026-11-05)
Added tests/test_release_readiness.py (commit 472596e5e7a613a6e982b11ef0339233cb7682cc), checking critical functions, data-quality gate ordering, mobile source cards and caveat before chart, nonblocking live checks, and handoff existence. Await latest CI. This is a regression guard, not final acceptance or deployment. No main/b3-speed-test modifications.

## 2026-11-05 Phase 13 second batch: release audit
User confirmed first batch CI green. README is minimal, requirements.txt contains streamlit/yfinance/pandas/numpy/plotly; no .streamlit/config.toml, Procfile or runtime.txt found (these are not necessarily required for Streamlit Cloud). Added V1_RELEASE_CHECKLIST.md commit 5b1c374582358108cc31419dc377f9961fe2f812 with verified test milestones, deployment prerequisites, manual mobile/desktop checks and no-main-change rule. No release or merge performed. Await actual deployment URL and manual acceptance before release.
