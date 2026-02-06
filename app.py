import streamlit as st
import calendar
import datetime
import yfinance as yf  # 실시간 환율용
from amadeus import Client, ResponseError

# 1. Amadeus 보안 설정
try:
    amadeus = Client(
        client_id=st.secrets["AMADEUS_KEY"],
        client_secret=st.secrets["AMADEUS_SECRET"]
    )
except Exception as e:
    st.error("API Key 설정 오류: Streamlit Secrets를 확인해주세요.")
    st.stop()

# 2. 실시간 환율 가져오기 함수 (EUR -> KRW)
@st.cache_data(ttl=3600) # 1시간 동안 환율 결과 캐싱 (API 호출 낭비 방지)
def get_eur_krw_rate():
    try:
        # 야후 파이낸스에서 유로/원 환율 데이터 추출
        ticker = yf.Ticker("EURKRW=X")
        todays_data = ticker.history(period='1d')
        return todays_data['Close'].iloc[-1]
    except Exception as e:
        st.warning(f"실시간 환율을 가져오지 못했습니다. 기본값(1,500원)을 사용합니다. 오류: {e}")
        return 1500.0

# 3. API 호출 함수
def fetch_real_prices(origin, destination, departure_month):
    try:
        response = amadeus.shopping.flight_dates.get(
            origin=origin,
            destination=destination,
            departureDate=departure_month, 
            oneWay=False
        )
        return response.data
    except ResponseError as error:
        st.error(f"API 호출 오류: {error}")
        return []

# 4. UI 및 CSS (기존과 동일)
st.set_page_config(layout="wide")
st.markdown("""
<style>
    .block-container { padding-top: 1rem; }
    table { width: 100%; border-collapse: collapse; font-size: 0.85rem; table-layout: fixed; }
    th { background-color: #f8f9fa; padding: 10px; border: 1px solid #dee2e6; text-align: center; }
    td { border: 1px solid #dee2e6; height: 140px; vertical-align: top; padding: 5px; width: 14.28%; }
    .day-num { font-weight: bold; font-size: 1rem; margin-bottom: 5px; }
    .price-tag { font-size: 0.7rem; padding: 2px 4px; border-radius: 4px; margin-bottom: 2px; }
    .cheap { color: #1d4ed8; font-weight: bold; background-color: #eff6ff; border: 1px solid #bfdbfe; }
    .normal { color: #4b5563; background-color: #f9fafb; border: 1px solid #f3f4f6; }
    .exchange-info { font-size: 0.8rem; color: #666; margin-bottom: 1rem; }
</style>
""", unsafe_allow_html=True)

# 5. 사이드바 검색 조건
with st.sidebar:
    st.header("✈️ 실시간 검색 조건")
    origin_code = st.text_input("출발지 (IATA)", value="ICN").upper()
    dest_code = st.text_input("도착지 (IATA)", value="NRT").upper()
    
    st.subheader("📅 조회 기간")
    target_year = st.selectbox("연도", [2026, 2027], index=0)
    target_month = st.selectbox("월", list(range(1, 13)), index=6) # 7월 기본
    
    st.subheader("⏳ 체류 기간 (박)")
    min_stay = st.number_input("최소", 1, 30, 3)
    max_stay = st.number_input("최대", 1, 30, 7)
    
    passengers = st.number_input("인원수", 1, 9, 1)
    run = st.button("🚀 데이터 분석 시작")

# 6. 메인 화면 로직
st.title(f"📊 {target_year}년 {target_month}월 항공권 최저가")

# 실시간 환율 적용
current_rate = get_eur_krw_rate()
st.markdown(f"<div class='exchange-info'>ℹ️ 현재 실시간 환율: 1 EUR = <b>{current_rate:,.2f} KRW</b> (Yahoo Finance 기준)</div>", unsafe_allow_html=True)

if run:
    query_month = f"{target_year}-{target_month:02d}"
    
    with st.spinner(f"Amadeus 데이터 및 환율 계산 중..."):
        raw_data = fetch_real_prices(origin_code, dest_code, query_month)

    if not raw_data:
        st.warning("데이터가 없습니다. (IATA 코드나 날짜를 확인하세요)")
    else:
        price_data = {}
        all_prices = []

        for entry in raw_data:
            d_date = datetime.datetime.strptime(entry['departureDate'], '%Y-%m-%d')
            r_date = datetime.datetime.strptime(entry['returnDate'], '%Y-%m-%d')
            
            if d_date.year == target_year and d_date.month == target_month:
                day = d_date.day
                stay = (r_date - d_date).days
                # 실시간 환율 적용 가격 계산
                price = int(float(entry['price']['total']) * current_rate * passengers)
                
                if min_stay <= stay <= max_stay:
                    if day not in price_data:
                        price_data[day] = {"stays": {}}
                    if stay not in price_data[day]["stays"] or price < price_data[day]["stays"][stay]:
                        price_data[day]["stays"][stay] = price
                        all_prices.append(price)

        threshold = sorted(all_prices)[int(len(all_prices) * 0.2)] if all_prices else 0

        # 달력 렌더링
        cal = calendar.Calendar(firstweekday=6)
        month_days = cal.monthdayscalendar(target_year, target_month)
        week_names = ["일", "월", "화", "수", "목", "금", "토"]

        html = "<table><tr>" + "".join(f"<th>{w}</th>" for w in week_names) + "</tr>"
        for week in month_days:
            html += "<tr>"
            for day in week:
                if day == 0:
                    html += "<td></td>"
                    continue
                info = price_data.get(day, {"stays": {}})
                cell = f"<div class='day-num'>{day}</div>"
                sorted_stays = sorted(info["stays"].items())
                if not sorted_stays:
                    cell += "<div style='color:#ccc; font-size:0.7rem;'>-</div>"
                else:
                    for stay, price in sorted_stays:
                        is_cheap = "cheap" if price <= threshold else "normal"
                        cell += f"<div class='price-tag {is_cheap}'>{stay}박: {price:,}원</div>"
                html += f"<td>{cell}</td>"
            html += "</tr>"
        html += "</table>"
        
        st.markdown(html, unsafe_allow_html=True)
        st.success(f"분석 완료: 실시간 환율 {current_rate:,.1f}원이 적용되었습니다.")
