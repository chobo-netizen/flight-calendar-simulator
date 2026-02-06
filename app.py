import streamlit as st
import calendar
import datetime
import yfinance as yf
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

# 2. 실시간 환율 가져오기
@st.cache_data(ttl=3600)
def get_eur_krw_rate():
    try:
        ticker = yf.Ticker("EURKRW=X")
        return ticker.history(period='1d')['Close'].iloc[-1]
    except:
        return 1500.0

# 3. 실시간 항공권 조회 함수 (Flight Offers Search 사용)
def fetch_month_prices(origin, destination, year, month, min_stay, max_stay):
    price_data = {}
    all_prices = []
    
    # 해당 월의 마지막 날 계산
    last_day = calendar.monthrange(year, month)[1]
    
    # 진행 바 표시
    progress_bar = st.progress(0)
    status_text = st.empty()

    for day in range(1, last_day + 1):
        departure_date = f"{year}-{month:02d}-{day:02d}"
        status_text.text(f"🔍 {departure_date} 실시간 가격 조회 중...")
        
        try:
            # 실시간 API 호출 (이건 400 에러가 거의 안 납니다)
            response = amadeus.shopping.flight_offers_search.get(
                originLocationCode=origin,
                destinationLocationCode=destination,
                departureDate=departure_date,
                adults=1, # 기준 가격은 1인으로 조회
                max=3     # 가장 싼 거 3개만
            )
            
            if response.data:
                # 가장 저렴한 가격 추출
                cheapest_offer = response.data[0]
                eur_price = float(cheapest_offer['price']['total'])
                
                # 결과 저장
                if day not in price_data:
                    price_data[day] = {"stays": {}}
                
                # Flight Offers Search는 복귀일을 랜덤하게 주지 않으므로 
                # 여기서는 '출발일 기준 최저가'를 메인으로 표시합니다.
                price_data[day]["stays"]["최저"] = eur_price
                all_prices.append(eur_price)
                
        except ResponseError:
            pass # 데이터 없는 날은 건너뜀
            
        progress_bar.progress(day / last_day)
    
    status_text.text("✅ 분석 완료!")
    return price_data, all_prices

# 4. UI 설정
st.set_page_config(layout="wide")
st.title("✈️ 실시간 항공권 캘린더 (Direct Search)")

with st.sidebar:
    st.header("🔍 검색 조건")
    origin = st.text_input("출발지 (IATA)", value="ICN").upper()
    dest = st.text_input("도착지 (IATA)", value="NRT").upper()
    target_year = st.selectbox("연도", [2026, 2027], index=0)
    target_month = st.selectbox("월", list(range(1, 13)), index=4) # 5월 기본
    passengers = st.number_input("인원수", 1, 9, 1)
    run = st.button("🚀 실시간 데이터 분석 시작")

current_rate = get_eur_krw_rate()
st.info(f"ℹ️ 현재 환율: 1 EUR = {current_rate:,.2f} KRW")

if run:
    # 실시간 데이터 수집
    price_dict, all_prices = fetch_month_prices(origin, dest, target_year, target_month, 0, 0)
    
    if not all_prices:
        st.error("해당 노선/날짜에 조회 가능한 항공권이 없습니다. IATA 코드를 확인해주세요.")
    else:
        # 달력 그리기 로직 (위와 동일)
        cal = calendar.Calendar(firstweekday=6)
        weeks = cal.monthdayscalendar(target_year, target_month)
        
        threshold = sorted(all_prices)[int(len(all_prices) * 0.2)] if all_prices else 0
        
        html = "<table style='width:100%; border-collapse:collapse;'>"
        html += "<tr>" + "".join(f"<th style='border:1px solid #ddd; padding:10px;'>{w}</th>" for w in ["일","월","화","수","목","금","토"]) + "</tr>"
        
        for week in weeks:
            html += "<tr>"
            for day in week:
                if day == 0:
                    html += "<td style='border:1px solid #ddd; height:100px;'></td>"
                    continue
                
                info = price_dict.get(day, {"stays": {}})
                cell = f"<div style='font-weight:bold;'>{day}</div>"
                
                if "최저" in info["stays"]:
                    eur = info["stays"]["최저"]
                    krw = int(eur * current_rate * passengers)
                    color = "#1d4ed8" if eur <= threshold else "#4b5563"
                    cell += f"<div style='color:{color}; font-size:0.8rem; margin-top:5px;'>{krw:,}원</div>"
                else:
                    cell += "<div style='color:#ccc; font-size:0.7rem;'>-</div>"
                
                html += f"<td style='border:1px solid #ddd; height:100px; vertical-align:top; padding:5px;'>{cell}</td>"
            html += "</tr>"
        html += "</table>"
        st.markdown(html, unsafe_allow_html=True)
