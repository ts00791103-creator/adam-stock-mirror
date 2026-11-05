## Telegram設定進度更新｜2026-11-06
使用者已儲存TELEGRAM_BOT_TOKEN，網頁顯示Repository secret added；check-bot工作42071328128／job127399735010成功，11項測試通過，程式確認Token屬於預期@adam_mirror_007_bot。未讀取Token值，未送真訊息。
目前等待使用者在手機私人機器人傳送本對話提供的/start配對碼，回覆已傳送後才執行find-chat。配對碼只在本對話／本次執行狀態，未寫公開交接。若新對話遺失配對碼，可重新產生並請本人重傳。Token不需重設。ChatID仍未設定、排程推播仍關閉。

# 最新接續狀態｜2026-11-06
以本節為準；下方舊紀錄保留追溯。

## 目前停在這裡
使用者已同意現在設定Telegram Token。GitHub私有提醒專案已建立並部署，但推播仍關閉。
已開啟 https://github.com/ts00791103-creator/adam-mirror-alerts/settings/secrets/actions/new ，填Name TELEGRAM_BOT_TOKEN，交由本人把Token貼入Secret並按Add secret；等本人回覆「Token已設定」。不要讀取或截圖輸入中的Secret、不要請本人貼Token到對話。
CUA瀏覽器2，候選tab2；私有提醒設定tab4（setupTab），Streamlit管理tab1。setupTab已markHandoff；這次Token設定尚未觀察到完成，CUA completion_summary須等交接完成再做。
接著在私有專案Actions執行check-bot，確認@adam_mirror_007_bot；手機傳精確/start隨機配對碼，再find-chat。將唯一私人收件人設TELEGRAM_CHAT_ID Secret，test-message本人確認，再preview與啟用；目前未發任何真實訊息。
Token、ChatID、密碼均不寫程式、備份或本文件。

## 網站目前版本與驗證
原專案只修改release/v1.0-development，最新功能提交 e8879fff9b864e3ff58959fea889d1891751031b。
提醒說明改善提交04db83d76146c5db5f25d972e625a842884a765c；來源診斷7acba3b29a5b7e4fe28b578253fd84d54001caa2。
Actions42069558393：Python3.11與3.14各137項測試通過，獨立背景包11項通過；前階段42068346766各134項。
候選站 https://adam-v1-candidate.streamlit.app/ 已重啟載入根數版。
已實際操作：日K顯示100/260/650；切週K顯示26/78/156；勾自訂顯示三個輸入欄位26/78/156。保留反轉span3/7/14，修改觀察窗不保證完整性或績效，可能改變歷史來源。只對候選版顯示；正式版不變。
新wave_settings.py檢查短至少7、中15、長29，依序遞增且<=5000；錯誤設定st.stop。日/週自訂鍵分開。這一輪尚未用真實行情完整驗收自訂後的全部鏡像圖。
原先四檔全部未判定已查出：Yahoo來源2026-11-05的2330/2308/2317/2454都有O/H/L，但Close均NaN；各243根，Volume無缺漏。不是查不到股票或網路下載失敗。
品質攔截維持，不補收盤、不刪異常列、不借前一天當當日。EntryDataError提供受控公開證據；網頁實測列出日期與收盤價缺漏。全部未判定時改為「尚無法確認」，不再稱沒有條件成立。
來源缺漏仍存在，不能宣稱四檔提醒判定已成功或資料已修好。
證據：outputs/提醒試跑_收盤缺漏提示驗收.jpg、波段根數_週K設定驗收.jpg。
手機視窗模擬set390x844但DOM仍1128x786，未生效，已reset，不能列手機通過；截圖已改名電腦版面複核。

## 獨立私有背景服務
https://github.com/ts00791103-creator/adam-mirror-alerts （Private）
提交57c23d27bb4d665328427e585942ffb0be34977b，13檔，預設分支main屬於這個獨立新專案；原網站main未修改。
連接器已有存取這個私有專案的權限，不必新授權。建立repo因連接器無此能力而用已登入GitHub網頁。
首次手動preview工作42069055672／job127391520928成功，11測試通過；台灣凌晨不在14:00後，時間保護直接跳過掃描，沒有報告、沒有訊息。不能稱真實掃描成功。
工作流預定平日14:47/18:17台灣時間，但ALERTS_ENABLED與config.enabled雙開關仍未啟用，Token/ChatID尚待本人設定；GitHub排程可能延遲或漏排。
worker只接受當日日K、假日或舊資料不發，先持久化pending再送，uncertain不自動重發；原網站repo禁止寫狀態。

## 授權與保存
使用者明確授權測試可直接開網頁、重新登入；測試站/正式站必要時可重啟。本人驗證碼、新增敏感權限仍交由本人。每階段保存並同步雲端交接。
網站正式發布不等於本輪已授權；正式站V1.0.1仍 https://adam-mirror-v1.streamlit.app/。
本輪核對：原main9d11d224e7e49ddec40988e3d782828b48fe0edd、B3 0239e3c374297a1d312a773ccdadb553946a1f1b、release/v1.0-production2369c3cc74e875e80e393f174e52924d4f67dd96，均未變。
完整備份04db83d：92個Git blob逐一SHA一致；outputs/進場提醒_完整程式備份_04db83d.zip。
完整備份e8879ff：94個Git blob逐一SHA一致；outputs/波段根數優化_完整程式備份_e8879ff.zip；SHA256 BF7BBA951D2100497E53A81C81168EF62179EE2F8BF35FA2F5668409455DEAF0。
部署包outputs/Telegram背景提醒_部署包.zip已同步EntryDataError。
全台股與合理價格正式版整合仍待處理，未取消；本輪優先BOT設定、根數與提醒品質。
公開交接文件不需登入閱讀；新對話若要寫GitHub需確認工具/連線權限，不保證永遠免登入。


---
以下為先前紀錄（若與上方衝突，以最新節為準）

