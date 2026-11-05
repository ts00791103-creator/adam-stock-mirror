## 排程實測進行中｜2026-11-06
使用者授權繼續測試排程與推播並每階段保存。已部署有截止時間的獨立Temporary system schedule verification，預定台灣07:20與07:25（UTC11/5 23:20/23:25）真正schedule事件；GitHub可能延遲或漏排。截止台灣08:00後程式直接跳過發送。
第一次用正式deliver_once與commit_checkpoint在state/scheduler_verification.json先持久化，再送明確系統測試訊息（非股票訊號）；第二次新runner讀回sent，應duplicate_skipped不再送。若pending/uncertain不重試、報錯。此實測不可冒稱下午14:47/18:17真實股票排程或真實訊號已驗收。
開發程式提交31e7f614932ebefe180ad749eaba110ffa5676c7／CI42128248776成功；主程式137項測試，獨立包13項。私有驗證提交95dd3cf9f5f2d88153f91eadadeb54de48c6d4ba／CI42128253990的push驗證13項成功，verify工作因非schedule正確跳過。
目前尚待真正定時觸發結果，不可宣稱排程成功。驗證後須移除臨時schedule，保留狀態與證據。原entry-alerts.yml正式時段未改。outputs/排程推播驗證_完整備份_95dd3cf.zip含17個Git blob逐一SHA一致，不含Secrets。outputs/排程推播驗證_階段紀錄.md保存接續點。

## Telegram啟用完成更新｜2026-11-06
已完成唯一私人聊天配對，使用者明確同意將收件人ID存入私有GitHub專案加密設定並發送連線測試；TELEGRAM_CHAT_ID已儲存。test-message工作42072376429成功，使用者親自確認手機收到。
背景配置enabled=true與Actions Variable ALERTS_ENABLED=true皆已啟用並讀回確認。追蹤名單已依使用者更新為六檔；個人名單與參數以私有專案alerts_config.json為準，不在公開交接列出。台灣平日14:47/18:17檢查，可能延遲或漏排。首次真正定時觸發、真實訊號推播與真實state push尚未驗證，不能宣稱已完成。
私有專案e1df345ca7fbbc2f0a7f24267f2505ac93f2416a為六檔配置版本；SETUP_STATUS.md已保存收訊、啟用與待驗證紀錄。網站與背景名單分開，修改網站不自動更新背景。
本機outputs/Telegram背景提醒_六檔設定備份_e1df345.zip，13個Git blob逐一SHA比對一致，不含Secrets。手機已完成連線測試，不需重新設定Token或重新配對。

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

