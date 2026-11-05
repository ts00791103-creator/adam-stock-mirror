# 亞當鏡像 V1.0 正式發布準備方案

日期：2026-11-05（台北）

狀態：發布準備文件；尚未合併、建立正式站或發布 GitHub Release。

## 建議決策

採用「獨立 V1.0 正式站」；保留現有 main 正式站、B3 測試站及 V1 候選站。不要直接把整個開發分支合併至 main。

原因：目前開發分支較共同祖先多275筆提交，main也有41筆獨有提交，兩者已分岔。main獨有差異含 app.py、箱型、手機圖表、即時圖表及期貨測試檔案；目前的V1測試不能證明合併後仍保持相同行為。

## 已核對的版本

| 用途 | 分支／提交 | 網站 |
|---|---|---|
| 既有正式站 | main，9d11d224e7e49ddec40988e3d782828b48fe0edd | https://adam-stock-mirror-mkxgzfcscdedtpfd6zx88v.streamlit.app/ |
| B3測試站 | b3-speed-test，0239e3c374297a1d312a773ccdadb553946a1f1b | https://adam-b3-box-test.streamlit.app/ |
| 已驗收候選站 | release/v1.0-development，07f76dbbf792c32189bf63d78d44edfbd9634a63 | https://adam-v1-candidate.streamlit.app/ |
| 程式實質版本 | 45e84cc496f045404371b00ee1aee672a36047e5，V1-READ-1105 | 後續兩筆提交只更新交接文件 |

發布來源應凍結在已驗收的完整提交07f76db，不追隨日後開發分支的任意新修改。若正式版要改標題、依賴或功能範圍，視為新候選版本，需重新檢查後才能取代這個基準。

## 建議正式站設定（尚未執行）

| 項目 | 建議值 |
|---|---|
| Repository | ts00791103-creator/adam-stock-mirror |
| 新的正式來源分支 | release/v1.0-production，由07f76db建立並凍結 |
| 入口 | app.py |
| 正式網址建議 | https://adam-mirror-v1.streamlit.app/ （尚未查證可用性，尚未建立） |
| 候選網址 | 保留 adam-v1-candidate.streamlit.app |
| Python | 對齊實際候選站的3.14系列；已觀察啟動日誌為3.14.10；新站需核對實際版本 |
| 閱覽對象 | 發布核准時確認；本次不改變現有網站權限 |
| 金鑰 | 核心Yahoo鏡像不需Fugle金鑰；Fugle即時功能如需啟用，僅由擁有者透過平台Secrets設定，不放進GitHub或備份 |

目前只允許修改release/v1.0-development。**建立release/v1.0-production及新正式站必須取得下一次明確核准，現在未建立。** 不假設平台Branch欄位可接受任意commit SHA；依官方文件採用明確分支，將其指向已審核提交。

## 已完成的測試與證據

- 最新已驗收來源07f76db的GitHub Actions： https://github.com/ts00791103-creator/adam-stock-mirror/actions/runs/42034935253 ，所有步驟success。
- 97項Python離線測試；9項價格軸Node行為測試；實際模板執行測試（初始漲跌/量能、窄寬版標籤、空資料與provider保留）。
- 真實Yahoo下載：2330、2308近兩年日K各486根、最後日期2026-11-05；收盤分別2240、1130，均PASS。
- 真實三波鏡像六項PASS：2330短波2240→2440、中波→2035、長波→1855；2308短波1130→915、中/長波→700。
- 候選站瀏覽器：股票及中文查詢、日/週K、三波同圖/獨立/單波、來源卡片與重複警示、負數投影警告、價格平移、縮放、手機/電腦重排均有測試紀錄。
- 使用者手機依五項清單回報「都可以」。未取得裝置型號與瀏覽器版本，因此只代表本次使用者裝置驗收，不外推所有裝置。
- 週K資料以該週起日標記，如2026-11-02，並不代表只更新到星期一。

## 發布範圍與限制

本次驗收承諾範圍為2330/2308查詢、日/週K及短中長波歷史路徑鏡像與基本圖表操作。期貨/其他商品、月K/分K、財務估價/MOPS、Fugle即時報價仍屬額外測試功能，不能寫成已全面驗收。