# 最新交接｜亞當鏡像與Telegram提醒（2026-11-06）
## 立即接續點
開發程式d0ed81ce8ee54eba1eff7e32f264080c618c8c77，Actions42063754047，Python3.11與3.14皆成功；132項Python測試通過。前版53dfaf6為130項。
候選站https://adam-v1-candidate.streamlit.app/目前實際載入仍為行情品質改善版d2a204b；提醒三步試跑尚未重啟載入、尚未瀏覽器驗收，不能宣稱使用者已能看到。
使用者剛誤關瀏覽器，已重新開啟候選站，確認標題及全市場功能可見。新的CUA瀏覽器ID2，候選tab2；GitHub新repo表單tab3在https://github.com/new。舊tab4/5/8已關，不可沿用。
functions store及Node變數曾因關閉而重置；檔案與GitHub仍完整。Node已重新初始化fs/crypto；沒有本機Python或git執行檔，以GitHub Actions驗證。

## 使用者意圖與授權
使用者持續指示「交給你優化程式」「繼續測試，BOT也排定下去」，希望好上手、可自動提醒進場觀察。
已選Telegram手機推播及箱底反彈／箱頂突破兩種條件。第一版先日K收盤後，不自動下單。
自建公開機器人帳號@adam_mirror_007_bot；已在t.me頁確認顯示「亞當」。已引導手機Telegram找此帳號傳/start。本人表示已傳送；尚未取得或驗證Token/Chat ID，未發任何真實訊息。
Token只由使用者填受保護的後台，不貼對話，不讀取、不寫程式或交接，不截圖Secrets。
使用者已授權測試站與正式站必要時直接重啟，不需逐次詢問；這不代表核准發布新功能、Secrets修改或刪站。
原網站只改release/v1.0-development；main與B3禁止動。正式分支release/v1.0-production仍2369c3cc74e875e80e393f174e52924d4f67dd96／V1.0.1。新功能發布前仍須具體更新內容與驗收。
每階段保存、同步GitHub雲端交接與本機檔，方便新對話讀取。

## 已完成提醒實作（未啟用）
entry_alerts.py：既有箱型與前20日量基準都取訊號日前，不讀未來K線。
箱底反彈預設：前收盤距箱底3%內、本日漲至少0.5%、收高於開盤且仍在箱內。
箱頂突破預設：高於箱頂0.5%至5%、量至少前20日均量1.5倍。共同20日均量>=1000張，箱型20根／20%振幅。均為可調測試參數，非回測最佳值。
entry_alerts_ui.py：三步試跑、進階設定收起來、手機訊息預覽與CSV，網頁永遠不送真實Telegram。試跑結果只存本次瀏覽器工作階段。
alert_delivery.py：持久去重；先存pending，再發送，狀態不明標uncertain不自動重送；持久保存失敗不發送。去重依股票、日期、條件與參數。
scripts/run_entry_alerts.py：預設dry run，需--send、config.enabled=true、ALERTS_ENABLED=true及Token/Chat ID才送。平日14:00後只接受當日日K，假日或舊資料不送。
telegram_setup.py：確認Token屬於預期bot；以精確/start配對碼找唯一私人聊天，禁止猜最後聊天；可人工送明確測試訊息。
worker明確禁止對原adam-stock-mirror專案git寫狀態。

## 背景部署範本與待辦
deploy/alerts-worker/已備妥獨立私有提醒專案範本（本機work/alerts-worker，outputs/Telegram背景提醒_部署包.zip與部署指南）。
預設全關閉；設計台灣平日14:47、18:17檢查，GitHub可能延遲或漏排，不能保證準時／即時送達。
GitHub schedule只在預設分支執行；不動原main/B3，因此需獨立私有提醒專案（建議ts00791103-creator/adam-mirror-alerts），存參數、工作流與持久去重狀態。
目前僅開到new repo表單，尚未建立、沒有付費或新權限變更。正式建立前釐清此獨立新專案範圍，不能用原網站main放排程。
原GitHub連接器沒有create repository或Secrets能力，僅tree/commit/ref。新repo可用已登入GitHub瀏覽器UI建立；新repo之連接器權限也可能需確認。瀏覽器上傳前讀file-uploads文件。
部署步驟：私有repo根目錄放範本→使用者填TELEGRAM_BOT_TOKEN Secret→check-bot→手機傳/start配對碼→find-chat取得唯一收件人→使用者填TELEGRAM_CHAT_ID Secret→test-message本人確認收到→preview→啟用enabled與ALERTS_ENABLED後安排正式send。
原repo內deploy/嵌套工作流不會自動排程，不能宣稱BOT已啟用。沒有Token、Chat ID或新背景repo，仍是待設定。

## 另已授權、尚未實作
使用者認為650長波根數可能太多，已同意優化：日K保留100/260/650；週K改參考26/78/156且可進階自訂。需說明是觀察窗參考，非完整性保證或回測最佳值；改長度可能改變波段結果。先完成提醒試跑，再接續此修改與測試。
全台股正式版整合及合理價格整合仍待處理，並未取消。估價舊介面含大量實驗項，不能整塊直接公開到正式版。

## 已有成果與備份
全市場程式5e35797，曾117項測試通過、官方有效上市1092／上櫃882，合1974，缺漏16另列；預設579初選僅實測20，不能宣稱全部歷史複選完成。
6148原始3根OHLC欄位不一致非精度誤差，已保留攔截並補明細；2y486根可分析，中波足夠、長波650不足。品質改善d2a204b通過120測試、68檔完整備份已核對。
備份位於outputs：全台股階段3/4接續包、行情品質改善階段6包、原正式版完整ZIP及更新前回復ZIP皆在。
最新工作檔work/alerts（提醒與app.py）、work/alerts-worker（獨立部署包）；不是git checkout。根數未實作。
正式網站https://adam-mirror-v1.streamlit.app/仍V1.0.1，包含自選30檔與個人即時報價，並無全市場／新提醒。
main9d11d224e7e49ddec40988e3d782828b48fe0edd、B3 0239e3c374297a1d312a773ccdadb553946a1f1b，保持不變。


---

## 歷史紀錄（以頂端為最新）

# 進場觀察提醒｜階段1實作待驗證
使用者選擇Telegram手機推播，箱底反彈與箱頂突破兩種，並要求易用。已有Telegram但尚在建立自己的機器人；已引導官方@BotFather，不要把Token貼入對話。
目前轉以自動提醒為優先；原全市場正式整合及合理價格整合保留為後續工作，沒有放棄，也未發布。
新增可調參數的日K條件引擎；只用訊號日前的既有箱型及前20日均量。
箱底反彈：前收盤在箱底上方3%內，本日漲幅至少0.5%、收高於開盤且仍在箱內。
箱頂突破：收盤比箱頂高0.5%至5%，成交量至少前20日均量1.5倍。
共同前20日均量至少1000張；箱型20根、振幅20%為測試預設，非投資建議，全部可調。
網頁只有三步試跑，不會發送Telegram；背景worker預設dry run，需要明確enabled、ALERTS_ENABLED=true、--send與Token/Chat ID才可發送。
提醒編號依股票、日期、條件及參數去重。推播前持久保存pending；儲存失敗不送出；送達不明記uncertain且不自動重送。
原網站專案禁止worker寫入狀態；真正背景排程須部署獨立專案。GitHub schedule只在預設分支執行，不修改原main/B3，獨立部署包稍後準備。
本階段僅release/v1.0-development。待CI、候選站操作驗收、Telegram機器人與背景專案設定；不得宣稱自動推播已啟用。正式仍2369c3c。


---

# 行情品質改善｜階段5查證、階段6驗收完成（2026-11-05）
## 最新狀態與授權
使用者在第二輪報告後指示「好 請繼續」，授權繼續查證6148資料異常。
候選站https://adam-v1-candidate.streamlit.app/已載入改善版d2a204b49b0c2887dd303e4c1f451a63bf77a288。
正式站仍V1.0.1／2369c3cc74e875e80e393f174e52924d4f67dd96；沒有發布全市場或本次品質提示改善到正式站。

## 階段5：原始行情查證
只讀診斷提交6d34076fa35dcef9f9024ed1b2535188f93db7f7，Actions42055717873／job127343431615成功。
資料來源Yahoo via yfinance1.8.0、auto_adjust=False、10y、日K；共2429根，最後日期2026-11-05。
|日期|開盤（約）|最高（約）|最低（約）|收盤（約）|收盤超過最高（約）|
|---|---:|---:|---:|---:|---:|
|2020-05-19|10.05|10.05|9.94|10.20|0.15|
|2020-08-21|10.50|10.50|10.10|10.60|0.10|
|2022-06-10|13.45|13.55|13.30|13.70|0.15|
差距約0.10至0.15元，非單純微小浮點精度誤差，來源回傳欄位彼此不一致。未以交易所歷史資料確認哪個欄位錯，也不能據此猜正確價格。
精確原始浮點值另存CSV與JSON；未裁切、刪除或修補原始K線。

## 修正方案與實作
已先向使用者列出問題與方案，才修改開發分支。
1. 保持原品質檢查，仍在鏡像分析前停止。
2. 異常時列最多20根日期、開高低收與原因，保留來源數值。
3. 提示可縮短歷史期間重試，同時提醒可能不足完整中、長波；不自動刪除資料或改價。
4. 全市場結果帶入處補說明：選股用官方日期及一年日K，個股另依所選期間取最新行情，日期與箱型可能不同。
實作：quote_quality.py、新tests/test_quote_quality_details.py、app.py品質攔截後的顯示、full_market_ui.py帶入說明。
audit_ohlc_data、find_pivots、mirror_wave函式原文與正式2369版本逐段核對一致，沒有放寬門檻或改公式。

## 階段6：驗證
最初新增整頁測試被其他AppTest留下的有效行情快取干擾，未觸發拒絕；已僅於測試setUp/tearDown清空快取，未改網站邏輯。
Actions42056699397：Python3.11／3.14各120項Python測試通過，價格軸Node9項及模板檢查成功。3.11日誌確認官方全市場snapshot及歷史日期alignment PASS。
候選站依既有持續授權必要重啟1次，已恢復並完成實際驗收：
- 6148／日K／10y：仍攔截3根異常，明細三個日期及開高低收與只讀證據一致，縮短期間提示顯示；未產生鏡像，符合預期。
- 6148／日K／2y：486根，最新2026-11-05收盤43.40，來源卡片與分析可產生；中波260根條件足夠，長波650根不足提示保留。不能宣稱完整長波驗收。
- 選股帶入說明已加且既有全市場離線UI測試通過；本輪沒有重新逐檔全市場掃描，也未重做全部手機／下載測試。
目前候選瀏覽器停在6148／日K／2y分析結果；重啟後舊全市場進度已重置。

## 備份與接續
程式完整備份：行情品質改善_完整專案備份_d2a204b.zip，68個原始檔逐一核對Git blob SHA一致，另含版本標記。
階段5證據及修改備份：6148查證_階段5原始證據與修改備份.zip。
精確原始證據：6148_原始OHLC異常證據.csv、6148_原始OHLC異常證據.json。
驗收截圖：6148_異常明細改善驗收.jpg、6148_兩年資料分析驗收.jpg。
工作目錄work/ohlc-probe（修改）與work/quality-full-d2a204b（完整快照）；非git checkout，以GitHub連接器及expected_sha更新。
本地outputs/ADAM_V1_HANDOFF_最新.md、行情品質改善_查證與驗收紀錄.md、亞當鏡像V1_進度備份.md同步。完整程式快照內的舊文件以本最新交接為準。
下一步：使用者於候選站確認本次提示與全市場功能；尚無正式發布授權。若要求發布，先補production模式全市場入口與測試，再以具體授權更新正式分支；不要直接搬測試版全部實驗功能。
如需真正修正6148的歷史價，須另找具體交易所歷史來源交叉核對，不能因本次改善便宣稱原始行情已修好。
main維持9d11d224e7e49ddec40988e3d782828b48fe0edd；B3維持0239e3c374297a1d312a773ccdadb553946a1f1b；production維持2369c3c，已核對未變。
持續授權仍有效：使用者允許測試站與正式站必要時重啟，不包含未核准發布、Secrets修改或刪站。每階段保存並更新最新交接。


