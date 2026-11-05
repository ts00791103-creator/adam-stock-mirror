# 亞當鏡像｜Telegram進場觀察提醒
這是獨立背景程式，與Streamlit網站分開。只能部署在自己的私有GitHub專案；預設不推播。
原網站專案adam-stock-mirror的main、B3、正式網站都不需要修改。

## 先試跑，再啟用
1. 建立私有提醒專案（建議adam-mirror-alerts），將本資料夾內容放在新專案預設分支根目錄。不可放到原網站專案根目錄。排程只會在預設分支執行。
2. Settings → Secrets and variables → Actions → Secrets，新增TELEGRAM_BOT_TOKEN；Token只填這裡，不要放程式、對話或截圖。
3. Actions → Adam entry observation reminders → Run workflow，先選check-bot，確認Token屬於@adam_mirror_007_bot。
   在自己的機器人傳「/start 配對碼」，配對碼用8至64個英數字元，例如自己隨機產生的一組。
   再執行find-chat，在setup_code填同一組配對碼；程式只接受唯一私人聊天，絕不猜最近收件人。
   把私有工作日誌顯示的收件人ID存成TELEGRAM_CHAT_ID Secret。
   執行test-message並親自確認手機收到；這是測試訊息，不是進場提醒。
4. 編輯alerts_config.json中的股票名單與門檻。先執行preview看報告，確認後才將enabled改true，並在Variables新增ALERTS_ENABLED=true。
   兩個開關皆啟用，且執行send或到排程時間，才會真正推播。停用時把ALERTS_ENABLED改false。

## 如何使用
- 最多30檔自選台股，用2330.TW／6488.TWO格式。
- 兩種可調條件：箱底反彈、箱頂突破放量。預設是測試參數，不保證適合所有股票。
- 預定台灣交易平日14:47、18:17檢查；GitHub可能延遲或漏排，不承諾準時、即時或保證送達。
- 只接受當日已收盤日K，14:00前及週末不執行推播；假日或來源仍是前日資料不發舊提醒。
- 同一股票、交易日、條件及參數只提醒一次；第二次排程可補看稍晚更新資料。
- 箱型與均量用訊號日前資料，資料品質異常直接未判定，沒有數字就不猜。
- state/alerts.json持久保存提醒紀錄，推播前先commit/push狀態，保存失敗就不推播。
- Telegram送達狀態不明會記uncertain，不自動重送；請本人先核對手機，再決定人工處理，避免重複。
- 僅允許單一worker；工作流程已限制concurrency。不要另開第二個服務讀寫相同state檔案。
- 所有提醒是條件到達的觀察資訊，不是保證上漲、不自動下單。

## 驗證與還原
純規則、去重、失敗保護測試：python -m unittest discover -s tests -v。
手機訊息只有實際完成Token／收件人設定並按test-message後才能驗證。
網站內三步試跑與背景配置分開；網站調參不會自動修改這裡的持久設定。以本專案alerts_config.json為背景實際參數。
停用可保留state及報告，不要刪除紀錄後立即重開推播，否則相同訊號可能重送。

官方文件：
https://core.telegram.org/bots/tutorial
https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule
