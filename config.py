"""
配置文件
包含所有系统配置参数
"""

import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# Twitter API 配置
TWITTER_CONFIG = {
    "BEARER_TOKEN": os.getenv("TWITTER_BEARER_TOKEN", "AAAAAAAAAAAAAAAAAAAAACrP2gEAAAAAVDu7sEdgju4uVOIVb9g%2Fj0aESm8%3DgbNNQF20iLJ5LhwnW1tR3BUcO5mReTiCcNV70RYqNh5V5589Nc"),
    "API_KEY": os.getenv("TWITTER_API_KEY", ""),
    "API_SECRET": os.getenv("TWITTER_API_SECRET", ""),
    "ACCESS_TOKEN": os.getenv("TWITTER_ACCESS_TOKEN", ""),
    "ACCESS_TOKEN_SECRET": os.getenv("TWITTER_ACCESS_TOKEN_SECRET", "")
}

# MongoDB 配置
MONGODB_CONFIG = {
    "CONNECTION_STRING": os.getenv("MONGODB_URI", "mongodb://localhost:27017/"),
    "DATABASE_NAME": "twitter_monitor",
    "COLLECTION_NAME": "tweets"
}

# 抓取配置
FETCH_CONFIG = {
    "MAX_TWEETS_PER_PERSON": 10,
    "SLEEP_BETWEEN_USERS": 5,  # 秒
    "FETCH_INTERVAL_HOURS": 2,
    "MAX_RETRIES": 3
}

# 领导人账号配置
LEADER_ACCOUNTS = {
    "realDonaldTrump": {
        "name": "特朗普",
        "country": "美国",
        "position": "前总统",
        "priority": "high"
    },
    "POTUS": {
        "name": "拜登",
        "country": "美国", 
        "position": "总统",
        "priority": "high"
    },
    "KremlinRussia_E": {
        "name": "普京",
        "country": "俄罗斯",
        "position": "总统",
        "priority": "high"
    },
    "EmmanuelMacron": {
        "name": "马克龙",
        "country": "法国",
        "position": "总统",
        "priority": "medium"
    },
    "ZelenskyyUa": {
        "name": "泽连斯基",
        "country": "乌克兰",
        "position": "总统",
        "priority": "high"
    },
    "netanyahu": {
        "name": "内塔尼亚胡",
        "country": "以色列",
        "position": "总理",
        "priority": "medium"
    },
    "RishiSunak": {
        "name": "苏纳克",
        "country": "英国",
        "position": "前首相",
        "priority": "medium"
    }
}

# 黑天鹅事件关键词配置
BLACK_SWAN_KEYWORDS = {
    "政治危机": {
        "keywords": ["resign", "impeach", "coup", "revolution", "overthrow", "crisis", "scandal", "辞职", "弹劾", "政变"],
        "weight": 2.0
    },
    "军事冲突": {
        "keywords": ["war", "attack", "invasion", "missile", "bomb", "military", "conflict", "战争", "攻击", "入侵"],
        "weight": 2.5
    },
    "核威胁": {
        "keywords": ["nuclear", "atomic", "warhead", "radiation", "reactor", "核武器", "核威胁", "辐射"],
        "weight": 3.0
    },
    "经济危机": {
        "keywords": ["crash", "collapse", "default", "bankruptcy", "recession", "inflation", "崩盘", "违约", "衰退"],
        "weight": 1.5
    },
    "恐怖主义": {
        "keywords": ["terrorist", "attack", "bomb", "explosion", "assassination", "恐怖", "爆炸", "暗杀"],
        "weight": 2.0
    },
    "自然灾害": {
        "keywords": ["earthquake", "tsunami", "hurricane", "flood", "disaster", "地震", "海啸", "飓风"],
        "weight": 1.0
    }
}

# 情感分析配置
SENTIMENT_CONFIG = {
    "MODELS": {
        "BERT": "cardiffnlp/twitter-roberta-base-sentiment-latest",
        "VADER": True,
        "TEXTBLOB": True
    },
    "THRESHOLDS": {
        "POSITIVE": 0.3,
        "NEGATIVE": -0.3
    }
}

# 警报配置
ALERT_CONFIG = {
    "LEVELS": {
        "RED": {"threshold": 70, "color": "#FF0000"},
        "ORANGE": {"threshold": 40, "color": "#FFA500"},
        "YELLOW": {"threshold": 20, "color": "#FFFF00"},
        "GREEN": {"threshold": 0, "color": "#00FF00"}
    },
    "COOLDOWN_MINUTES": 30,
    "MAX_ALERTS_PER_HOUR": 10
}

# Streamlit 配置
STREAMLIT_CONFIG = {
    "PAGE_TITLE": "推特舆情监控",
    "PAGE_ICON": "🌍",
    "LAYOUT": "wide",
    "REFRESH_INTERVAL": 60  # 秒
}