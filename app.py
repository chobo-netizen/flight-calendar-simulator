import streamlit as st
import calendar
import datetime
import random
import math

# --------------------
# 페이지 설정
# --------------------
st.set_page_config(layout="wide")

# --------------------
# CSS (여백 최소화)
# --------------------
st.markdown("""
<style>
.block-container {
    padding-top: 1rem;
    padding-bottom: 1rem;
}
h1 {
    font-size: 1.4rem;
    margin-bottom: 0.3rem;
}
h2 {
    font-size: 1.1rem;
}
table {
    font-size: 0.85rem;
}
</style>
""", unsafe_allow_html=True)

# --------------------
# 사이드바 입력 옵션
# --------------------
st.sidebar.header("✈️ 검색 조건")

origin = st.sidebar.text_input("출발지", value="서울")
destination = st.sidebar.text_input("도착지", value="도쿄")

passengers = st.sidebar.number_input(
    "인원수",
    min_value=1,
    max_value=9,
    value=1,
    step=1
)

direct_only = st.sidebar.checkbox("직항만 보기", value=True)

col_a, col_b = st.sidebar.columns(2)
with col_a:
    min_stay = st.number_input("최소 체류일", 1, 30, 3)
with col_b:
    max_stay = st.number_input("최대 체류일", 1, 30, 7)

run = st.sidebar.button("🧮 시뮬레이션 실행")

# --------------------
# 메인 타이틀
# --------------------
st.title("✈️ 항공권 캘린더 시뮬레이터")

# --------------------
# 시뮬레이션
# --------------------
if run:
    year = 2026
    month = 2

    st.subheader(f"{year}년 {month}월")

    cal = calendar.Calendar(firstweekday=0)
    month_days = cal.monthdayscalendar(year, month)

    # --------------------
    # 더미 가격 생성
    # --------------------
    price_data = {}

    for week in month_days:
        for day in week:
            if day == 0:
                continue

            weekday = datetime.date(year, month, day).weekday()
            base_price = random.randint(250000, 600000)

            # 직항 옵션 반영 (가산)
            if not direct_only:
                base_price -= 30000

            # 인원수 반영
            base_price *= passengers

            stays = {}
            for stay in range(min_stay, max_stay + 1):
                fluctuation = random.randint(-40000, 70000)
                stays[stay] = max(120000, base_price + fluctuation)

            price_data[day] = {
                "weekday": weekday,
                "stays": stays
            }

    # --------------------
    # 저렴한 30% 기준선
    # --------------------
    weekday_prices = []
    weekend_prices = []

    for info in price_data.values():
        min_price = min(info["stays"].values())
        if info["weekday"] <= 3:
            weekday_prices.append(min_price)
        else:
            weekend_prices.append(min_price)

    weekday_threshold = sorted(weekday_prices)[int(len(weekday_prices) * 0.3)] if weekday_prices else 0
    weekend_threshold = sorted(weekend_prices)[int(len(weekend_prices) * 0.3)] if weekend_prices else 0

    # --------------------
    # 달력 렌더링
    # --------------------
    week_names = ["월", "화", "수", "목", "금", "토", "일"]

    html = "<table border='1' style='border-collapse:collapse;width:100%'>"
    html += "<tr>" + "".join(f"<th>{w}</th>" for w in week_names) + "</tr>"

    for week in month_days:
        html += "<tr>"
        for day in week:
            if day == 0:
                html += "<td style='height:130px'></td>"
                continue

            info = price_data[day]
            cell = f"<b>{day}</b><br>"

            for stay, price in info["stays"].items():
                style = ""
                if info["weekday"] <= 3 and price <= weekday_threshold:
                    style = "color:blue;font-weight:bold;"
                elif info["weekday"] >= 4 and price <= weekend_threshold:
                    style = "color:red;font-weight:bold;"

                cell += f"<div style='{style}'>{stay}일 : {price:,}원</div>"

            html += f"<td valign='top' style='padding:4px'>{cell}</td>"
        html += "</tr>"

    html += "</table>"

    st.markdown(html, unsafe_allow_html=True)
