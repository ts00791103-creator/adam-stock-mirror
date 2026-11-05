# 亞當V1.0部署接續指南

2026-11-05更新。這是已建候選站及未執行正式發布的接續紀錄，不是重新建立候選站的指令。

## 現有網站
- 候選站：https://adam-v1-candidate.streamlit.app/；release/v1.0-development；app.py；實際版本V1-READ-1105。
- 舊正式站：https://adam-stock-mirror-mkxgzfcscdedtpfd6zx88v.streamlit.app/；main；保持原樣。
- B3測試站：https://adam-b3-box-test.streamlit.app/；b3-speed-test；保持原樣。
- adam-mirror-v1-test.streamlit.app不是有效候選入口，請勿再用。

## 已完成
- 早期網站執行舊B3版本的問題，已透過使用者及後續授權Reboot更新；目前來源卡片/版本標識正常。
- 上下拖曳已改為價格範圍平移，移除translate3d暫行方式。桌面與真實手機操作已有驗收紀錄，不再列為「尚未實機驗收」。
- 使用者手機五項：查詢、左右、上下、雙指、週K均回覆可用；未知裝置/瀏覽器，不擴大相容性結論。
- 使用者授權可在開發驗證時重啟候選站；不包含舊正式站或B3，不等同正式發布授權。

## 下一個正式發布步驟
- 詳見V1_PUBLICATION_PLAN.md與V1_RELEASE_CHECKLIST.md。
- 建議獨立V1正式站與凍結來源分支，避免main的41筆獨有提交被不經審核地合併。
- 目前只能修改開發分支；新正式來源分支、新站、正式URL、閱覽權限、標籤/Release都尚未建立或變更。
- 不把開發分支直接當永久正式來源，因部署來源更新通常會更新網站。

## 維運注意
- requirements.txt尚未鎖版；候選站Python3.14.10與CI3.11有差異。正式新站需核對/記錄環境，不能只複製舊文件的預設版本。
- 核心鏡像使用Yahoo歷史資料，非即時行情；Fugle金鑰/密碼只在平台Secrets，不寫入檔案或GitHub。
- 額外估價、期貨及即時功能仍是測試功能；本次驗收不能擴大成全功能保證。
- 若候選站未同步，先核對實際版本與日誌，再依既有授權重啟候選站；不要修改main/B3以解決候選站同步。
- 回退以正常提交與舊正式站URL為基準，不刪站、不force push。
