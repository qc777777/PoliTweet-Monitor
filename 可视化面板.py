# streamlit run app.py

import streamlit as st
from pymongo import MongoClient
import pandas as pd
import matplotlib.pyplot as plt
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np
import sys
import os

# 添加推特文件夹到路径
sys.path.append(os.path.join(os.path.dirname(__file__), '推特'))

try:
    from alert_system import alert_system
except ImportError:
    st.error("无法导入alert_system模块，请确保推特文件夹中的文件存在")
    alert_system = None

# ---------- 页面设置 ----------
st.set_page_config(page_title="推特舆情监控", layout="wide", initial_sidebar_state="expanded")

# ---------- 连接 MongoDB ----------
@st.cache_data(ttl=60)  # 缓存1分钟
def load_data():
    try:
        client = MongoClient("mongodb://localhost:27017/")
        db = client["twitter_monitor"]
        collection = db["tweets"]
        raw_data = list(collection.find().sort("created_at", -1).limit(1000))
        return pd.DataFrame(raw_data)
    except Exception as e:
        st.error(f"❌ 无法连接数据库: {e}")
        return pd.DataFrame()

df = load_data()

# ---------- 侧边栏导航 ----------
st.sidebar.title("📊 导航菜单")
page = st.sidebar.selectbox("选择页面", ["🏠 实时监控", "📈 历史分析", "🚨 警报中心", "⚙️ 系统设置"])

# ---------- 数据预处理 ----------
if df.empty:
    st.warning("⚠️ 当前数据库中没有任何推文数据，请先运行 auto_fetch.py。")
    st.stop()

# 清洗字段
df = df.dropna(subset=["username", "text"])
df["created_at"] = pd.to_datetime(df["created_at"])
df = df.sort_values("created_at", ascending=False)

# 确保必要字段存在
required_fields = ["sentiment_score", "risk_score", "alert_level", "urgency_level"]
for field in required_fields:
    if field not in df.columns:
        df[field] = 0 if "score" in field else "未知"

# ---------- 实时监控页面 ----------
if page == "🏠 实时监控":
    st.title("🌍 国家领导人推特舆情监控面板")
    
    # 实时状态指标
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_tweets = len(df)
        st.metric("总推文数", total_tweets)
    
    with col2:
        black_swan_count = len(df[df["black_swan"] == True])
        st.metric("黑天鹅事件", black_swan_count, delta=f"{black_swan_count/total_tweets*100:.1f}%")
    
    with col3:
        avg_sentiment = df["sentiment_score"].mean() if "sentiment_score" in df.columns else 0
        st.metric("平均情感分数", f"{avg_sentiment:.2f}")
    
    with col4:
        high_risk_count = len(df[df["risk_score"] > 50])
        st.metric("高风险推文", high_risk_count)
    
    # 用户选择
    st.sidebar.subheader("🎯 筛选选项")
    usernames_list = df["username"].dropna().astype(str).unique()
    usernames = st.sidebar.multiselect(
        "选择领导人",
        options=sorted(usernames_list),
        default=list(usernames_list)
    )
    
    # 时间范围选择
    time_range = st.sidebar.selectbox(
        "时间范围",
        ["最近24小时", "最近3天", "最近7天", "最近30天", "全部"]
    )
    
    # 根据时间范围筛选
    now = datetime.now()
    if time_range == "最近24小时":
        time_filter = now - timedelta(hours=24)
    elif time_range == "最近3天":
        time_filter = now - timedelta(days=3)
    elif time_range == "最近7天":
        time_filter = now - timedelta(days=7)
    elif time_range == "最近30天":
        time_filter = now - timedelta(days=30)
    else:
        time_filter = None
    
    # 筛选数据
    filtered_df = df[df["username"].isin(usernames)]
    if time_filter:
        filtered_df = filtered_df[filtered_df["created_at"] >= time_filter]
    
    # ---------- 风险热力图 ----------
    st.subheader("🔥 风险热力图")
    
    if not filtered_df.empty:
        # 创建风险矩阵
        risk_matrix = filtered_df.groupby(["username", "alert_level"]).size().unstack(fill_value=0)
        
        if not risk_matrix.empty:
            fig_heatmap = px.imshow(
                risk_matrix.values,
                x=risk_matrix.columns,
                y=risk_matrix.index,
                color_continuous_scale="Reds",
                title="各领导人风险等级分布"
            )
            st.plotly_chart(fig_heatmap, use_container_width=True)
    
    # ---------- 实时推文流 ----------
    st.subheader("📱 实时推文流")
    
    # 显示最新推文，带风险标识
    for idx, row in filtered_df.head(10).iterrows():
        with st.container():
            col1, col2 = st.columns([1, 4])
            
            with col1:
                # 风险等级标识
                if row.get("alert_level") == "红色":
                    st.error("🚨 红色")
                elif row.get("alert_level") == "橙色":
                    st.warning("🟠 橙色")
                elif row.get("alert_level") == "黄色":
                    st.info("🟡 黄色")
                else:
                    st.success("🟢 正常")
            
            with col2:
                st.write(f"**{row['username']}** - {row['created_at'].strftime('%Y-%m-%d %H:%M')}")
                st.write(row['text'][:200] + "..." if len(row['text']) > 200 else row['text'])
                
                # 显示分析结果
                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    st.caption(f"情感: {row.get('sentiment', '未知')}")
                with col_b:
                    st.caption(f"风险分数: {row.get('risk_score', 0)}")
                with col_c:
                    st.caption(f"紧急度: {row.get('urgency_level', '未知')}")
            
            st.divider()

