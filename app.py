import streamlit as st
import pandas as pd
from amadeus import Client, ResponseError
from datetime import datetime, timedelta
import calendar

# 1. Amadeus 클라이언트 설정
# 토큰 발급 및 관리를 Amadeus 라이브러리가 자동으로 처리합니다.
amadeus = Client(
    client_id='uMjiYwRybLsvIp0ABaDPUUcHVG7S9OIE',
    client_secret='kgbcorUxITyESvD5'
)

# --------------------
# 2. 데이터 수집 함수
# --------------------
def get_amadeus_prices(origin, destination, departure_date):
    """
    한 번의 호출로 해당 날짜로부터 시작되는 다양한 여정의 최저가를 가져옵니다.
    """
    try:
        # Flight Cheapest Date Search API 활용
        response = amadeus.shopping.flight_dates.get(
            origin=origin,
            destination=destination,
            departureDate=departure_date, # 예: '2026-07-01'
            oneWay=False
        )
        return response.data
    except ResponseError as error:
        st.error(f"API 오류: {error}")
        return None

# --------------------
# 3. UI 레이아웃
# --------------------
st.set_page_config(layout="wide", page_title="Amadeus Flight Analyzer")
st.title("📊 Amadeus 실시간 항공권 매트릭스")

with st.sidebar:
    st.header("✈️ 검색 조건")
    origin = st.text_input("출발지 (IATA)", value="ICN")
    dest = st.text_input("도착지 (IATA)", value="NRT")
    
    # Amadeus는 보통 현재로부터 1년 이내 데이터를 제공합니다.
    target_date = st.date_input("조회 시작일", value=datetime(2026, 7, 1))
    
    min_stay = st.slider("최소 체류일", 1, 15, 3)
    max_stay = st.slider("최대 체류일", 1, 15, 7)
    
    run = st.button("🚀 분석 시작 (API 1회 소모)")

# --------------------
# 4. 데이터 가공 및 출력
# --------------------
if run:
    with st.spinner("Amadeus 엔진에서 데이터를 분석 중입니다..."):
        data = get_amadeus_prices(origin, dest, target_date.strftime('%Y-%m-%d'))
        
    if data:
        # 1. 데이터 구조화
        processed_data = []
        for entry in data:
            dep_date = entry['departureDate']
            ret_date = entry['returnDate']
            price = float(entry['price']['total'])
            
            # 체류 기간 계산
            d1 = datetime.strptime(dep_date, '%Y-%m-%d')
            d2 = datetime.strptime(ret_date, '%Y-%m-%d')
            stay_duration = (d2 - d1).days
            
            # 사용자가 설정한 체류 기간 내의 데이터만 필터링
            if min_stay <= stay_duration <= max_stay:
                processed_data.append({
                    "출발일": dep_date,
                    "귀국일": ret_date,
                    "체류일": f"{stay_duration}일",
                    "가격(EUR)": price, # Amadeus 기본 통화는 보통 EUR입니다.
                    "원화환산": int(price * 1500) # 대략적인 환율 적용
                })
        
        df = pd.DataFrame(processed_data)
        
        if not df.empty:
            # 2. 결과 시각화 (피벗 테이블 활용)
            st.subheader(f"📅 {origin} ➡️ {dest} 체류일별 최저가 요약")
            
            # 행: 출발일, 열: 체류일로 구성된 매트릭스 생성
            matrix = df.pivot_table(
                index="출발일", 
                columns="체류일", 
                values="원화환산", 
                aggfunc='min'
            )
            
            # 보기 좋게 스타일링 (최저가 강조)
            st.dataframe(
                matrix.style.background_gradient(cmap="YlGnBu", axis=None)
                .format("{:,.0f}원")
            )
            
            # 3. 상세 목록
            with st.expander("상세 데이터 보기"):
                st.table(df.sort_values("원화환산").head(10))
        else:
            st.info("설정한 체류 기간 내에 검색된 데이터가 없습니다. 범위를 조절해 보세요.")
    else:
        st.error("데이터를 가져오지 못했습니다. IATA 코드를 확인해 주세요.")

st.divider()
st.caption("Amadeus Self-Service API를 사용하여 실시간 데이터를 조회합니다. (무료 2,000회/월)")
