# 排程與推播驗證結果｜2026-11-06 08:00（台灣）
## 已通過
- 手機本人先前確認手動連線訊息送達（42072376429）。
- 正式deliver_once與commit_checkpoint真實Git保存；新runner讀回後duplicate_skipped：42129294532，兩次telegram_calls=0。
- 主程式Python3.11/3.14各137項、背景包13項，備援模擬8項通過。
## 未通過
本次07:20至08:00定時觀察，GitHub API沒有任何event=schedule紀錄。原兩個指定時間、每5分鐘重查及一次UI停用再啟用後皆未取得自動觸發證據。不能稱自動排程或自動推播已正常；根因仍未確定，也不能斷言永遠不會執行。
這是無須股票行情的系統驗證，未開盤不能解釋沒有schedule紀錄。沒有以手動dispatch或push驗證冒充自動排程成功。本輪沒有新增Telegram訊息或真實股票訊號。
## 已清理與保留
臨時scheduler-verification.yml已移除schedule並改名Archived；其原程式硬截止08:00，晚到的驗證也不能發送訊息。保留手動驗證入口與歷史結果。
正式entry-alerts.yml保持台灣平日14:47／18:17、六檔名單與啟用開關；下午真實日K與原正式排程尚待驗證。這不等於已認定正式排程可靠。
state/storage_verification.json是假傳輸的獨立測試紀錄，不是實際Telegram送達紀錄。正式股票state沒有污染。
## 備援修正方案（未部署）
deploy/fallback-scheduler（原網站release/v1.0-development提交789d6fa9fb62e72fe3625c5568f85d86710d3dd7）已準備：Cloudflare Cron在原時段晚10分鐘dispatch既有GitHub工作，沿用既有行情品質、時段、去重與序列執行。
8項離線模擬通過，不代表Cloudflare真實部署、Cron或手機推播通過。預設DISPATCH_ENABLED=false、crons空。需要本人確認新服務與只限提醒repo的Actions寫入憑證；未建立帳號、未接受條款、未部署或付費。
## 保存
outputs/排程推播驗證_存儲驗證通過完整備份.zip：21個Git blob逐一SHA一致。
outputs/備援排程_未部署審閱包.zip；階段紀錄與分項結果均保存。不含Token、私人收件人ID或聊天內容。
