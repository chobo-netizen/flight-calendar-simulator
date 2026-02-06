import streamlit as st
import asyncio
from playwright.async_api import async_playwright
import datetime
import calendar
import pandas as pd

# --- 스카이스캐너 크롤링 함수 (Playwright) ---
async def get_skyscanner_price(origin, dest, dep_date, ret_date):
    async with async_playwright() as p:
        # 브라우저 실행 (Streamlit Cloud 환경 설정)
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        url_dep = dep_date.strftime("%y%m%d")
        url_ret = ret_date.strftime("%y%m%d")
        url = f"https://www.skyscanner.co.kr/transport/flights/{origin}/{dest}/{url_dep}/{url_ret}/?adults=1&cabinclass=economy&ref=home"
        
        try:
            await page.goto(url, wait_until="networkidle", timeout=60000)
            # 가격 정보가 담긴 요소가 나타날 때까지 대기
            # 스카이스캐너의 가격 클래스명은 유동적이므로 '원' 텍스트가 포함된 요소를 찾습니다.
            price_selector = "span[class*='Price_mainPrice']"
            await page.wait_for_selector(price_selector, timeout=20000)
            
            price_text = await page.inner_text(price_selector)
            price = int(price_text.replace(",", "").replace("원", "").strip())
            await browser.close()
            return price
        except Exception as e:
            await browser.close()
            return None

# --- UI 레이아웃 ---
st.set_page_config(page_title="Skyscanner Real-time Scanner", layout="wide")
st.title("✈️ 스카이스캐너 실시간 연동 캘린더")

with st.sidebar:
    st.header("🔍 검색 설정")
    origin = st.text_input("출발지", value="ICN").upper()
    dest = st.text_input("도착지", value="NRT").upper()
    
    target_date = st.date_input("조회 시작일", datetime.date(2026, 5, 1))
    
    st.subheader("⏳ 체류 기간 (박)")
    min_stay = st.number_input("최소", 1, 10, 3)
    max_stay = st.number_input("최대", 1, 10, 5)
    
    run_btn = st.button("🚀 스캔 시작")

if run_btn:
    # 31일치를 다 돌리기엔 Streamlit Cloud 사양이 낮아 타임아웃 위험이 있습니다.
    # 우선 특정 날짜부터 일주일치 정도만 테스트해보는 것을 권장합니다.
    days_to_scan = 7 
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    results = []

    # 비동기 함수 실행을 위한 로직
    async def main_scan():
        for i in range(days_to_scan):
            dep_date = target_date + datetime.timedelta(days=i)
            day_data = {"date": dep_date, "prices": {}}
            
            for stay in range(min_stay, max_stay + 1):
                ret_date = dep_date + datetime.timedelta(days=stay)
                status_text.text(f"🔎 {dep_date} ({stay}박) 조회 중...")
                
                price = await get_skyscanner_price(origin, dest, dep_date, ret_date)
                if price:
                    day_data["prices"][stay] = price
                
                # 봇 차단 방지용 미세 대기
                await asyncio.sleep(1)
            
            results.append(day_data)
            progress_bar.progress((i + 1) / days_to_scan)
        
        status_text.success("조회 완료!")
        return results

    final_data = asyncio.run(main_scan())
    
    # 결과 출력 (간이 리스트 형태)
    for res in final_data:
        st.write(f"📅 **{res['date']} 출발**")
        cols = st.columns(len(res['prices']))
        for idx, (stay, price) in enumerate(res['prices'].items()):
            cols[idx].metric(f"{stay}박", f"{price:,}원")
