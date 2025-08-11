import tweepy
from pymongo import MongoClient
from textblob import TextBlob
import schedule
import time
from datetime import datetime
import sys
import io
import os
from dotenv import load_dotenv
from 语义分析 import analyze_tweet
from 警报系统 import send_alert_if_needed

# 加载环境变量
load_dotenv()

# ---------- 配置区 ----------
# 从环境变量获取API密钥，如果没有则使用占位符
BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN")  

# 如果使用占位符，提示用户配置
if BEARER_TOKEN == "your_bearer_token_here":
    print("⚠️ 请在.env文件中配置TWITTER_BEARER_TOKEN")
    print("或者直接在此处替换BEARER_TOKEN变量")

MAX_TWEETS_PER_PERSON = 5
SLEEP_BETWEEN_USERS = 10  # 秒
FETCH_INTERVAL_HOURS = 2  # 每几小时抓一次

# 领导人账号（用户名 → 中文名称）
LEADER_ACCOUNTS = {
    "realDonaldTrump": "特朗普",
    "POTUS": "拜登",
    "KremlinRussia_E": "普京",
    "RishiSunak": "苏纳克",
    "EmmanuelMacron": "马克龙",
    "netanyahu": "内塔尼亚胡",
    "ZelenskyyUa": "泽连斯基"
}

# 黑天鹅关键词
BLACK_SWAN_KEYWORDS = [
    "resign", "nuclear", "assassinate", "collapse", "shutdown", "default",
    "emergency", "war", "coup", "strike", "riot", "dead", "爆炸", "危机"
]

# ---------- 初始化 ----------
# 输出防 emoji 报错
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 检查API密钥
if BEARER_TOKEN == "your_bearer_token_here":
    print("❌ 请先配置Twitter API密钥")
    sys.exit(1)

client_twitter = tweepy.Client(
    bearer_token=BEARER_TOKEN,
    wait_on_rate_limit=True
)

client_mongo = MongoClient("mongodb://localhost:27017/")
db = client_mongo["twitter_monitor"]
collection = db["tweets"]

# ⚠️ 缓存 user_id，避免多次请求 get_user()
USER_ID_CACHE = {}

# ---------- 工具函数 ----------

def analyze_sentiment(text):
    blob = TextBlob(text)
    polarity = blob.sentiment.polarity
    if polarity > 0.2:
        return "正面"
    elif polarity < -0.2:
        return "负面"
    else:
        return "中性"

def contains_black_swan_keywords(text):
    text_lower = text.lower()
    return any(kw.lower() in text_lower for kw in BLACK_SWAN_KEYWORDS)

def safe_print(msg):
    try:
        print(msg)
    except Exception:
        print(msg.encode("utf-8", errors="ignore").decode("utf-8"))

# ---------- 抓取单账号 ----------
def fetch_user_tweets(username):
    try:
        # 从缓存中获取 user_id，避免重复请求
        if username in USER_ID_CACHE:
            user_id = USER_ID_CACHE[username]
        else:
            user = client_twitter.get_user(username=username)
            user_id = user.data.id
            USER_ID_CACHE[username] = user_id

        tweets = client_twitter.get_users_tweets(
            id=user_id,
            max_results=MAX_TWEETS_PER_PERSON,
            tweet_fields=["created_at", "text", "lang"]
        )

        if tweets.data is None:
            safe_print(f"⚠️ {username} 无新推文。")
            return

        for tweet in tweets.data:
            # 使用增强的语义分析
            analysis_result = analyze_tweet(tweet.text)
            
            tweet_dict = {
                "id": tweet.id,
                "created_at": tweet.created_at.isoformat(),
                "text": tweet.text,
                "author_id": tweet.author_id,
                "username": username,
                # 保持向后兼容
                "sentiment": analysis_result['sentiment_label'],
                "black_swan": analysis_result['is_black_swan'],
                # 新增字段
                "sentiment_score": analysis_result['sentiment_score'],
                "confidence": analysis_result['confidence'],
                "risk_score": analysis_result['risk_score'],
                "urgency_level": analysis_result['urgency_level'],
                "alert_level": analysis_result['alert_level'],
                "detected_categories": analysis_result['detected_categories'],
                "analyzed_at": analysis_result['analyzed_at']
            }

            collection.update_one(
                {"id": tweet.id},
                {"$set": tweet_dict},
                upsert=True
            )

            # 检查是否需要发送警报
            if analysis_result['is_black_swan']:
                send_alert_if_needed(tweet_dict)

            # 显示状态
            if analysis_result['is_black_swan']:
                flag = f"🚨 {analysis_result['alert_level']}"
            else:
                flag = "✅"
            
            msg = f"{flag} [{tweet.created_at}] {username}: {tweet.text[:60]}..."
            safe_print(msg)

    except Exception as e:
        safe_print(f"❌ 错误（{username}）: {e}")

# ---------- 批量抓取 ----------
def fetch_all_leaders():
    safe_print(f"\n🕐 {datetime.utcnow().isoformat()} 正在抓取推文...\n")
    for username in LEADER_ACCOUNTS:
        fetch_user_tweets(username)
        safe_print(f"⏱ 已抓取 {username}，等待 {SLEEP_BETWEEN_USERS} 秒...\n")
        time.sleep(SLEEP_BETWEEN_USERS)

# ---------- 定时调度 ----------
if __name__ == "__main__":
    safe_print(f"📡 舆情监控启动，每 {FETCH_INTERVAL_HOURS} 小时执行一次...")
    fetch_all_leaders()  # 启动即执行一次
    schedule.every(FETCH_INTERVAL_HOURS).hours.do(fetch_all_leaders)

    while True:
        schedule.run_pending()
        time.sleep(10)
