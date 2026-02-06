import streamlit as st
import asyncio
import os
import subprocess
import datetime
import pandas as pd
from playwright.async_api import async_playwright

# --- 1. 브라우저 자동 설치 (최초 1회) ---
@st.cache_resource
def install_playwright_browsers():
    try:
        # 브라우저 엔진 설치
        subprocess.run(["playwright", "install", "chromium"], check=True)
    except Exception as e:
        print(f"설치 로그: {e}")

install_playwright_browsers()

# --- 2. 스카이스캐너 가격 추출 핵심 함수 ---
async def fetch_skyscanner(origin, dest, dep_date, ret_date):
    """
    한 개의 일정(왕복)에 대한 실시간 최저가를 가져옵니다.
    """
    async with async_playwright() as p:
        # 차단 회피를 위한 브라우저 설정
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        # URL 생성 (날짜 형식: 260501)
        d = dep_date.strftime("%y%m%d")
        r = ret_date.strftime("%y%m%d")
        url = f"https://www.skyscanner.co.kr/transport/flights/{origin}/{dest}/{d}/{r}/?adults=1&cabinclass=economy&ref=home"
        
        try:
            # 페이지 이동
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            
            # 가격 요소가 나타날 때까지 대기 (최대 30초)
            price_selector = "span[class*='Price_mainPrice']"
            await page.wait_for_selector(price_selector, timeout=30000)
            
            # 가격 텍스트 추출 및 정제
            price_text = await page.inner_text(price_selector)
            price = int(price_text.replace(",", "").replace("원", "").strip())
            
            await browser.close()
            return price
        except Exception as e:
            await browser.close()
            return None

# --- 3. UI 레이아웃 ---
st.set_page_config(page_title="항공권 가격 캘린더", layout="wide")
st.title("📅 항공권 실시간 가격 시뮬레이터")
st.info("스카이스캐너 실시간 데이터를 조회합니다. 차단 방지를 위해 천천히 진행됩니다.")

# 사이드바 설정
with st.sidebar:
    st.header("🔍 검색 조건")
    origin = st.text_input("출발지 (공항코드)", value="ICN").upper()
    dest = st.text_input("도착지 (공항코드)", value="NRT").upper()
    
    st.divider()
    start_date = st.date_input("조회 시작일", datetime.date(2026, 5, 1))
    scan_days = st.slider("조회할 일수 (출발일 기준)", 1, 7, 3)
    
    st.subheader("⏳ 숙박 기간 (박)")
    stays = st.multiselect("확인할 숙박 기간", [1, 2, 3, 4, 5, 6, 7], default=[3, 4])
    
    run_btn = st.button("🚀 검색 시작", use_container_width=True)

# --- 4. 메인 실행 로직 ---
if run_btn:
    if not stays:
        st.error("최소 하나 이상의 숙박 기간을 선택해주세요.")
    else:
        results = []
        total_count = scan_days * len(stays)
        current_count = 0
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # 날짜별 루프
        for i in range(scan_days):
            dep = start_date + datetime.timedelta(days=i)
            day_data = {"출발일": dep.strftime("%Y-%m-%d (월/일)")}
            
            for stay in stays:
                ret = dep + datetime.timedelta(days=stay)
                current_count += 1
                
                # 상태 표시
                status_text.write(f"🔎 조회 중: {dep} 출발 ({stay}박 일정) - [{current_count}/{total_count}]")
                
                # 비동기 함수 실행 (가격을 가져옴)
                try:
                    price = asyncio.run(fetch_skyscanner(origin, dest, dep, ret))
                    if price:
                        day_data[f"{stay}박"] = f"{price:,}원"
                    else:
                        day_data[f"{stay}박"] = "재시도 필요"
                except Exception as e:
                    day_data[f"{stay}박"] = "오류"
                
                # 진행도 업데이트
                progress_bar.progress(current_count / total_count)
                
                # 봇 차단 방지를 위한 간격 (매우 중요)
                asyncio.run(asyncio.sleep(2))
            
            results.append(day_data)
        
        status_text.success("✅ 조회가 완료되었습니다!")
        
        # 데이터프레임 출력
        st.divider()
        st.subheader("📊 결과 요약")
        df = pd.DataFrame(results)
        st.table(df) # 표 형태로 깔끔하게 표시