---

## 歷史紀錄（以頂端為最新）

# 全台股選股｜階段4第二輪實際操作測試（2026-11-05）
候選站：https://adam-v1-candidate.streamlit.app/
程式仍5e35797c663f61d9be4fcd08240b8097adef139e，開發文件基準404fe905acbe131814066513fc002c685f93e70a。
使用者指示「開始測試」，本輪只操作候選站並保存報告，沒有修改程式、重啟站台或發布正式版。

## 逐項結果
|項目|結果|實際操作與證據|
|---|---|---|
|改條件不沿用舊結果|通過|將股價改2259至2261後，提示條件已變更、舊結果隱藏，必須重新初選|
|小批次完整結束|通過|上市＋上櫃2259至2261、當日量及均量>=1000張、近箱底5%；初選1、已檢查1、待0、符合1、無法判定0；下一批按鈕消失並顯示處理完|
|官方日期與歷史資料對齊|通過|上例2330官方與歷史資料同為2026-11-04、收盤2260；不使用11-05較新日K|
|錯誤股價範圍|通過|最低3000、最高2261按初選，顯示最低不可大於最高，未保留舊初選結果|
|單一上櫃市場及零結果|通過|上櫃2259至2261初選0、已0、待0，顯示無符合者，市場統計僅上櫃897公司／882有效／15缺漏|
|上櫃價量與箱型複選|通過|上櫃股價0至100、當日量及20日均量>=1000張：初選89；近箱底5%首10符合0、無法判定0；切不限箱型重新初選及複選，首10符合10、無法判定0，待79|
|缺漏原因另列|通過|展開15筆缺漏表，顯示市場、代號及無法辨識官方價格／量／日期的原因，不混作不符合|
|上櫃帶入商品|通過|選股結果6148驊宏資帶入後，下方顯示6148與上櫃，實際分析使用6148.TWO，非.TW|
|6148十年歷史鏡像|該條件下未完成，品質攔截正常|歷史10y／日K按分析，提示存在3根高低價關係異常K線並停止；尚未取得3根原始資料逐筆查證，不能斷言異常根因|
|6148一年歷史鏡像|通過但資料不足須保留提示|改1y重跑，商品6148.TWO、最新2026-11-05、收盤43.40，來源卡片正常；243根日K不足中波260與長波650，不能視作完整長波驗收|
|瀏覽器錯誤紀錄|本輪讀取時0筆|未觀察到本輪操作的瀏覽器error；不代表所有情境無錯誤|

## 發現、重現與建議
1. 選股以一年日K判定，但帶入個股保留原先十年設定；6148在一年資料可選入，十年分析卻被品質檢查停止。
   重現：全台股→上櫃→股價0至100→當日量與均量1000→不限箱型→初選→分析首批→6148→帶入→日K／10y→分析。
   安全處理：保留品質攔截，不刪除或改寫價格；1y可分析但243根不足完整中長波。
   後續方案：若要修程式，先取得3根原始OHLC及日期，釐清真實資料異常或數值精度問題；帶入成功提示補上選股日期／一年資料與個股最新日期／目前期間可能不同的說明。未經查證不能放寬品質條件、不能把1y當成完整長波。
2. 上市官方行情仍11-04、上櫃11-05。系統已提示並按每檔官方日期截歷史，不是即時全台股。
3. 89檔只實際檢查前10檔，原預設579檔仍僅先前20檔；沒有全數逐檔歷史驗證，不可宣稱全台股全數通過。
4. 本輪沒有實測CSV檔案下載內容，沒有刻意中斷來源製造網站端網路故障；相關離線失敗保護測試沿用先前CI117項結果，不表示本輪重跑CI。

## 保存與接續
截圖：全台股選股_第二輪_完整結束.jpg、全台股選股_第二輪_缺漏項目.jpg、全台股選股_第二輪_十年資料異常攔截.jpg、全台股選股_第二輪_上櫃一年鏡像.jpg。
完整程式備份沿用全台股選股_完整專案備份_5e35797.zip（61檔核對一致）；本輪沒有程式變更。
目前候選瀏覽器測試條件停在上櫃0至100／不限箱型，已檢查10、待79；個股6148／日K／1y。名單與進度仍僅本次瀏覽器工作階段保留。
正式站保持V1.0.1／2369c3c；未修改正式分支、main或B3。
下一步：使用者驗收；如要進一步修正，先核對6148十年資料根因並改善期間／日期提示，再測試。正式發布須另經使用者確認，本輪「開始測試」不是發布授權。
持續授權保留：測試站與正式站必要時可直接重啟，但不擴及未核准發布、Secrets或刪站。


---

## 歷史紀錄（以頂端為最新）

# 全台股選股｜階段3候選站驗收完成（2026-11-05）
## 最新狀態
候選站：https://adam-v1-candidate.streamlit.app/
程式版本：5e35797c663f61d9be4fcd08240b8097adef139e。
只更新release/v1.0-development，正式站仍為V1.0.1／2369c3cc74e875e80e393f174e52924d4f67dd96。
使用者要求每階段保存，方便新對話接續；本次階段1實作、階段2來源修正及驗證、階段3網站驗收均已保存。

## 設計與範圍
新增「全台股選股（分批測試）」；保留自選30檔、原個股鏡像、估價測試與個人報價。
範圍為官方公司名單中的上市／上櫃四碼股票，排除ETF、權證、興櫃；不是所有證券種類。
第一步：官方公司名單與每日行情，依股價與當日成交量（張）初選。
第二步：使用者按「分析下一批（最多10檔）」，讀取Yahoo歷史日K，再套用20日平均量及箱型條件。不批量呼叫即時行情。
以官方每檔行情日期截取歷史K線，捨去較新K棒，避免不同日期或未來資料混用；若歷史缺該日期則無法判定。
清楚顯示市場範圍、日期、缺漏、初選、已檢查、待檢查及無法判定。少數備援股票不冒充全市場。初選依當日量由高至低處理，不是投資推薦排序。
條件改變後舊結果隱藏，須重新取得初選。可下載初選及已檢查CSV，結果可帶入原個股查詢。
來源：https://openapi.twse.com.tw/v1/opendata/t187ap03_L、https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL、https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap03_O、https://www.tpex.org.tw/openapi/v1/tpex_mainboard_quotes。

## 驗證結果
CI 42049552472，Python3.11／3.14各117項Python測試通過，9項Node價格軸測試及圖表模板／既有行情鏡像檢查成功。
兩個工作日誌均確認官方全市場snapshot PASS及上市、上櫃歷史日期alignment PASS，而非只看允許失敗的步驟結論。
真實官方結果：
- 上市：公司1093檔，有效每日行情1092檔，缺漏／無效1檔，行情日期2026-11-04。
- 上櫃：公司897檔，有效每日行情882檔，缺漏／無效15檔，行情日期2026-11-05。
- 合計有效1974檔；16檔缺漏另列，並非不符合。
最初實作曾發現TPEx公司名單英文欄位差異，已修正並重跑成功。TWSE行情比Yahoo晚一天，已改以官方日期截取歷史資料。
候選站實際操作：
1. 預設上市＋上櫃、股價0至10000、官方當日量>=1000張：初選579檔。
2. 第一批：已檢查10、待檢查569、符合0、無法判定0。
3. 第二批：累計已檢查20、待檢查559、符合2、無法判定0；未重複處理，部分結果警示正常。
4. 結果「帶入這檔股票查看鏡像」後，下方成功切至2883凱基金；未把本次測試符合者當成投資推薦。
5. 390px手機寬度模擬版面確認正常，非所有實機驗證。
離線UI測試另驗證12檔跨批完整處理、結果選取、條件變更隱藏舊結果、日期缺漏不得計為不符合。

## 限制與下一步
尚未處理其餘559檔歷史複選，不可宣稱全部579檔已驗證。使用者可繼續逐批檢查；網路錯誤個別列出。
官方資料可能尚未更新或休市；以各檔日期為準。不同市場日期可不同，不是即時全市場選股。
名單／進度僅目前瀏覽器工作階段保留；重啟可能遺失，重要結果請下載CSV。
帶入個股分析會重新使用該頁的最新資料，可能與官方初選日期不同，請核對兩邊日期。
免費資料源可能限流，歷史資料最多15分鐘快取，單批最多10檔降低負載。沒有承諾秒級完整掃描或自動背景排程。
下一步：使用者在候選站驗收。尚未取得本功能正式發布授權；不可因必要重啟授權而移動正式分支。若要求發布，先開啟production模式入口、補測正式入口流程，再依具體發布授權更新正式分支。
正式站與main／B3維持原版本；最後核對main9d11d224e7e49ddec40988e3d782828b48fe0edd、B3 0239e3c374297a1d312a773ccdadb553946a1f1b、production2369c3c。

## 備份與接續
程式完整快照：全台股選股_完整專案備份_5e35797.zip（61個原始檔逐一核對Git blob SHA一致）；階段1修改備份70e75c8及來源修正備份5e35797另存。
本機最新交接：outputs/ADAM_V1_HANDOFF_最新.md；階段進度：outputs/全台股選股_階段接續紀錄.md。
驗收截圖：全台股選股_全市場涵蓋與進度.jpg、全台股選股_前二十檔複選結果.jpg、全台股選股_手機版面.jpg。
程式在work/market及work/market-full-5e35797；非git checkout，使用GitHub連接器提交，期望SHA防覆蓋；本機沒有Python，以GitHub Actions跑測試。
跨對話接續時先讀本文件與GitHub ADAM_V1_HANDOFF.md頂端，不要重做已驗收步驟。

## 持續授權
使用者明確表示：「測試站與正式站在必要時都可重啟。」可直接重啟adam-v1-candidate或adam-mirror-v1，記錄原因及恢復結果即可，不須每次詢問。
此授權不包括發布未核准新功能、Secrets修改、刪站、main/B3變更。


---

## 歷史紀錄（以頂端為最新）

# 全台股選股階段1：實作待驗證（2026-11-05）
只在release/v1.0-development開發，正式版2369c3c不動。使用者要求每階段保存方便新對話接續。
設計已實作：官方上市上櫃公司名單＋每日行情初選，再每批10檔歷史日K複選。分開當日量與20日均量、分開未處理／無法判定／不符合、日期不一致不判定、部分來源失敗明確標示。
工作來源：market_universe.py、full_market_ui.py、app.py候選入口；tests/test_full_market.py；scripts/live_market_smoke.py；CI新增官方來源probe。
尚待本次CI與真實官方欄位驗證，再候選站操作驗收；不得宣稱已全市場通過或正式發布。原自選名單與即時價格保留。


---