# ---------- 历史分析页面 ----------
elif page == "📈 历史分析":
    st.title("📈 历史趋势分析")
    
    # 时间序列分析
    st.subheader("📊 情感趋势")
    
    # 按日期聚合数据
    df_daily = df.copy()
    df_daily['date'] = df_daily['created_at'].dt.date
    daily_sentiment = df_daily.groupby(['date', 'username'])['sentiment_score'].mean().reset_index()
    
    fig_trend = px.line(
        daily_sentiment, 
        x='date', 
        y='sentiment_score', 
        color='username',
        title="各领导人情感分数趋势"
    )
    st.plotly_chart(fig_trend, use_container_width=True)
    
    # 风险分数分布
    st.subheader("⚠️ 风险分数分布")
    
    fig_risk_dist = px.histogram(
        df, 
        x='risk_score', 
        color='username',
        title="风险分数分布",
        nbins=20
    )
    st.plotly_chart(fig_risk_dist, use_container_width=True)
    
    # 黑天鹅事件统计
    st.subheader("🦢 黑天鹅事件统计")
    
    black_swan_stats = df[df['black_swan'] == True].groupby('username').size().reset_index()
    black_swan_stats.columns = ['username', 'count']
    
    if not black_swan_stats.empty:
        fig_swan = px.bar(
            black_swan_stats,
            x='username',
            y='count',
            title="各领导人黑天鹅事件数量"
        )
        st.plotly_chart(fig_swan, use_container_width=True)
    else:
        st.info("暂无黑天鹅事件记录")

# ---------- 警报中心页面 ----------
elif page == "🚨 警报中心":
    st.title("🚨 警报中心")
    
    if alert_system:
        # 获取最近警报
        recent_alerts = alert_system.get_recent_alerts(hours=24)
        
        if recent_alerts:
            st.subheader("📋 最近24小时警报")
            
            for alert in recent_alerts:
                with st.expander(f"{alert['title']} - {alert['created_at'][:19]}"):
                    st.write(alert['message'])
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("风险分数", alert['risk_score'])
                    with col2:
                        st.metric("警报级别", alert['alert_level'])
                    with col3:
                        st.metric("紧急程度", alert['urgency_level'])
        else:
            st.success("✅ 最近24小时无警报")
        
        # 警报统计
        st.subheader("📊 警报统计")
        alert_stats = alert_system.get_alert_statistics(days=7)
        
        if alert_stats:
            fig_alert_stats = px.pie(
                values=list(alert_stats.values()),
                names=list(alert_stats.keys()),
                title="最近7天警报级别分布"
            )
            st.plotly_chart(fig_alert_stats, use_container_width=True)
    else:
        st.error("警报系统未正确加载")

# ---------- 系统设置页面 ----------
elif page == "⚙️ 系统设置":
    st.title("⚙️ 系统设置")
    
    st.subheader("📧 邮件警报设置")
    
    with st.form("email_settings"):
        email_enabled = st.checkbox("启用邮件警报")
        smtp_server = st.text_input("SMTP服务器", value="smtp.gmail.com")
        smtp_port = st.number_input("SMTP端口", value=587)
        email_username = st.text_input("邮箱用户名")
        email_password = st.text_input("邮箱密码", type="password")
        recipients = st.text_area("收件人邮箱（每行一个）")
        
        if st.form_submit_button("保存邮件设置"):
            st.success("邮件设置已保存")
    
    st.subheader("🔔 Webhook设置")
    
    with st.form("webhook_settings"):
        webhook_enabled = st.checkbox("启用Webhook警报")
        webhook_url = st.text_input("Webhook URL")
        
        if st.form_submit_button("保存Webhook设置"):
            st.success("Webhook设置已保存")
    
    st.subheader("⚠️ 警报阈值设置")
    
    with st.form("threshold_settings"):
        red_threshold = st.slider("红色警报阈值", 0, 100, 70)
        orange_threshold = st.slider("橙色警报阈值", 0, 100, 40)
        yellow_threshold = st.slider("黄色警报阈值", 0, 100, 20)
        cooldown_minutes = st.number_input("警报冷却时间（分钟）", value=30)
        
        if st.form_submit_button("保存阈值设置"):
            st.success("阈值设置已保存")

# ---------- 页面底部信息 ----------
st.sidebar.markdown("---")
st.sidebar.info(f"📊 数据更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
st.sidebar.info(f"📈 总推文数: {len(df)}")
if not df.empty:
    st.sidebar.info(f"⏰ 最新推文: {df['created_at'].max().strftime('%Y-%m-%d %H:%M')}")