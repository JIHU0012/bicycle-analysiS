import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import os
import requests
from datetime import datetime

# 페이지 기본 설정
st.set_page_config(page_title="서울시 공공자전거 분석 대시보드", layout="wide")

# 1. 데이터베이스 파일 확인 (친절한 에러 메시지)
db_path = '자전거 분석.db'
if not os.path.exists(db_path):
    st.error("🚨 앗! 데이터베이스 파일을 찾을 수 없어요.")
    st.info(f"현재 폴더에 '{db_path}' 파일이 있는지 꼭 확인해주세요! (GitHub에 같이 업로드 하셨는지 확인해주세요)")
    st.stop() # 파일이 없으면 여기서 멈춥니다.

# 2. 데이터 불러오기 함수 (캐싱으로 빠르게!)
@st.cache_data
def load_data():
    conn = sqlite3.connect(db_path)
    
    # 💡 여기서 테이블 이름을 '대여소2', '이용정보2'로 올바르게 수정했습니다!
    df_station = pd.read_sql_query("SELECT * FROM 대여소2", conn)
    df_usage = pd.read_sql_query("SELECT * FROM 이용정보2", conn)
    
    conn.close()
    return df_station, df_usage

# 데이터 불러오기 실행
df_station, df_usage = load_data()

# 메인 제목
st.title("🚲 서울시 공공자전거(따릉이) 분석 대시보드")
st.markdown("공공데이터를 활용하여 자전거 대여소 및 이용 현황을 분석합니다.")
st.divider()

# ==========================================
# 1. 낙후시설 확인 (10년 이상 지난 대여소)
# ==========================================
st.subheader("1. 자치구별 낙후 대여소 현황 (설치 후 10년 이상)")

# 설치시기를 날짜형식으로 바꾸고 10년 전 계산
df_station['설치시기'] = pd.to_datetime(df_station['설치시기'], errors='coerce')
ten_years_ago = datetime.now().year - 10 

# 10년 이상 된 대여소 필터링 및 집계
old_stations = df_station[df_station['설치시기'].dt.year <= ten_years_ago]
old_station_count = old_stations.groupby('자치구').size().reset_index(name='낙후대여소_수')

# 버블 차트 그리기
fig1 = px.scatter(
    old_station_count, x='자치구', y='낙후대여소_수', 
    size='낙후대여소_수', color='낙후대여소_수',
    title="자치구별 낙후 대여소 수 (버블 그래프)", size_max=40
)
st.plotly_chart(fig1, use_container_width=True)


# ==========================================
# 2. 자치구별 탄소 절감량 (막대그래프)
# ==========================================
st.subheader("2. 자치구별 탄소 절감량 (이동거리 기준)")

# 이용정보2(대여소번호)와 대여소2(대여소번호PK) 합치기
df_merged = pd.merge(df_usage, df_station, left_on='대여소번호', right_on='대여소번호PK')
df_merged['탄소량'] = pd.to_numeric(df_merged['탄소량'], errors='coerce').fillna(0)

# 자치구별 탄소량 모두 더하기
carbon_sum = df_merged.groupby('자치구')['탄소량'].sum().reset_index(name='총_탄소절감량(kg)')

# 막대 그래프 그리기
fig2 = px.bar(
    carbon_sum, x='자치구', y='총_탄소절감량(kg)', 
    color='자치구', title="자치구별 총 탄소 절감량 (kg)"
)
st.plotly_chart(fig2, use_container_width=True)


# ==========================================
# 3. 자치구별 대여소 수 집계 (지도/코로플레스 맵)
# ==========================================
st.subheader("3. 자치구별 대여소 분포 지도")

# 자치구별 대여소 총 개수 세기
station_count = df_station.groupby('자치구').size().reset_index(name='대여소_수')

# 서울시 지도(GeoJSON) 데이터 인터넷에서 불러오기
geojson_url = "https://raw.githubusercontent.com/southkorea/seoul-maps/master/kostat/2013/json/seoul_municipalities_geo_simple.json"
seoul_geojson = requests.get(geojson_url).json()

# 지도 그리기
fig3 = px.choropleth(
    station_count, geojson=seoul_geojson,
    locations='자치구', featureidkey='properties.name', 
    color='대여소_수', color_continuous_scale='Blues',
    title="서울시 자치구별 대여소 밀집도"
)
fig3.update_geos(fitbounds="locations", visible=False)
fig3.update_layout(margin={"r":0,"t":40,"l":0,"b":0})

st.plotly_chart(fig3, use_container_width=True)