保留並明示：鏡像不是未來股價預測；未來日期未完整處理交易所假日/盤中休市；歷史不足及同來源警告；零/負數投影是數學情境而非可交易股價。測試功能若要納入正式承諾，須另行測試；若要隱藏或移除，也須建立新候選版本並回歸驗證。

## 發布前需核對的技術條件

1. **版本與環境**：requirements.txt目前未鎖版本；CI為Python3.11、候選站為3.14.10。日誌可見NumPy分別2.4.6/2.5.4。CI成功不能當作兩環境完全相同的證明。新站應沿用候選環境，記錄安裝版本；若鎖版或變更Python，先在候選站驗證。
2. **完整依賴**：財報模組直接使用requests與pd.read_html；CI額外安裝requests、lxml、html5lib、beautifulsoup4，但requirements.txt只列5個核心套件。目前核心功能已實測，附加財報功能仍需補完整依賴/全新環境安裝檢查才能納入正式承諾。
3. **自動工作流程**：tx-daily-update.yml含contents:write且目標是b3-speed-test；本次不執行、不啟用、不修改它。site-health.yml只是檢查舊正式URL的HTTP回應，不能當成V1功能健康檢查。不要在新正式站方案中誤認已具備V1監控。
4. **版本名稱**：目前首頁仍有「候選測試版」及測試功能名稱。正式命名調整是後續發布變更，不能只口頭宣布為全功能正式版。
5. **新站安裝驗證**：第一次部署仍需核對import成功、chart_price_pan.js被包含、無Python/JS錯誤、圖表CDN可載入。既有ZIP不包含平台Secrets。

## 核准後的執行順序

1. 再次核對三個受保護分支與已驗收提交；保留本次備份。
2. 依核准範圍，完成正式命名、環境/依賴及功能範圍整理；如有程式變更，先在允許的開發分支形成新的候選版本，跑CI並複測，再記錄新的核准SHA。
3. 取得對「新正式來源分支」的明確授權後，從最終核准SHA建立release/v1.0-production，不合併main，不變更b3-speed-test。
4. 在Streamlit建立獨立正式App；填入明確分支、app.py及核對過的Python/Secrets/閱覽設定。網址可用性以實際平台回應為準。
5. 新站啟動後先做2330/2308日/週K、來源/警告、上下左右/縮放、手機/桌面驗證；任一核心失敗則不對外宣布。
6. 使用者確認新正式URL與驗收結果後，才更新分享連結/QR。GitHub v1.0.0標籤及Release亦需另行授權，不在本次建立。

## 回退與失敗處理

- 獨立新站方案下，舊main正式站與B3始終保留原分支及網址。新V1出問題時，先停止推廣新URL，提供原正式網址，不改main或B3來修復V1。
- 若新正式分支後續發生問題，用已保存的正常SHA重新建立修復提交或回退部署；執行前需對新正式分支取得授權，不進行force push。
- 網址名稱切換不能假設有自動轉址；不刪除候選站或舊站。
- 回退後同樣以2330/2308查詢及圖表能操作為成功條件，不能只看HTTP200。

## 備份與復原資料

- V1完整來源備份：亞當V1_完整專案備份_45e84cc.zip（程式版本相同，交接文件較早）。
- 既有正式站完整來源：正式站發布前備份_main_9d11d22.zip，11個來源檔案已核對Git blob SHA。
- 最新進度：亞當鏡像V1_進度備份.md；最新驗收：ADAM_V1_HANDOFF_最新.md。
- 網站分支設定證據：發布前_網站分支設定.jpg。
- 本文件不包含密碼、金鑰或Streamlit Secrets。

## 本次完成後的狀態

只更新開發分支上的發布文件。尚未建立正式分支、正式站、v1.0.0標籤或Release；尚未改正式URL或權限，未合併main。

## 官方操作參考

- 建站需明確指定repository、branch及入口檔：https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy
- 部署分支提交通常會觸發網站更新，正式來源不宜跟隨持續變動的開發分支：https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app/edit-your-app
