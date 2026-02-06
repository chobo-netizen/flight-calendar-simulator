import streamlit as st
import asyncio
import os
import subprocess
import datetime
import pandas as pd
from playwright.async_api import async_playwright

# --- 1. 브라우저 자동 설치 섹션 ---
# Streamlit Cloud 서버에는 브라우저가 없으므로 실행 시점에 설치해줘야 합니다.
@st.cache_resource
def install_playwright_browsers():
    try:
        # Playwright 브라우저 엔진(Chromium) 설치
        subprocess.run(["playwright", "install", "chromium"], check=True)
        # 시스템 의존성 라이브러리 설치
        subprocess.run(["playwright", "install-deps"], check=True)
    except Exception as e:
        st.error(f"브라우저 설치 중 오류가 발생했습니다: {e}")

# 앱 시작 시 설치 함수 호출
install_playwright_browsers()

# --- 2. 스카이스캐너 크롤링 로직 ---
async def get_skyscanner_price(origin, dest, dep_date, ret_date):
    async with async_playwright() as p:
        # 브라우저 실행 (headless=True 필수)
        browser = await p.chromium.launch(headless=True)
        
        # 실제 브라우저처럼 보이게 하기 위한 User-Agent 설정
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        # 날짜 포맷팅 (예: 2026-05-01 -> 260501)
        url_dep = dep_date.strftime("%y%m%d")
        url_ret = ret_date.strftime("%y%m%d")
        
        # 스카이스캐너 URL 생성
        url = f"https://www.skyscanner.co.kr/transport/flights/{origin}/{dest}/{url_dep}/{url_ret}/?adults=1&cabinclass=economy&ref=home"
        
        try:
            # 페이지 이동 및 네트워크 안정화 대기
            await page.goto(url, wait_until="networkidle", timeout=60000)
            
            # 가격 정보 셀렉터 대기 (스카이스캐너의 메인 가격 표시 태그)
            # 'Price_mainPrice'를 포함하는 클래스를 찾습니다.
            price_selector = "span[class*='Price_mainPrice']"
            await page.wait_for_selector(price_selector, timeout=20000)
            
            # 가격 텍스트 추출 및 숫자 변환
            price_text = await page.inner_text(price_selector)
            price = int(price_text.replace(",", "").replace("원", "").strip())
            
            await browser.close()
            return price
        except Exception:
            await browser.close()
            return None

# --- 3. Streamlit UI 구성 ---
st.set_page_config(page_title="항공권 가격 시뮬레이터", layout="wide")

st.title("✈️ 실시간 항공권 가격 캘린더")
st.markdown("출발지와 목적지, 그리고 기간을 설정한 후 '조회 시작'을 눌러주세요.")

# 사이드바 설정
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
    # 서버 부하를 고려해 조회 일수 제한 (무료 티어는 성능이 낮음)
    scan_days = st.slider("조회할 일수 (오늘부터 N일간)", 1, 14, 5)
    
    run_btn = st.button("🚀 실시간 가격 조회 시작", use_container_width=True)

# 실행 버튼 클릭 시
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
                
                # 진행률 업데이트
                current_step += 1
                progress_bar.progress(current_step / total_steps)
                
                # 봇 감지 회피를 위한 짧은 대기
                await asyncio.sleep(1.5)
            
            results.append(day_results)
        
        status_text.success("✅ 조회가 완료되었습니다!")
        return results

    # 비동기 루프 실행
    final_data = asyncio.run(run_scanner())
    
    # 결과 시각화 (테이블 형태)
    st.divider()
    st.subheader("📊 조회 결과")
    
    if final_data:
        # 데이터프레임 변환
        df_list = []
        for item in final_data:
            row = {"출발일": item["date"]}
            for stay, price in item["prices"].items():
                row[f"{stay}박"] = f"{price:,}원" if price else "조회 실패"
            df_list.append(row)
        
        df = pd.DataFrame(df_list)
        st.dataframe(df, use_container_width=True)
    else:
        st.warning("조회된 데이터가 없습니다.")
