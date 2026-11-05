# 備援排程方案（未部署，預設關閉）
目前只完成程式與離線模擬測試，不能宣稱雲端Cron已驗證，也不保證準點／必達。原GitHub定時驗證未取得schedule事件，這是用第二個排程來源降低對單一觸發來源的依賴；仍須真實部署驗收。

方案：Cloudflare Workers Cron → GitHub workflow_dispatch(mode=send) → 原提醒工作。
不直接讀行情、不持有Telegram Token、收件人ID或股票名單。沿用原程式的日期檢查、行情品質、防重複與序列執行。GitHub runner也可能延遲；備援不等於保證送達。
備援建議台灣平日14:57／18:27（比原14:47／18:17晚10分鐘）；原排程先執行過的同一訊號會由既有持久紀錄跳過。
程式只接受這兩個Cron字串，公開HTTP呼叫固定404，不能指定其他repo或工作。錯誤不輸出憑證或HTTP內容，網路狀態不明不自動重送dispatch。

## 啟用前必須由本人確認／完成
1. 決定是否使用Cloudflare帳號及適用方案；本次沒有建立帳號、接受條款、訂閱或付費，沒有部署。
2. 建立只選adam-mirror-alerts這一個repo的GitHub fine-grained Token，Actions read/write；不要求Contents write。這仍授予該repo的Actions寫入權限，必須本人確認並完成憑證建立。
3. Token只填Cloudflare的GITHUB_ACTIONS_TOKEN加密Secret，不貼對話、不放原始碼或公開變數。這是新的服務／權限範圍，不能沿用先前Telegram授權。
4. 正式部署前先執行node test_worker.mjs；wrangler.jsonc仍DISPATCH_ENABLED=false、crons=[]。
5. 本人確認啟用後才改DISPATCH_ENABLED=true，crons加入「57 6 * * MON-FRI」「27 10 * * MON-FRI」。Cron按UTC，Cloudflare週日數字與其他cron不同，因此使用星期英文名稱。
6. 先用明確系統測試驗證真正Cloudflare觸發、GitHub dispatch、手機送達與跨來源去重，再宣稱備援成功。Cron異動可能需最多15分鐘傳播。
停用：DISPATCH_ENABLED=false並移除crons。若要停全部Telegram提醒，也把GitHub ALERTS_ENABLED改false。

官方文件：
https://developers.cloudflare.com/workers/configuration/cron-triggers/
https://docs.github.com/en/rest/actions/workflows#create-a-workflow-dispatch-event
