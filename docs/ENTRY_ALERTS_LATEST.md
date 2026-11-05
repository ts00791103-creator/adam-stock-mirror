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
