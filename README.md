
# Twitter Opinion Monitor · 推特舆情监控

实时抓取多位国家领导人推文，执行情感分析与“黑天鹅关键词”检测，存入 MongoDB，并用 Streamlit 可视化。

## ✨ Features
- 多账号定时抓取（每 N 小时一次，速率受控）
- 情感分析（positive/neutral/negative）
- 黑天鹅关键词检测（war、nuclear、riot… 可配置）
- MongoDB 持久化 + 去重更新
- Streamlit 控制台：筛选领导人、查看黑天鹅预警、导出 CSV

## 📦 Tech Stack
Python · Tweepy · MongoDB · TextBlob · Streamlit · schedule

## 🗂 Project Structure
