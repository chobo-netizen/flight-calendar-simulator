import streamlit as st
import calendar
import datetime
import yfinance as yf
from amadeus import Client, ResponseError

# 1. Amadeus 보안 설정 (Streamlit Secrets 사용)
try:
    amadeus = Client(
        client_id=st.secrets["AMADEUS_KEY"],
        client_secret=st.secrets["AMADEUS_SECRET"]
    )
except Exception as e:
    st.error("API Key 설정 오류: Streamlit Secrets를 확인해주세요.")
    st.stop()

# 2. 실시간 환율 가져오기 (EUR -> KRW)
@st.cache_data(ttl=3600)
def get_eur_krw_rate():
    try:
        # 야후 파이낸스에서 실시간 유로/원 환율 추출
        ticker = yf.Ticker("EURKRW=X")
        rate = ticker.history(period='1d')['Close'].iloc[-1]
        return rate
    except:
        return 1510.0  # 데이터 획득 실패 시 기본값

# 3. UI 스타일 설정 (CSS)
st.set_page_config(layout="wide", page_title="Direct Search Flight Calendar")
st.markdown("""
<style>
    .cal-table { width: 100%; border-collapse: collapse; table-layout: fixed; }
    .cal-th { background: #f8f9fa; padding: 12px; border: 1px solid #dee2e6; text-align: center; }
    .cal-td { border: 1px solid #dee2e6; height: 120px; vertical-align: top; padding: 10px; width: 14.28%; }
    .day-num { font-weight: bold; font-size: 1.1rem; margin-bottom: 8px; }
    .price-val { font-size: 0.85rem; padding: 5px; border-radius: 4px; text-align: center; line-height: 1.4; }
    .cheap-price { background-color: #eff6ff; color: #1d4ed8; font-weight: bold; border: 1px solid #bfdbfe; }
    .normal-price { background-color: #f9fafb; color: #4b5563; border: 1px solid #f3f4f6; }
    .empty-day { color: #d1d5db; font-size: 0.75rem; }
</style>
""", unsafe_allow_html=True)

# 4. 사이드바 검색 조건 설정
with st.sidebar:
    st.header("🔍 검색 필터")
    origin = st.text_input("출발지 (IATA)", value="ICN").upper()
    dest = st.text_input("도착지 (IATA)", value="NRT").upper()
    
    st.subheader("📅 조회 일정")
    target_year = st.selectbox("연도", [2026, 2027], index=0)
    target_month = st.selectbox("월", list(range(1, 13)), index=4) # 기본 5월
    
    st.subheader("⚙️ 옵션")
    is_non_stop = st.checkbox("✈️ 직항만 보기", value=True)
    passengers = st.number_input("인원수 (성인)", 1, 9, 1)
    
    st.divider()
    run = st.button("🚀 실시간 전수조사 시작", use_container_width=True)

# 5. 메인 화면 상단 정보
st.title(f"📊 {target_year}년 {target_month}월 항공권 최저가 리포트")
current_rate = get_eur_krw_rate()
st.write(f"ℹ️ **적용 환율:** 1 EUR = **{current_rate:,.2f} KRW** (Yahoo Finance 실시간 데이터)")

# 6. 메인 로직 실행
if run:
    # 해당 월의 일수 계산
    last_day = calendar.monthrange(target_year, target_month)[1]
    
    price_dict = {}
    all_prices = []
    
    # 진행 상황 표시
    progress_bar = st.progress(0)
    status_text = st.empty()

    # 1일부터 말일까지 실시간 API 호출 루프
    for day in range(1, last_day + 1):
        dep_date = f"{target_year}-{target_month:02d}-{day:02d}"
        status_text.text(f"📡 {dep_date} {'직항' if is_non_stop else '전체'} 가격 조회 중... ({day}/{last_day})")
        
        try:
            # 실시간 항공권 검색 API (Flight Offers Search)
            response = amadeus.shopping.flight_offers_search.get(
                originLocationCode=origin,
                destinationLocationCode=dest,
                departureDate=dep_date,
                adults=passengers,
                nonStop='true' if is_non_stop else 'false',
                max=1  # 가장 싼 표 1개만 신속하게 가져옴
            )
            
            if response.data:
                eur_price = float(response.data[0]['price']['total'])
                krw_price = int(eur_price * current_rate)
                price_dict[day] = krw_price
                all_prices.append(krw_price)
            
        except ResponseError as e:
            # API 오류나 데이터 부재 시 로그 없이 스킵
            pass
            
        progress_bar.progress(day / last_day)

    status_text.success(f"✅ {target_year}년 {target_month}월 전수조사가 완료되었습니다!")

    # 7. 달력 렌더링
    if not all_prices:
        st.error(f"조회된 항공권 데이터가 없습니다. {origin}→{dest} 노선의 직항 여부나 날짜를 확인해 주세요.")
    else:
        # 상위 20% 저렴한 가격 강조 기준값
        threshold = sorted(all_prices)[int(len(all_prices) * 0.2)] if all_prices else 0
        
        cal = calendar.Calendar(firstweekday=6) # 일요일 시작
        weeks = cal.monthdayscalendar(target_year, target_month)
        week_names = ["일", "월", "화", "수", "목", "금", "토"]

        # HTML 테이블 생성
        html = "<table class='cal-table'><tr>"
        for w in week_names:
            html += f"<th class='cal-th'>{w}</th>"
        html += "</tr>"

        for week in weeks:
            html += "<tr>"
            for day in week:
                if day == 0:
                    html += "<td class='cal-td'></td>"
                else:
                    price = price_dict.get(day)
                    price_html = ""
                    if price:
                        p_class = "cheap-price" if price <= threshold else "normal-price"
                        price_html = f"<div class='price-val {p_class}'>{price:,}원</div>"
                    else:
                        price_html = "<div class='empty-day'>데이터 없음</div>"
                    
                    html += f"<td class='cal-td'><div class='day-num'>{day}</div>{price_html}</td>"
            html += "</tr>"
        html += "</table>"
        
        st.markdown(html, unsafe_allow_html=True)
        st.caption("※ 위 가격은 실시간 최저가 기준이며, 실제 예약 시점에 따라 변동될 수 있습니다.")

else:
    st.info("사이드바에서 조건을 설정한 후 '조회 시작' 버튼을 눌러주세요. (약 20~30초 소요)")
