import streamlit as st
import calendar
import datetime
import random
import math

# --------------------
# 기본 설정
# --------------------
st.set_page_config(layout="wide")

# --------------------
# 상단 여백 최소화 (CSS)
# --------------------
st.markdown("""
<style>
.block-container {
    padding-top: 1rem;
    padding-bottom: 1rem;
}
h1 {
    font-size: 1.4rem;
    margin-bottom: 0.2rem;
}
h2 {
    font-size: 1.1rem;
    margin-bottom: 0.2rem;
}
table {
    font-size: 0.85rem;
}
</style>
""", unsafe_allow_html=True)

# --------------------
# 입력 UI
# --------------------
st.title("✈️ 항공권 캘린더 시뮬레이터")

col1, col2, col3, col4 = st.columns([2, 2, 1, 1])

with col1:
    origin = st.text_input("출발지", value="서울")

with col2:
    destination = st.text_input("도착지", value="도쿄")

with col3:
    min_stay = st.number_input("최소 체류일", min_value=1, max_value=30, value=3)

with col4:
    max_stay = st.number_input("최대 체류일", min_value=1, max_value=30, value=7)

run = st.button("🧮 시뮬레이션 하기")

# --------------------
# 시뮬레이션 실행
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

            weekday = datetime.date(year, month, day).weekday()  # 0=월
            base_price = random.randint(300000, 700000)

            stays = {}
            for stay in range(min_stay, max_stay + 1):
                fluctuation = random.randint(-50000, 80000)
                stays[stay] = max(150000, base_price + fluctuation)

            price_data[day] = {
                "weekday": weekday,
                "stays": stays
            }

    # --------------------
    # 저렴한 30% 기준선 계산
    # --------------------
    weekday_prices = []
    weekend_prices = []

    for day, info in price_data.items():
        min_price = min(info["stays"].values())
        if info["weekday"] <= 3:  # 월~목
            weekday_prices.append(min_price)
        else:  # 금~일
            weekend_prices.append(min_price)

    weekday_threshold = sorted(weekday_prices)[max(0, math.floor(len(weekday_prices) * 0.3) - 1)] if weekday_prices else 0
    weekend_threshold = sorted(weekend_prices)[max(0, math.floor(len(weekend_prices) * 0.3) - 1)] if weekend_prices else 0

    # --------------------
    # 달력 출력
    # --------------------
    week_names = ["월", "화", "수", "목", "금", "토", "일"]

    html = "<table border='1' style='border-collapse:collapse; width:100%'>"
    html += "<tr>" + "".join([f"<th>{w}</th>" for w in week_names]) + "</tr>"

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
                if info["weekday"] >= 4 and price <= weekend_threshold:
                    style = "color:red;font-weight:bold;"

                cell += f"<div style='{style}'>{stay}일 : {price:,}원</div>"

            html += f"<td valign='top' style='padding:4px'>{cell}</td>"
        html += "</tr>"

    html += "</table>"

    st.markdown(html, unsafe_allow_html=True)
