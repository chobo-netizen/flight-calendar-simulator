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

# 2. 실시간 환율 (EUR -> KRW)
@st.cache_data(ttl=3600)
def get_eur_krw_rate():
    try:
        ticker = yf.Ticker("EURKRW=X")
        return ticker.history(period='1d')['Close'].iloc[-1]
    except:
        return 1510.0

# 3. UI 스타일 (다중 가격 표시용)
st.set_page_config(layout="wide", page_title="Advanced Flight Calendar")
st.markdown("""
<style>
    .cal-table { width: 100%; border-collapse: collapse; table-layout: fixed; }
    .cal-th { background: #f8f9fa; padding: 10px; border: 1px solid #dee2e6; }
    .cal-td { border: 1px solid #dee2e6; height: 160px; vertical-align: top; padding: 5px; width: 14.28%; }
    .day-num { font-weight: bold; font-size: 1.1rem; margin-bottom: 5px; border-bottom: 1px solid #eee; }
    .price-item { font-size: 0.75rem; padding: 2px 4px; border-radius: 3px; margin-bottom: 2px; display: flex; justify-content: space-between; }
    .cheap { background-color: #e1effe; color: #1e429f; font-weight: bold; }
    .normal { background-color: #f3f4f6; color: #374151; }
</style>
""", unsafe_allow_html=True)

# 4. 사이드바 설정
with st.sidebar:
    st.header("🔍 상세 검색")
    origin = st.text_input("출발지 (IATA)", value="ICN").upper()
    dest = st.text_input("도착지 (IATA)", value="NRT").upper()
    
    target_year = st.selectbox("연도", [2026, 2027], index=0)
    target_month = st.selectbox("월", list(range(1, 13)), index=4) 
    
    st.subheader("⏳ 체류 기간 설정")
    min_stay = st.number_input("최소 체류 (박)", 1, 30, 3)
    max_stay = st.number_input("최대 체류 (박)", 1, 30, 5)
    
    st.subheader("⚙️ 필터")
    is_non_stop = st.checkbox("✈️ 직항만 보기", value=True)
    passengers = st.number_input("인원수", 1, 9, 1)
    
    run = st.button("🚀 전수조사 시작 (호출 소모 주의)", use_container_width=True)

# 5. 메인 로직
st.title(f"📊 {target_year}년 {target_month}월 항공권 가격 분석")
current_rate = get_eur_krw_rate()
st.info(f"ℹ️ 환율: 1 EUR = {current_rate:,.2f} KRW")

if run:
    if min_stay > max_stay:
        st.error("최소 체류일이 최대 체류일보다 클 수 없습니다.")
        st.stop()

    last_day = calendar.monthrange(target_year, target_month)[1]
    price_data = {} # { day: { stay_count: price } }
    all_prices = []
    
    # 총 호출 횟수 계산
    total_calls = last_day * (max_stay - min_stay + 1)
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    call_count = 0
    for day in range(1, last_day + 1):
        price_data[day] = {}
        dep_date = datetime.date(target_year, target_month, day)
        
        # 체류 기간별로 루프
        for stay in range(min_stay, max_stay + 1):
            ret_date = dep_date + datetime.timedelta(days=stay)
            call_count += 1
            status_text.text(f"📡 조회 중: {dep_date} ({stay}박) - [{call_count}/{total_calls}]")
            
            try:
                response = amadeus.shopping.flight_offers_search.get(
                    originLocationCode=origin,
                    destinationLocationCode=dest,
                    departureDate=dep_date.strftime('%Y-%m-%d'),
                    returnDate=ret_date.strftime('%Y-%m-%d'), # 귀국일 명시로 왕복 검색
                    adults=passengers,
                    nonStop='true' if is_non_stop else 'false',
                    max=1
                )
                
                if response.data:
                    price = int(float(response.data[0]['price']['total']) * current_rate)
                    price_data[day][stay] = price
                    all_prices.append(price)
            except:
                pass
            
            progress_bar.progress(call_count / total_calls)

    status_text.success("✅ 조회가 완료되었습니다!")

    # 6. 달력 그리기
    threshold = sorted(all_prices)[int(len(all_prices) * 0.2)] if all_prices else 0
    
    cal = calendar.Calendar(firstweekday=6)
    weeks = cal.monthdayscalendar(target_year, target_month)
    
    html = "<table class='cal-table'><tr>"
    for w in ["일","월","화","수","목","금","토"]:
        html += f"<th class='cal-th'>{w}</th>"
    html += "</tr>"

    for week in weeks:
        html += "<tr>"
        for day in week:
            if day == 0:
                html += "<td class='cal-td'></td>"
                continue
            
            day_prices = price_data.get(day, {})
            cell = f"<div class='day-num'>{day}</div>"
            
            if not day_prices:
                cell += "<div style='color:#ccc; font-size:0.7rem;'>데이터 없음</div>"
            else:
                # 체류일 순서대로 정렬해서 표시
                for stay in sorted(day_prices.keys()):
                    p = day_prices[stay]
                    p_class = "cheap" if p <= threshold else "normal"
                    cell += f"<div class='price-item {p_class}'><span>{stay}박</span> <span>{p:,}원</span></div>"
            
            html += f"<td class='cal-td'>{cell}</td>"
        html += "</tr>"
    html += "</table>"
    st.markdown(html, unsafe_allow_html=True)
