import streamlit as st
import asyncio
import os
import subprocess
import datetime
import pandas as pd
from playwright.async_api import async_playwright

# --- 1. 브라우저 자동 설치 섹션 ---
@st.cache_resource
def install_playwright_browsers():
    try:
        # 시스템 권한이 필요한 install-deps는 제외하고 브라우저만 설치
        subprocess.run(["playwright", "install", "chromium"], check=True)
    except Exception as e:
        st.error(f"브라우저 설치 중 오류 발생: {e}")

install_playwright_browsers()

# --- 2. 스카이스캐너 크롤링 로직 ---
async def get_skyscanner_price(origin, dest, dep_date, ret_date):
    async with async_playwright() as p:
        try:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            
            url_dep = dep_date.strftime("%y%m%d")
            url_ret = ret_date.strftime("%y%m%d")
            url = f"https://www.skyscanner.co.kr/transport/flights/{origin}/{dest}/{url_dep}/{url_ret}/?adults=1&cabinclass=economy&ref=home"
            
            await page.goto(url, wait_until="networkidle", timeout=60000)
            
            # 스카이스캐너 가격 태그 (최신 선택자로 업데이트 시도)
            price_selector = "span[class*='Price_mainPrice']"
            await page.wait_for_selector(price_selector, timeout=20000)
            
            price_text = await page.inner_text(price_selector)
            price = int(price_text.replace(",", "").replace("원", "").strip())
            
            await browser.close()
            return price
        except Exception as e:
            # 에러 발생 시 로그 확인용 (사용자 화면에는 안 보임)
            print(f"Error fetching {dep_date}: {e}")
            if 'browser' in locals():
                await browser.close()
            return None

# --- 3. Streamlit UI 구성 ---
st.set_page_config(page_title="항공권 가격 시뮬레이터", layout="wide")
st.title("✈️ 실시간 항공권 가격 캘린더")

with st.sidebar:
    st.header("⚙️ 검색 옵션")
    origin = st.text_input("출발지 (공항코드)", value="ICN").upper()
    dest = st.text_input("도착지 (공항코드)", value="NRT").upper()
    start_date = st.date_input("조회 시작일", datetime.date(2026, 5, 1))
    
    st.divider()
    st.subheader("⏳ 체류 기간 (박)")
    min_stay = st.number_input("최소 숙박", 1, 14, 3)
    max_stay = st.number_input("최대 숙박", 1, 14, 5)
    
    st.divider()
    scan_days = st.slider("조회할 일수", 1, 14, 5)
    run_btn = st.button("🚀 실시간 가격 조회 시작", use_container_width=True)

if run_btn:
    progress_bar = st.progress(0)
    status_text = st.empty()
    results = []

    async def run_scanner():
        total_steps = scan_days * (max_stay - min_stay + 1)
        current_step = 0
        
        for i in range(scan_days):
            dep_date = start_date + datetime.timedelta(days=i)
            day_results = {"date": dep_date, "prices": {}}
            
            for stay in range(min_stay, max_stay + 1):
                ret_date = dep_date + datetime.timedelta(days=stay)
                status_text.text(f"🔍 {dep_date} 출발 - {stay}박 일정 검색 중...")
                
                price = await get_skyscanner_price(origin, dest, dep_date, ret_date)
                day_results["prices"][stay] = price
                
                current_step += 1
                progress_bar.progress(current_step / total_steps)
                await asyncio.sleep(2) # 차단 방지를 위해 약간 더 대기
            
            results.append(day_results)
        
        status_text.success("✅ 조회가 완료되었습니다!")
        return results

    final_data = asyncio.run(run_scanner())
    
    st.divider()
    st.subheader("📊 조회 결과")
    
    if final_data:
        df_list = []
        for item in final_data:
            row = {"출발일": item["date"]}
            for stay, price in item["prices"].items():
                row[f"{stay}박"] = f"{price:,}원" if price else "조회 실패"
            df_list.append(row)
        
        df = pd.DataFrame(df_list)
        st.dataframe(df, use_container_width=True)
