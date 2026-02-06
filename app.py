import streamlit as st
import pandas as pd
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
import calendar

st.set_page_config(page_title="항공권 캘린더 시뮬레이터", layout="wide")

st.title("✈️ 항공권 캘린더 시뮬레이터")
st.caption("출발일 × 체류기간 조합을 한 번에 보기 위한 개인용 도구")

# ----------------------------
# 입력 영역
# ----------------------------
with st.sidebar:
    st.header("검색 조건")

    departure_city = st.text_input(
        "출발지",
        value="서울 (ICN)",
        disabled=True
    )

    destination = st.text_input(
        "도착지 (한글 / 영문 / IATA)",
        value="후쿠오카"
    )

    col1, col2 = st.columns(2)
    with col1:
        start_month = st.date_input(
            "출발 시작 월",
            value=date.today().replace(day=1)
        )
    with col2:
        month_range = st.selectbox(
            "출발 월 범위",
            options=[1, 2],
            index=1
        )

    min_stay = st.number_input("최소 체류일", min_value=1, max_value=30, value=3)
    max_stay = st.number_input("최대 체류일", min_value=1, max_value=30, value=7)

    st.subheader("경유 조건")
    direct = st.checkbox("직항", value=True)
    one_stop = st.checkbox("1회 경유")
    multi_stop = st.checkbox("2회 이상 경유")

    st.subheader("인원")
    adults = st.number_input("성인", min_value=1, max_value=9, value=1)
    children = st.number_input("어린이", min_value=0, max_value=9, value=0)
    infants = st.number_input("유아", min_value=0, max_value=9, value=0)

    run = st.button("시뮬레이션 실행")

# ----------------------------
# 날짜 계산 로직
# ----------------------------
def generate_departure_dates(start_date, months):
    end_date = start_date + relativedelta(months=months)
    dates = []
    d = start_date
    while d < end_date:
        dates.append(d)
        d += timedelta(days=1)
    return dates

def generate_results(departure_dates, min_stay, max_stay):
    rows = []
    for dep in departure_dates:
        for stay in range(min_stay, max_stay + 1):
            ret = dep + timedelta(days=stay)
            rows.append({
                "출발일": dep,
                "요일": calendar.day_name[dep.weekday()],
                "체류일": stay,
                "귀국일": ret,
                "왕복가격(가상)": dep.day * 1000 + stay * 5000  # 임시값
            })
    return pd.DataFrame(rows)

# ----------------------------
# 실행 영역
# ----------------------------
if run:
    st.subheader("📊 시뮬레이션 결과")

    dep_dates = generate_departure_dates(start_month.replace(day=1), month_range)
    df = generate_results(dep_dates, min_stay, max_stay)

    df = df.sort_values("왕복가격(가상)")

    st.dataframe(df, use_container_width=True)

    csv = df.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "CSV 다운로드",
        csv,
        file_name="flight_simulation.csv",
        mime="text/csv"
    )
