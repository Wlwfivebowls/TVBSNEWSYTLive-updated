
import streamlit as st
import pandas as pd
import numpy as np
import altair as alt

# Google Sheet 的 CSV 連結
sheet_url = "https://docs.google.com/spreadsheets/d/1DIz9Cd5iSr1ssNkyYgvBshwKcxfkdraOYilXbXzLXhU/gviz/tq?tqx=out:csv"

@st.cache_data(ttl=300)
def load_data():
    df = pd.read_csv(sheet_url)

    # 清洗欄位名稱：去除前後空白與特殊符號
    df.columns = df.columns.str.strip().str.replace("　", "").str.replace("\n", "").str.replace("　", "")

    # 取得欄位名稱（前3欄：連結、頻道名稱、影片標題）
    id_cols = df.columns[:3]
    value_cols = df.columns[3:]

    # melt 成長格式
    df_melted = df.melt(id_vars=id_cols, value_vars=value_cols, var_name="時間", value_name="在線人數")

    # 清洗時間與人數欄位
    df_melted["時間"] = pd.to_datetime(df_melted["時間"], errors="coerce")
    df_melted["在線人數"] = pd.to_numeric(df_melted["在線人數"], errors="coerce")
    df_melted = df_melted.dropna(subset=["時間", "在線人數"])

    # 自動辨識頻道名稱欄位
    name_col = [col for col in id_cols if "頻道" in col or "名稱" in col]
    if not name_col:
        raise ValueError("找不到頻道名稱欄位")
    df_melted = df_melted.rename(columns={name_col[0]: "頻道名稱"})

    return df_melted

st.title("📊 YouTube 直播頻道在線人數分析（雲端自動更新）")

try:
    df = load_data()
except Exception as e:
    st.error(f"❌ 表格載入錯誤：{e}")
    st.stop()

channels = df["頻道名稱"].unique().tolist()
channels.sort()

選擇模式 = st.sidebar.radio("選擇檢視模式", ["單一頻道分析", "各頻道比較"])

if 選擇模式 == "單一頻道分析":
    selected_channel = st.sidebar.selectbox("請選擇頻道", channels)
    df = df[df["頻道名稱"] == selected_channel]

min_date, max_date = df["時間"].dt.date.min(), df["時間"].dt.date.max()
start_date = st.sidebar.date_input("開始日期", min_value=min_date, max_value=max_date, value=min_date)
end_date = st.sidebar.date_input("結束日期", min_value=min_date, max_value=max_date, value=max_date)

mask = (df["時間"].dt.date >= start_date) & (df["時間"].dt.date <= end_date)
df_filtered = df[mask].copy()
df_filtered["日期"] = df_filtered["時間"].dt.date
df_filtered["小時"] = df_filtered["時間"].dt.hour

grouped = df_filtered.groupby(["頻道名稱", "日期"])
stats = grouped["在線人數"].agg(
    每日平均="mean",
    每日加總="sum",
    午間平均=lambda x: x[(x.index.hour >= 11) & (x.index.hour < 14)].mean(),
    晚間平均=lambda x: x[(x.index.hour >= 19) & (x.index.hour < 22)].mean()
).reset_index()

均值 = stats.groupby("頻道名稱")[["每日平均", "午間平均", "晚間平均"]].mean().round().sort_values("每日平均", ascending=False)
均值.index.name = "頻道名稱"
st.subheader("📈 各頻道每日平均在線人數（排序）")
st.dataframe(均值.style.highlight_max(axis=0, color="gold").set_properties(**{"font-weight": "bold", "color": "black", "background-color": "#FFD700"}))

st.subheader("📅 每日在線人數統計表")
st.dataframe(stats.round(0), use_container_width=True)

if 選擇模式 == "各頻道比較":
    hourly_avg = df_filtered.groupby(["時間", "頻道名稱"])["在線人數"].mean().reset_index()
    chart = alt.Chart(hourly_avg).mark_line().encode(
        x="時間:T", y="在線人數:Q", color="頻道名稱:N", tooltip=["時間", "頻道名稱", "在線人數"]
    ).properties(width=700, height=400)
    st.altair_chart(chart, use_container_width=True)
