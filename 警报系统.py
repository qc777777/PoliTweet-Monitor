"""
报警系统模块
处理黑天鹅事件的实时报警和通知
"""

import smtplib
import json
import requests
from datetime import datetime, timedelta
from pymongo import MongoClient
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AlertSystem:
    def __init__(self, config_file="alert_config.json"):
        """初始化报警系统"""
        self.config = self._load_config(config_file)
        self.mongo_client = MongoClient("mongodb://localhost:27017/")
        self.db = self.mongo_client["twitter_monitor"]
        self.alerts_collection = self.db["alerts"]
        
    def _load_config(self, config_file):
        """加载配置文件"""
        default_config = {
            "email": {
                "enabled": False,
                "smtp_server": "smtp.gmail.com",
                "smtp_port": 587,
                "username": "",
                "password": "",
                "recipients": []
            },
            "webhook": {
                "enabled": False,
                "url": "",
                "headers": {}
            },
            "alert_thresholds": {
                "red": 70,
                "orange": 40,
                "yellow": 20
            },
            "cooldown_minutes": 30  # 同类型警报冷却时间
        }
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                # 合并默认配置
                for key, value in default_config.items():
                    if key not in config:
                        config[key] = value
                return config
        except FileNotFoundError:
            logger.warning(f"配置文件 {config_file} 不存在，使用默认配置")
            return default_config
    
    def check_and_send_alerts(self, tweet_data):
        """检查并发送警报"""
        if not tweet_data.get('is_black_swan', False):
            return False
        
        alert_level = tweet_data.get('alert_level', '绿色')
        risk_score = tweet_data.get('risk_score', 0)
        
        # 检查是否需要发送警报
        if not self._should_send_alert(tweet_data, alert_level):
            return False
        
        # 创建警报记录
        alert_record = self._create_alert_record(tweet_data, alert_level, risk_score)
        
        # 发送警报
        success = False
        if self.config['email']['enabled']:
            success |= self._send_email_alert(alert_record)
        
        if self.config['webhook']['enabled']:
            success |= self._send_webhook_alert(alert_record)
        
        # 保存警报记录
        if success:
            self.alerts_collection.insert_one(alert_record)
            logger.info(f"警报已发送: {alert_record['title']}")
        
        return success
    
    def _should_send_alert(self, tweet_data, alert_level):
        """判断是否应该发送警报"""
        risk_score = tweet_data.get('risk_score', 0)
        username = tweet_data.get('username', '')
        
        # 检查风险评分阈值
        thresholds = self.config['alert_thresholds']
        if alert_level == '红色' and risk_score < thresholds['red']:
            return False
        elif alert_level == '橙色' and risk_score < thresholds['orange']:
            return False
        elif alert_level == '黄色' and risk_score < thresholds['yellow']:
            return False
        
        # 检查冷却时间
        cooldown_minutes = self.config['cooldown_minutes']
        cutoff_time = datetime.now() - timedelta(minutes=cooldown_minutes)
        
        recent_alerts = self.alerts_collection.find({
            "username": username,
            "alert_level": alert_level,
            "created_at": {"$gte": cutoff_time.isoformat()}
        })
        
        if recent_alerts.count() > 0:
            logger.info(f"警报冷却中，跳过发送: {username} - {alert_level}")
            return False
        
        return True
    
    def _create_alert_record(self, tweet_data, alert_level, risk_score):
        """创建警报记录"""
        return {
            "id": f"alert_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{tweet_data.get('username', 'unknown')}",
            "title": f"🚨 {alert_level}警报: {tweet_data.get('username', '未知用户')}",
            "message": self._format_alert_message(tweet_data, alert_level, risk_score),
            "alert_level": alert_level,
            "risk_score": risk_score,
            "username": tweet_data.get('username', ''),
            "tweet_text": tweet_data.get('text', ''),
            "tweet_id": tweet_data.get('id', ''),
            "detected_categories": tweet_data.get('detected_categories', []),
            "urgency_level": tweet_data.get('urgency_level', '低'),
            "created_at": datetime.now().isoformat(),
            "status": "pending"
        }
    
    def _format_alert_message(self, tweet_data, alert_level, risk_score):
        """格式化警报消息"""
        username = tweet_data.get('username', '未知用户')
        text = tweet_data.get('text', '')[:200] + ('...' if len(tweet_data.get('text', '')) > 200 else '')
        categories = tweet_data.get('detected_categories', [])
        urgency = tweet_data.get('urgency_level', '低')
        
        message = f"""
🚨 黑天鹅事件警报 ({alert_level})

👤 用户: {username}
📊 风险评分: {risk_score}/100
⚡ 紧急程度: {urgency}
📝 推文内容: {text}

🏷️ 检测到的风险类别:
"""
        
        for cat in categories:
            message += f"• {cat['category']}: {', '.join(cat['matched_keywords'])}\n"
        
        message += f"\n⏰ 检测时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        return message
    
    def _send_email_alert(self, alert_record):
        """发送邮件警报"""
        try:
            email_config = self.config['email']
            
            msg = MIMEMultipart()
            msg['From'] = email_config['username']
            msg['To'] = ', '.join(email_config['recipients'])
            msg['Subject'] = alert_record['title']
            
            body = alert_record['message']
            msg.attach(MIMEText(body, 'plain', 'utf-8'))
            
            server = smtplib.SMTP(email_config['smtp_server'], email_config['smtp_port'])
            server.starttls()
            server.login(email_config['username'], email_config['password'])
            
            text = msg.as_string()
            server.sendmail(email_config['username'], email_config['recipients'], text)
            server.quit()
            
            logger.info("邮件警报发送成功")
            return True
            
        except Exception as e:
            logger.error(f"邮件发送失败: {e}")
            return False
    
    def _send_webhook_alert(self, alert_record):
        """发送Webhook警报"""
        try:
            webhook_config = self.config['webhook']
            
            payload = {
                "alert_level": alert_record['alert_level'],
                "title": alert_record['title'],
                "message": alert_record['message'],
                "risk_score": alert_record['risk_score'],
                "username": alert_record['username'],
                "timestamp": alert_record['created_at']
            }
            
            headers = webhook_config.get('headers', {})
            headers['Content-Type'] = 'application/json'
            
            response = requests.post(
                webhook_config['url'],
                json=payload,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info("Webhook警报发送成功")
                return True
            else:
                logger.error(f"Webhook发送失败: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Webhook发送失败: {e}")
            return False
    
    def get_recent_alerts(self, hours=24):
        """获取最近的警报"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        alerts = list(self.alerts_collection.find({
            "created_at": {"$gte": cutoff_time.isoformat()}
        }).sort("created_at", -1))
        
        return alerts
    
    def get_alert_statistics(self, days=7):
        """获取警报统计"""
        cutoff_time = datetime.now() - timedelta(days=days)
        
        pipeline = [
            {"$match": {"created_at": {"$gte": cutoff_time.isoformat()}}},
            {"$group": {
                "_id": "$alert_level",
                "count": {"$sum": 1}
            }}
        ]
        
        stats = list(self.alerts_collection.aggregate(pipeline))
        return {item['_id']: item['count'] for item in stats}

# 全局警报系统实例
alert_system = AlertSystem()

def send_alert_if_needed(tweet_data):
    """如果需要则发送警报"""
    return alert_system.check_and_send_alerts(tweet_data)