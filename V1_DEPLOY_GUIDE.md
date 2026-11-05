# 亞當 V1.0 候選網站部署指南（繁體中文）

紀錄日期：2026-11-05

## 目的
建立第二個 Streamlit Community Cloud App，測試亞當 V1.0，**不覆蓋**原本 B3 測試站。

## 已確認設定
- GitHub repository：`ts00791103-creator/adam-stock-mirror`
- Branch：`release/v1.0-development`
- Main file path：`app.py`
- Python dependencies：`requirements.txt`
- 原 B3 測試站：https://adam-b3-box-test.streamlit.app/

## 部署操作
1. 登入 https://share.streamlit.io/ ，選擇 **Create app / New app**。
2. 選擇 **Deploy a public app from GitHub**。
3. Repository：`ts00791103-creator/adam-stock-mirror`。
4. Branch：`release/v1.0-development`（不是 main，也不是 b3-speed-test）。
5. Main file path：`app.py`。
6. App URL：選一個新的名稱，例如 `adam-v1-candidate`（若已被使用，請選其他名稱）。此名稱只是建議，**不代表網址已建立**。
7. 按 Deploy，等待畫面顯示啟動完成。記下實際候選站網址，並檢查啟動日誌。

## 手機驗收清單
- [ ] 開啟網站，無啟動錯誤
- [ ] 輸入 2330、2308 等代號能讀到資料
- [ ] 日K／週K／月K 可以切換
- [ ] 短中長鏡像正確顯示
- [ ] 箱型支撐壓力可顯示
- [ ] 單指左右拖曳 K 線
- [ ] 單指上下拖曳 K 線（確認不會誤捲動整頁）
- [ ] 雙指縮放
- [ ] 移動後不突然跳回原位
- [ ] 重新整理／切換標的後畫面合理
- [ ] 網路失敗或資料不足時有可理解的提示

## 重要限制
- GitHub Actions 綠燈僅代表目前 CI 涵蓋的測試通過，並非網站部署成功或手機操作驗收完成。
- 目前手機圖表 touch-action:none 與 vertTouchDrag:true 尚未實機驗收。
- 未來鏡像日期對交易所假日及盤中休市的處理仍待完善。
- 不要把候選站直接指向 B3 現有 app，否則會覆蓋原 B3 的設定。

## 部署後
將候選站實際 URL、測試結果和發現的錯誤回報，更新 ADAM_V1_HANDOFF.md。完成驗收前，不合併至 main。
