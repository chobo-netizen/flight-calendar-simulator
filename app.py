import streamlit as st
import calendar
import datetime
from amadeus import Client, ResponseError

# --------------------
# 1. Amadeus 설정 및 데이터 수집 함수
# --------------------
# 발급받으신 키를 여기에 넣었습니다.
amadeus = Client(
    client_id='uMjiYwRybLsvIp0ABaDPUUcHVG7S9OIE',
    client_secret='kgbcorUxITyESvD5'
)

def fetch_real_prices(origin, destination, departure_date):
    try:
        # Amadeus의 'Cheapest Date' API는 한 번 호출에 한 달 치 데이터를 묶어 주는 경우가 많아 효율적입니다.
        response = amadeus.shopping.flight_dates.get(
            origin=origin,
            destination=destination,
            departureDate=departure_date,
            oneWay=False
        )
        return response.data
    except ResponseError as error:
        st.error(f"API 호출 오류: {error}")
        return []

# --------------------
# 2. 페이지 설정 및 CSS
# --------------------
st.set_page_config(layout="wide")
st.markdown("""
<style>
.block-container { padding-top: 1rem; padding-bottom: 1rem; }
h1 { font-size: 1.4rem; margin-bottom: 0.3rem; }
table { font-size: 0.85rem; width: 100%; border-collapse: collapse; }
th { background-color: #f0f2f6; padding: 10px; }
td { border: 1px solid #ddd; height: 120px; vertical-align: top; padding: 5px; }
.price-tag { font-size: 0.75rem; margin-bottom: 2px; }
</style>
""", unsafe_allow_html=True)

# --------------------
# 3. 사이드바 (IATA 코드 입력 안내 필요)
# --------------------
st.sidebar.header("✈️ 실시간 검색 조건")
st.sidebar.info("💡 출발지와 도착지는 IATA 코드(예: ICN, NRT)를 입력하세요.")

origin_code = st.sidebar.text_input("출발지 (IATA)", value="ICN")
dest_code = st.sidebar.text_input("도착지 (IATA)", value="NRT")

# 인원수와 경유 조건은 Amadeus 필터에 맞게 확장 가능하지만, 
# 우선 가격 표시 로직에 집중합니다.
passengers = st.sidebar.number_input("인원수", 1, 9, 1)

col1, col2 = st.sidebar.columns(2)
with col1:
    min_stay = st.number_input("최소 체류", 1, 30, 3)
with col2:
    max_stay = st.number_input("최대 체류", 1, 30, 7)

run = st.sidebar.button("🚀 실시간 데이터 분석 실행")

# --------------------
# 4. 메인 분석 로직
# --------------------
st.title("✈️ Amadeus 실시간 항공권 캘린더")

if run:
    # 2026년 2월 기준 (사용자 날짜 선택 가능하게 변경 가능)
    year, month = 2026, 2
    query_date = f"{year}-{month:02d}-01"
    
    with st.spinner("Amadeus 서버에서 실시간 최저가를 불러오는 중..."):
        raw_data = fetch_real_prices(origin_code, dest_code, query_date)

    if not raw_data:
        st.warning("조회된 실시간 데이터가 없습니다. 날짜나 장소를 확인해주세요.")
    else:
        # API 데이터를 캘린더용 price_data 구조로 변환
        price_data = {}
        all_prices = []

        for entry in raw_data:
            d_date = datetime.datetime.strptime(entry['departureDate'], '%Y-%m-%d')
            r_date = datetime.datetime.strptime(entry['returnDate'], '%Y-%m-%d')
            
            if d_date.month != month: continue # 해당 월 데이터만 필터
            
            day = d_date.day
            stay = (r_date - d_date).days
            price = int(float(entry['price']['total']) * 1500 * passengers) # 환율 1500원 가정
            
            if min_stay <= stay <= max_stay:
                if day not in price_data:
                    price_data[day] = {"weekday": d_date.weekday(), "stays": {}}
                price_data[day]["stays"][stay] = price
                all_prices.append(price)

        # --------------------
        # 5. 달력 렌더링 (기존 HTML 로직 활용)
        # --------------------
        st.subheader(f"📅 {year}년 {month}월 실시간 리포트 ({origin_code} ➔ {dest_code})")
        
        # 하위 30% 저렴한 가격 기준점 계산
        threshold = sorted(all_prices)[int(len(all_prices) * 0.3)] if all_prices else 0

        cal = calendar.Calendar(firstweekday=6) # 일요일 시작
        month_days = cal.monthdayscalendar(year, month)
        week_names = ["일", "월", "화", "수", "목", "금", "토"]

        html = "<table>"
        html += "<tr>" + "".join(f"<th>{w}</th>" for w in week_names) + "</tr>"

        for week in month_days:
            html += "<tr>"
            for day in week:
                if day == 0:
                    html += "<td></td>"
                    continue

                info = price_data.get(day, {"stays": {}})
                weekday = datetime.date(year, month, day).weekday()
                
                cell = f"<b>{day}</b><br>"
                # 체류일별 가격 나열
                sorted_stays = sorted(info["stays"].items())
                for stay, price in sorted_stays:
                    style = "color: blue; font-weight: bold;" if price <= threshold else "color: #555;"
                    cell += f"<div class='price-tag' style='{style}'>{stay}일: {price:,}원</div>"

                html += f"<td>{cell}</td>"
            html += "</tr>"
        html += "</table>"
        
        st.markdown(html, unsafe_allow_html=True)
        st.success(f"분석 완료! 총 {len(raw_data)}개의 여정 조합을 확인했습니다.")
        