# V1.0.1 正式發布完成｜2026-11-05
正式網址：https://adam-mirror-v1.streamlit.app/
使用者確認測試報價正常並明確授權更新正式版，後續自行完成正式站Secrets設定及報價查詢。
正式凍結程式：2369c3cc74e875e80e393f174e52924d4f67dd96；分支release/v1.0-production；入口production_app.py；Python3.11。
功能：自選名單最多30檔、股價／20日均量／有效箱型篩選、結果帶入個股、CSV、受密碼保護的個人即時價格（單次查詢或自願每10秒更新）。
正式站實測：4檔篩選有效4檔，結果帶入2330成功；日K與鏡像來源正常。正式站設定已讀取，使用者自行驗證報價後由瀏覽器核對2330最新成交2240、漲跌-20、-0.88%，成交時間2026-11-05 13:30:00台灣時間。驗收時已收盤，畫面正確顯示資料超過90秒提示。此結果驗證最近成交可用，未驗證開盤時延遲或每一筆交易。
CI 42044974987：Python3.11和3.14各110項Python測試通過，既有9項價格軸Node測試與圖表模板／真實行情檢查成功。
main維持9d11d224e7e49ddec40988e3d782828b48fe0edd；B3維持0239e3c374297a1d312a773ccdadb553946a1f1b。沒有合併main/B3，未建立GitHub Release或tag。
完整備份：亞當V1.0.1_正式版完整備份_2369c3c.zip，55個原始檔逐一核對Git blob SHA一致。
回復備份：V1.0.1更新前_正式版回復備份_60cef83.zip。
驗收截圖：V1.0.1_正式站選股上線.jpg、V1.0.1_正式報價驗收.png（只含公開報價與狀態）。
未讀取或保存Secrets；報價設定留在Streamlit後台，不包含在程式備份中。日後搬站需使用者重新設定金鑰與報價密碼。
合理價格估值仍只在候選站；選股用歷史日K，不因即時報價而重新計算。名單／結果僅工作階段保存，重要結果請下載CSV。
本文件同步到開發分支；正式來源保持2369c3c。後續變更先測試再由使用者確認發布。歷史文件若記載尚待設定或驗收，以本段完成紀錄為準。


---

## 歷史紀錄（以頂端為最新）

# 自選名單選股與即時價格整合（2026-11-05）
## 範圍與授權
使用者選擇「先做自選名單篩選」，另要求即時價格也準備加入正式版，但明確選擇「先測試再確認發布」。
修改只在release/v1.0-development；正式來源release/v1.0-production維持60cef83，未發布本階段功能。
程式版本：d12475bd7a03882c343b3bb2ceb2987d379fa510。
候選站：https://adam-v1-candidate.streamlit.app/

## 功能
- 自選名單最多30檔，代號／完整中文名稱／明確TW或TWO後綴，重複股票去除。
- 日K股價範圍、20日平均成交量（張）、不限箱型／箱內整理／接近箱底，以及箱型參數可調。
- 原有箱型演算法共用；只有延續至最新K棒的整理箱型可作目前箱底，歷史已突破箱型不冒充有效支撐。
- 顯示每檔資料日期、20日均量、當日相對量、箱頂箱底與距離；符合與所有有效行情皆可查看，CSV含有效行情與符合欄位。
- 錯字、缺欄位、空資料、無效OHLC或成交量等失敗另列；不計為不符合。條件變更會隱藏舊結果並要求重新篩選。
- 結果可帶入下方個股查詢，再按原本分析按鈕查看鏡像與估價。
- 即時價格保留FUGLE_API_KEY與LIVE_QUOTE_PASSWORD保護，新增「查詢一次最新成交價」，並保留自願啟用每10秒更新。單次查詢不啟動自動輪詢。
- 報價顯示目前股票、成交時間與過舊提示，無效報價與連線失敗不繼續展示舊價格；不改寫歷史K線與選股結果。
- 開發分支production_app.py已準備正式版報價入口；正式網站凍結版本未改動。估價功能仍逐檔使用，未作批次估值篩選。

## 驗證
GitHub Actions 42043540275：Python3.11／3.14各109項Python測試通過，9項價格軸Node測試、圖表模板及既有真實行情／鏡像煙霧檢查皆成功。
實際候選站操作：
1. 名單2330／2308／2317／2454，預設股價範圍、均量>=1000張、不限箱型：有效4檔，符合4檔，失敗0。
2. 切換接近箱底5%：先顯示需重新篩選；執行後符合2檔。這是測試當時資料與條件的結果，不是推薦名單。
3. 使用這檔股票：下方股票查詢與名稱成功切換2330。
4. 名單2330,2308,不存在,2330：有效2檔，符合1檔，失敗1筆；重複去除、錯字另列。
5. 即時報價真實來源尚待使用者在網站輸入個人報價密碼驗收。測試站已出現密碼欄位；未讀取或記錄密碼。單次查詢、密碼拒絕、無效數值與連線失敗經離線UI測試通過。
截圖：選股功能_箱底篩選實測.jpg。
備份：亞當V1_選股與報價完整備份_d12475b.zip；54個原始檔逐一核對Git blob SHA一致。

## 限制與接續
選股使用Yahoo歷史日K與最多15分鐘快取，盤中日K未完成；不是30檔即時掃描。請看各檔資料日期。名單與結果僅在當前瀏覽器工作階段保留，重啟或開新工作階段需重輸入；可下載CSV保存。
目前富果免費方案官方表列5訂閱、日內60次/分鐘；單一使用者每10秒1檔約6次/分鐘，多使用者需合併計算。付費增加容量不等同價格更準確，現有10秒輪詢不會因付費變成逐筆推送。資料權限以供應商實際帳號為準。
正式站更新須先完成使用者真實報價驗收與確認發布；勿因本文件移動正式分支、main或B3。

候選站第二次重啟後已確認新報價說明與密碼保護入口；390px手機寬度選股介面檢查完成。截圖另存「即時價格_新版密碼入口.jpg」「選股功能_手機版面.jpg」。實際供應商報價仍待使用者於網站輸入密碼驗收。


---

## 歷史紀錄（以頂端為最新）

# 亞當鏡像 V1.0 正式上線紀錄

日期：2026-11-05（台灣時間）

正式網址：https://adam-mirror-v1.streamlit.app/
候選站：https://adam-v1-candidate.streamlit.app/

