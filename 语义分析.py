"""
增强的语义分析模块
使用多种模型进行情感分析和黑天鹅事件检测
"""

import torch
from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
from textblob import TextBlob
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import numpy as np
import re
from datetime import datetime

class EnhancedSentimentAnalyzer:
    def __init__(self):
        """初始化多个情感分析模型"""
        self.vader = SentimentIntensityAnalyzer()
        
        # 加载预训练的情感分析模型
        try:
            self.bert_analyzer = pipeline(
                "sentiment-analysis",
                model="cardiffnlp/twitter-roberta-base-sentiment-latest",
                return_all_scores=True
            )
        except:
            print("⚠️ BERT模型加载失败，使用基础模型")
            self.bert_analyzer = None
        
        # 黑天鹅关键词（分类）
        self.black_swan_keywords = {
            "政治危机": ["resign", "impeach", "coup", "revolution", "overthrow", "crisis", "scandal"],
            "军事冲突": ["war", "attack", "invasion", "missile", "bomb", "military", "conflict"],
            "核威胁": ["nuclear", "atomic", "warhead", "radiation", "reactor"],
            "经济危机": ["crash", "collapse", "default", "bankruptcy", "recession", "inflation"],
            "恐怖主义": ["terrorist", "attack", "bomb", "explosion", "assassination"],
            "自然灾害": ["earthquake", "tsunami", "hurricane", "flood", "disaster"],
            "健康危机": ["pandemic", "virus", "outbreak", "epidemic", "disease"]
        }
        
        # 紧急程度关键词
        self.urgency_keywords = {
            "极高": ["emergency", "urgent", "immediate", "breaking", "alert"],
            "高": ["serious", "critical", "important", "significant"],
            "中": ["concern", "issue", "problem", "matter"],
            "低": ["discuss", "consider", "review", "study"]
        }
    
    def analyze_sentiment_comprehensive(self, text):
        """综合情感分析"""
        results = {}
        
        # TextBlob分析
        blob = TextBlob(text)
        textblob_score = blob.sentiment.polarity
        
        # VADER分析
        vader_scores = self.vader.polarity_scores(text)
        
        # BERT分析（如果可用）
        bert_score = None
        if self.bert_analyzer:
            try:
                bert_result = self.bert_analyzer(text[:512])  # BERT有长度限制
                bert_score = bert_result[0]
            except:
                pass
        
        # 综合评分
        sentiment_score = self._calculate_composite_score(textblob_score, vader_scores, bert_score)
        sentiment_label = self._score_to_label(sentiment_score)
        
        return {
            "sentiment_score": sentiment_score,
            "sentiment_label": sentiment_label,
            "textblob_score": textblob_score,
            "vader_compound": vader_scores['compound'],
            "bert_score": bert_score,
            "confidence": self._calculate_confidence(textblob_score, vader_scores, bert_score)
        }
    
    def detect_black_swan_events(self, text):
        """检测黑天鹅事件"""
        text_lower = text.lower()
        detected_categories = []
        urgency_level = "低"
        risk_score = 0
        
        # 检测各类黑天鹅事件
        for category, keywords in self.black_swan_keywords.items():
            matches = [kw for kw in keywords if kw in text_lower]
            if matches:
                detected_categories.append({
                    "category": category,
                    "matched_keywords": matches,
                    "count": len(matches)
                })
                risk_score += len(matches) * 10
        
        # 检测紧急程度
        for level, keywords in self.urgency_keywords.items():
            if any(kw in text_lower for kw in keywords):
                urgency_level = level
                break
        
        # 计算最终风险评分
        if urgency_level == "极高":
            risk_score *= 2
        elif urgency_level == "高":
            risk_score *= 1.5
        
        is_black_swan = len(detected_categories) > 0 and risk_score > 15
        
        return {
            "is_black_swan": is_black_swan,
            "risk_score": min(risk_score, 100),  # 限制在100以内
            "urgency_level": urgency_level,
            "detected_categories": detected_categories,
            "alert_level": self._get_alert_level(risk_score)
        }
    
    def _calculate_composite_score(self, textblob_score, vader_scores, bert_score):
        """计算综合情感评分"""
        scores = [textblob_score, vader_scores['compound']]
        weights = [0.3, 0.4]
        
        if bert_score:
            # 转换BERT评分到-1到1的范围
            if bert_score[0]['label'] == 'LABEL_2':  # positive
                bert_normalized = bert_score[0]['score']
            elif bert_score[0]['label'] == 'LABEL_0':  # negative
                bert_normalized = -bert_score[0]['score']
            else:  # neutral
                bert_normalized = 0
            
            scores.append(bert_normalized)
            weights.append(0.3)
        
        # 加权平均
        composite_score = sum(s * w for s, w in zip(scores, weights)) / sum(weights)
        return composite_score
    
    def _score_to_label(self, score):
        """将评分转换为标签"""
        if score > 0.3:
            return "积极"
        elif score < -0.3:
            return "消极"
        else:
            return "中性"
    
    def _calculate_confidence(self, textblob_score, vader_scores, bert_score):
        """计算置信度"""
        scores = [abs(textblob_score), abs(vader_scores['compound'])]
        if bert_score:
            scores.append(max([s['score'] for s in bert_score]))
        
        return min(np.mean(scores), 1.0)
    
    def _get_alert_level(self, risk_score):
        """根据风险评分确定警报级别"""
        if risk_score >= 70:
            return "红色"
        elif risk_score >= 40:
            return "橙色"
        elif risk_score >= 20:
            return "黄色"
        else:
            return "绿色"

# 全局分析器实例
analyzer = EnhancedSentimentAnalyzer()

def analyze_tweet(text):
    """分析单条推文"""
    sentiment_result = analyzer.analyze_sentiment_comprehensive(text)
    black_swan_result = analyzer.detect_black_swan_events(text)
    
    return {
        **sentiment_result,
        **black_swan_result,
        "analyzed_at": datetime.now().isoformat()
    }