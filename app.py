import streamlit as st
import pandas as pd
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
import calendar
import math

# ----------------------------
# 기본 설정 (여백 최소화)
# ----------------------------
st.set_page_config(
    page_title="항공권 캘린더",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown(
    "<h3 style='margin-bottom:5px;'>✈️ 항공권 캘린더 시뮬레이터</h3>",
    unsafe_allow_html=True
)

# ----------------------------
# 사이드바 입력 UI
# ----------------------------
with st.sidebar:
    st.markdown("### 실행")
    run = st.button("▶ 시뮬레이션 실행", use_container_width=True)

    st.markdown("---")
    st.markdown("### 기본 조건")

    departure_city = st.text_input(
        "출발지",
        value="서울 (ICN)"
    )

    destination = st.text_input(
        "도착지",
        value="후쿠오카"
    )

    col_m1, col_m2 = st.columns(2)
    with col_m1:
        start_month = st.date_input(
            "출발 시작 월",
            value=date.today().replace(day=1)
        )
    with col_m2:
        month_range = st.selectbox(
            "출발 월 범위",
            options=[1, 2],
            index=1
        )

    col_s1, col_s2 = st.columns(2)
    with col_s1:
        min_stay = st.number_input(
            "최소 체류일",
            min_value=1,
            max_value=30,
            value=3
        )
    with col_s2:
        max_stay = st.number_input(
            "최대 체류일",
            min_value=1,
            max_value=30,
            value=7
        )

    st.markdown("### 경유 조건")
    direct = st.checkbox("직항", value=True)
    one_stop = st.checkbox("1회 경유")
    multi_stop = st.checkbox("2회 이상 경유")

    st.markdown("### 인원")
    col_p1, col_p2, col_p3 = st.columns(3)
    with col_p1:
        adults = st.number_input("성인", 1, 9, 1)
    with col_p2:
        children = st.number_input("어린이", 0, 9, 0)
    with col_p3:
        infants = st.number_input("유아", 0, 9, 0)

# ----------------------------
# 날짜 및 더미 가격 생성
# ----------------------------
def generate_departure_dates(start_date, months):
    end_date = start_date + relativedelta(months=months)
    dates = []
    d = start_date
    while d < end_date:
        dates.append(d)
        d += timedelta(days=1)
    return dates

def fake_price(dep_date, stay):
    # 임시 가격 로직 (요일/날짜 기반)
    base = dep_date.day * 1200 + stay * 5000
    weekend = 15000 if dep_date.weekday() >= 4 else 0
    return base + weekend

# ----------------------------
# 달력용 데이터 구조
# ----------------------------
def build_calendar_data(dep_dates, min_stay, max_stay):
    data = {}
    prices = []

    for d in dep_dates:
        stays = {}
        for stay in range(min_stay, max_stay + 1):
            price = fake_price(d, stay)
            stays[stay] = price
            prices.append((d.weekday(), price))
        data[d] = stays

    return data, prices

def get_thresholds(prices):
    weekday_prices = [p for w, p in prices if w <= 3]
    weekend_prices = [p for w, p in prices if w >= 4]

    def threshold(lst):
        if not lst:
            return math.inf
        lst_sorted = sorted(lst)
        return lst_sorted[int(len(lst_sorted) * 0.3)]

    return threshold(weekday_prices), threshold(weekend_prices)

# ----------------------------
# 결과 출력 (달력)
# ----------------------------
if run:
    dep_dates = generate_departure_dates(start_month.replace(day=1), month_range)
    calendar_data, prices = build_calendar_data(dep_dates, min_stay, max_stay)
    weekday_th, weekend_th = get_thresholds(prices)

    st.markdown("<hr style='margin:10px 0;'>", unsafe_allow_html=True)

    current_month = None
    week = []

    for d in dep_dates:
        if current_month != (d.year, d.month):
            if week:
                st.markdown(render_week(week), unsafe_allow_html=True)
                week = []
            st.markdown(
                f"<h4 style='margin-top:10px;'>{d.year}년 {d.month}월</h4>",
                unsafe_allow_html=True
            )
            current_month = (d.year, d.month)
            week = [""] * d.weekday()

        stays = calendar_data[d]
        cell = f"<b>{d.month}/{d.day} ({calendar.day_name[d.weekday()]})</b><br>"
        for stay, price in stays.items():
            if d.weekday() <= 3 and price <= weekday_th:
                color = "blue"
                weight = "bold"
            elif d.weekday() >= 4 and price <= weekend_th:
                color = "red"
                weight = "bold"
            else:
                color = "black"
                weight = "normal"

            cell += f"<span style='color:{color}; font-weight:{weight};'>{stay}일 : {price:,}원</span><br>"

        week.append(cell)

        if len(week) == 7:
            st.markdown(render_week(week), unsafe_allow_html=True)
            week = []

    if week:
        week += [""] * (7 - len(week))
        st.markdown(render_week(week), unsafe_allow_html=True)

# ----------------------------
# 주간 렌더링 함수
# ----------------------------
def render_week(cells):
    html = "<table style='width:100%; table-layout:fixed; border-collapse:collapse;'>"
    html += "<tr>"
    for c in cells:
        html += (
            "<td style='border:1px solid #ddd; vertical-align:top; "
            "padding:6px; font-size:12px; height:130px;'>"
            f"{c}</td>"
        )
    html += "</tr></table>"
    return html