## 授權與部署
使用者在獨立正式分支／獨立正式站的具體方案後指示「開始執行」，授權此次部署。沒有合併 main 或 B3。
正式來源：release/v1.0-production
凍結程式：60cef83ae292d30b5e4ab78356bd0ccfe4f90240
入口：production_app.py
部署介面選擇：Python 3.11；根目錄 requirements.txt 已固定依賴版本。
正式頁標題：亞當鏡像分析 V1.0；圖表版本 V1.0.0。
正式模式提供台股／ETF、日K／週K核心功能；候選站保留實驗功能。此次未建立 GitHub Release 或標籤。

## 檢查結果
|項目|結果|證據與範圍|
|---|---|---|
|部署與啟動|通過|新網址實際載入正式標題、V1.0.0，並完成真實行情分析|
|2330 台積電日K|通過|2026-11-05 收盤2240，短／中／長鏡像與來源卡片皆出現|
|2308 台達電日K|通過|2026-11-05 收盤1130；中長波共用2026-09-14至10-06，警示正常|
|2330 台積電週K|通過|最新週標記2026-11-02，收盤2240；三波12／2／11根|
|2308 台達電週K|通過|最新週標記2026-11-02，收盤1130；中波-420、長波-995.5提示正常|
|上下／左右拖曳|通過|正式站桌面實際操作；價格刻度移動、時間範圍移動|
|滾輪縮放|通過|正式站桌面實際操作，K棒間距隨縮放改變|
|手機版面|通過（390px模擬）|來源卡片直向排列、按鈕換行、價格標籤簡化，截圖留存|
|手機觸控|先前候選站使用者實機通過|使用者對查詢、左右／上下拖曳、雙指縮放、週K回覆「都可以」；正式網址尚未另做使用者實機驗收，未推廣至所有裝置|
|程式與瀏覽器錯誤|通過本次流程|分析正常完成；本次正式站瀏覽器error紀錄為空，並非保證所有情況均無錯誤|
|自動驗證|通過|CI 42037752365，Python3.11與3.14各99項Python測試，9項價格軸Node測試、圖表模板與Yahoo行情鏡像檢查通過|

## 保護與備份
main：9d11d224e7e49ddec40988e3d782828b48fe0edd（未修改）
b3-speed-test：0239e3c374297a1d312a773ccdadb553946a1f1b（未修改）
正式分支仍指向60cef83；本次紀錄只追加開發分支，正式程式保持凍結。
完整正式版49個檔案已逐一比對Git blob SHA，全部一致，存於本機完整備份ZIP。原main與候選版備份也保留。

## 已知限制與後續
1. 週K「最新資料」是該週起日，最新週可能尚未結束。
2. 10年週K不足650根時長波會顯示資料不足提示，屬有限資料情境。
3. 鏡像可能產生零或負數，保留數學結果並提示，不可當成可交易股價。
4. 未來日期未完整排除台股休市日；鏡像不是未來價格預測。
5. 圖表操作文字仍含「手機待實機驗收」，與先前候選站已完成的單一手機回報不一致，列為後續文案修正；本次不為文案變更重新移動正式來源。
6. 正式版使用新網址；原候選站QR碼仍導向候選站，請勿混用。
7. 後續程式變更先在release/v1.0-development測試，經使用者確認後再另行更新正式來源；不要修改main或B3。回復時依完整備份與本文件凍結SHA部署，勿直接合併main。


---

## 歷史交接紀錄（以下包含發布前狀態，以本文件頂端為最新）

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

## 2026-11-05｜瀏覽器驗收後第一批修正
- 管理頁確認候選站 https://adam-v1-candidate.streamlit.app/ 對應 release/v1.0-development；原 adam-mirror-v1-test 網址登入後仍 not_found。
- 實測候選站仍顯示 B3 Pro、沒有來源卡片，但目前分支已有 V1.0 標題、來源卡片及重複警示。屬執行版本差異，尚未證明最新程式的來源卡片失效；需核對候選站部署日誌，不可誤稱已修好部署。
- 程式已使用獨立 volume priceScale；先前瀏覽器測試報告的「量價共用刻度」推論更正。
- 新增 projection_warnings，揭露零／負數與非有限鏡像值，不裁切結果、不修改左右反轉公式；新增離線測試。
- 圖表版本統一為 V1-UI-1105，移除以 BOX-1125C 字串猜測新舊元件的錯誤診斷。操作說明依手機圖表／Plotly 分流。iframe 高度 720，預留手機標題與三波切換換行空間。
- 上下手勢仍沿用原本有限視覺平移，未完成價格軸平移；雙指觸控未實機驗證。沒有新增上下按鈕。
- 本機沒有可執行 Python，已檢查內嵌 JavaScript 語法；Python 編譯及離線測試需以本次提交的 CI 結果為準。main、b3-speed-test 不修改，不合併、不正式發布。

## 2026-11-05｜價格軸平移階段（V1-PAN-1105）
- 使用者授權依規劃持續開發，正式發布前由使用者測試；要求定期備份。本機 outputs/亞當鏡像V1_進度備份.md 與本階段修改 ZIP 可接續工作，GitHub 提交保存遠端版本。
- 第一批 V1-UI-1105 已由使用者 Reboot 後驗證：V1.0 標題、來源卡片、2308 日K中長波重複警示、週K -420/-995.5 提示、390px 卡片換行均正常。第一批 CI run 42026405282 全部成功。
- 本階段移除 mobile_chart.py 的 translate3d 整圖平移，新增 chart_price_pan.js 控制器，用 autoscaleInfoProvider 平移所有股價序列可視價格範圍，不改變行情或鏡像值。成交量保留獨立刻度，箱型依 priceToCoordinate 重畫。
- 滑鼠與單指使用相同控制器；雙指時取消單指狀態，保留原生 pinch。滑鼠雙擊右側價格軸可還原。原始股票／鏡像公式不變，未新增上下按鈕。
- Node 9 項行為測試本機通過（含往返原點恢復原始範圍，避免起始防抖閾值留下殘餘偏移）；兩段內嵌 JavaScript 語法通過。CI 新增 Run chart price pan behavior tests。既有觸控靜態測試已更新為價格軸機制。
- 以合成行情瀏覽器實測向下100px、向上200px、左右拖曳、滾輪縮放、雙擊軸還原皆有效；K線/箱型同步，量能區域固定，未出現 console error/warn。這不是實際股票或手機多指驗收。
- 待續：核對本次 CI 成功；候選站載入 V1-PAN-1105 後，用 2330/2308 真實行情複測，再由使用者實機雙指驗收。不要把尚未驗收的手機手勢宣稱完成。
- main/b3-speed-test 不修改；不合併、不正式發布。

