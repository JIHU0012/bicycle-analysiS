import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import os
import requests
from datetime import datetime

# 페이지 기본 설정 (가로로 넓게 사용)
st.set_page_config(page_title="서울시 공공자전거 분석 대시보드", layout="wide")

# 사이드바 스타일 설정 (선택 사항)
with st.sidebar:
    st.title("📊 분석 설정")
    st.info("데이터베이스와 연동된 실시간 대시보드입니다.")

# 1. 데이터베이스 파일 확인 및 경로 최적화
base_path = os.path.dirname(__file__)
db_path = os.path.join(base_path, '자전거 분석.db')

if not os.path.exists(db_path):
    st.error("🚨 앗! 데이터베이스 파일을 찾을 수 없어요.")
    st.info(f"찾으려는 경로: {db_path}\nGitHub에 파일을 꼭 포함해서 push 해주세요!")
    st.stop()

# 2. 데이터 불러오기 함수 (캐싱 적용)
@st.cache_data
def load_data():
    conn = sqlite3.connect(db_path)
    # 테이블명과 컬럼명을 실제 확인된 값에 맞춰 수정
    df_station = pd.read_sql_query("SELECT * FROM 대여소2", conn)
    df_usage = pd.read_sql_query("SELECT * FROM 이용정보2", conn)
    conn.close()
    return df_station, df_usage

# 데이터 불러오기 실행
df_station, df_usage = load_data()

# 메인 제목 및 설명
st.title("🚲 서울시 공공자전거(따릉이) 분석 대시보드")
st.markdown("공공데이터를 활용하여 자치구별 자전거 대여 시설 및 환경 기여도를 분석합니다.")
st.divider()

# ==========================================
# 1. 낙후시설 확인 (기본 유지하되 레이아웃 조정)
# ==========================================
st.subheader("1. 자치구별 노후 대여소 현황 (10년 이상)")

df_station['설치시기'] = pd.to_datetime(df_station['설치시기'], errors='coerce')
ten_years_ago = datetime.now().year - 10 

old_stations = df_station[df_station['설치시기'].dt.year <= ten_years_ago]
old_station_count = old_stations.groupby('자치구').size().reset_index(name='노후대여소_수')

fig1 = px.scatter(
    old_station_count, x='자치구', y='노후대여소_수', 
    size='노후대여소_수', color='노후대여소_수',
    color_continuous_scale='Reds',
    title="자치구별 노후 대여소 수 (버블 그래프)", size_max=30
)
fig1.update_layout(template="plotly_dark") # 대시보드 테마와 통일
st.plotly_chart(fig1, use_container_width=True)


# ==========================================
# 2. 자치구별 탄소 절감량 (그래프 간소화 및 레이아웃 분할)
# ==========================================
st.divider()
st.subheader("2. 자치구별 탄소 절감 현황")

# 데이터 가공
df_merged = pd.merge(df_usage, df_station, on='대여소번호')
df_merged['탄소량'] = pd.to_numeric(df_merged['탄소량'], errors='coerce').fillna(0)
carbon_sum = df_merged.groupby('자치구')['탄소량'].sum().reset_index(name='총_탄소절감량(kg)')

# 두 개의 컬럼으로 나누어 시각화
col1, col2 = st.columns([1.2, 1])

with col1:
    # 상위 10개 구만 추출하여 막대그래프 생성
    carbon_top10 = carbon_sum.sort_values(by='총_탄소절감량(kg)', ascending=False).head(10)
    fig_bar = px.bar(
        carbon_top10, x='자치구', y='총_탄소절감량(kg)',
        color='총_탄소절감량(kg)', 
        color_continuous_scale='Viridis',
        text_auto='.2s', # 막대 위에 수치 표시
        title="탄소 절감량 TOP 10 자치구"
    )
    fig_bar.update_layout(xaxis_title="자치구", yaxis_title="절감량(kg)")
    st.plotly_chart(fig_bar, use_container_width=True)

with col2:
    # 전체 비율을 보여주는 도넛 차트
    fig_pie = px.pie(
        carbon_sum, values='총_탄소절감량(kg)', names='자치구',
        hole=0.4, # 도넛 스타일
        title="전체 자치구별 탄소 절감 비율"
    )
    fig_pie.update_traces(textinfo='percent+label')
    fig_pie.update_layout(showlegend=False) # 너무 많으므로 범례 숨김
    st.plotly_chart(fig_pie, use_container_width=True)


# ==========================================
# 3. 자치구별 대여소 분포 지도 (디자인 개선)
# ==========================================
st.divider()
st.subheader("3. 자치구별 대여소 밀집도 지도")

# 데이터 가공
station_count = df_station.groupby('자치구').size().reset_index(name='대여소_수')
geojson_url = "https://raw.githubusercontent.com/southkorea/seoul-maps/master/kostat/2013/json/seoul_municipalities_geo_simple.json"
seoul_geojson = requests.get(geojson_url).json()

# 지도 시각화 개선
fig3 = px.choropleth(
    station_count, geojson=seoul_geojson,
    locations='자치구', featureidkey='properties.name', 
    color='대여소_수', color_continuous_scale='GnBu',
)

# 지도 위에 텍스트를 뿌리는 대신, 경계선을 명확히 하고 정보를 강화함
fig3.update_traces(
    marker_line_width=1.5, 
    marker_line_color='white', # 구 경계선을 흰색으로 굵게 하여 구분감 향상
    hovertemplate="<b>%{location}</b><br>대여소 개수: %{z}개<extra></extra>"
)

fig3.update_geos(fitbounds="locations", visible=False)
fig3.update_layout(
    margin={"r":0,"t":0,"l":0,"b":0},
    coloraxis_colorbar=dict(title="대여소 수")
)

st.plotly_chart(fig3, use_container_width=True)
st.caption("※ 지도 위를 클릭하거나 마우스를 올리면 자치구 이름을 확인할 수 있습니다.")