## 2026-11-05｜價格軸實站驗收與手機可讀性階段
- 程式提交 cc550d256a2fc0c0ef77b4f15ac5c1e946b5b9dd 的 CI run 42029091502 全部成功：Python 編譯、離線回歸、9項 Node 價格軸測試、兩項實際行情 smoke check。
- 使用者明確授權這次與後續開發驗證重啟 adam-v1-candidate 候選站；不包括 main/B3 正式站。20:42（台北）重啟後已確認 V1-PAN-1105。
- 真實2308日K上下往返移動、2330日K向上移動/雙擊價格軸還原通過；K線、鏡像、箱型對齊，量能區域固定。390px手機版時間軸與圖表底部可見。重啟期間的一筆 WebSocket 1006 警告與斷線時間一致，恢復後圖表可用；不是零警告。
- 已做完整專案快照 cc550d2（44檔＋提交標記）與進度備份，不只修改檔案。
- 手機可讀性新版本 V1-READ-1105：小於600px時隱藏線條價格軸文字標籤，保留三波切換按鈕與來源卡片；放大至電腦寬度恢復標籤。
- 修正初次載入行情欄位：從包含前收/量能的 byTime 資料顯示最新K棒，避免漲跌與成交量初始為空值。未變更數據、鏡像公式或價格軸拖曳機制。
- tests/test_chart_render.cjs 在 Node VM 執行實際模板腳本，驗證初始漲跌/量能、手機/電腦標籤切換、不覆蓋價格軸provider、空行情安全性；本機已通過，加入CI。
- 此批待CI與候選站重新載入後驗證。手機多指手勢仍待使用者實機驗收；不正式發布、不合併。

## 2026-11-05｜V1-READ-1105 候選站驗證完成
- 程式提交 45e84cc496f045404371b00ee1aee672a36047e5；CI run 42030429977 全部步驟成功，含 Python 編譯、離線回歸、價格軸/模板 Node 測試及兩項真實行情檢查。
- 依使用者持續授權重啟候選站，已確認實際載入 V1-READ-1105。2308 日K初始漲跌 -7.38%、成交量 19,927.91 張正常呈現；390px 隱藏擁擠線條標籤，還原電腦寬度後標籤恢復。
- 最後瀏覽器 error 紀錄為空。重啟期間曾有預期斷線警告，不宣稱整段期間零警告。
- 完整45檔專案快照已核對 Git blob SHA，全數相符；本機保存 outputs/亞當V1_完整專案備份_45e84cc.zip 與 outputs/亞當鏡像V1_進度備份.md。cc550d2 舊備份保留供回退。
- 下一步由使用者真實手機驗收雙指縮放與單指上下左右移動；目前工具不能模擬真實多指手勢，因此此項不標記通過。完成使用者驗收前，不合併、不正式發布。

## 2026-11-05｜使用者手機驗收通過
- 使用者在手機開啟候選測試站後，依五項清單測試並回覆「都可以」：2330/2308 查詢、單指左右拖曳、單指上下拖曳（含圖線/箱型對齊及往返）、雙指縮放後繼續拖曳、週K切換與手勢。
- 本次為使用者實機回報，對應候選版本 V1-READ-1105；沒有取得手機型號、作業系統或瀏覽器版本，因此不可外推為所有裝置皆已驗證。
- 來源重複警告此前已有瀏覽器驗證；本次使用者沒有逐項另述警告結果。
- 程式提交45e84cc496f045404371b00ee1aee672a36047e5與已驗證程式不變。本次只記錄驗收，不合併、不正式發布；維持release/v1.0-development分支限制。

## 2026-11-05｜正式發布準備（未發布）
- 使用者要求「準備發布正式版」。本次僅整理方案、說明草稿、檢查表及備份，未合併、建正式分支/新站、改正式URL/權限、建立標籤或Release。
- 以07f76db為基準比較main，開發分支275筆獨有提交、main41筆獨有提交，不能直接當作快進發布。建議獨立V1正式站與從最終核准SHA建立的凍結正式來源分支；建立新分支仍需另取得明確授權。
- 最新07f76db的CI run42034935253：97項Python、9項價格軸、模板顯示與兩項真實行情步驟全成功，並看過日誌PASS。45e84cc至07f76db僅ADAM交接文件差異。
- 檢查出未鎖依賴、CI3.11/候選3.14.10差異，以及CI額外安裝HTML解析依賴。新增正式版/依賴調整需先形成新候選並測試；附加財報/期貨/即時功能未納入本次完整驗收。
- tx-daily-update.yml會寫B3，不執行；site-health.yml目前只測舊正式URL的HTTP，不是V1功能監控。
- 已保存舊main 9d11d22全11檔來源備份並比對blob SHA無差異。main/B3保留原提交與站址。
- 新文件V1_PUBLICATION_PLAN.md與V1_RELEASE_NOTES_DRAFT.md；更新過時的V1_RELEASE_CHECKLIST.md、V1_DEPLOY_GUIDE.md。輸出備份在outputs/亞當鏡像V1_正式發布準備方案.md等及正式站發布前備份_main_9d11d22.zip。
- 建議正式網址adam-mirror-v1.streamlit.app僅為提案，未檢查可用性、未建立。下一步先確認方案/授權範圍，再做發布前候選整理；不得把本次「準備」解讀成已准許正式發布。
