import streamlit as st
import asyncio
import os
import subprocess
import datetime
import pandas as pd
from playwright.async_api import async_playwright

# --- 1. 환경 설정 및 브라우저 설치 ---
@st.cache_resource
def install_playwright_browsers():
    try:
        subprocess.run(["playwright", "install", "chromium"], check=True)
    except:
        pass

install_playwright_browsers()

# --- 2. 스카이스캐너 캘린더 데이터 추출 로직 ---
async def get_calendar_prices(origin, dest, year_month):
    """
    특정 월의 전체 가격 데이터를 캘린더 뷰에서 가져오려고 시도합니다.
    """
    async with async_playwright() as p:
        # 봇 탐지를 피하기 위한 브라우저 설정
        browser = await p.chromium.launch(headless=True)
        # 일반적인 사용자의 브라우저 환경을 흉내냅니다.
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        # 스카이스캐너의 '월간 단위' 검색 URL (이 방식이 차단이 덜함)
        url = f"https://www.skyscanner.co.kr/transport/flights/{origin}/{dest}/{year_month[2:]}/?adults=1&cabinclass=economy&ref=home"
        
        try:
            # 페이지 접속
            await page.goto(url, wait_until="networkidle", timeout=60000)
            
            # 1. 팝업이나 쿠키 동의창이 뜨면 닫기 시도 (차단 방지)
            try:
                if await page.query_selector("button:has-text('동의')"):
                    await page.click("button:has-text('동의')", timeout=3000)
            except:
                pass

            # 2. 가격 데이터 로딩 대기
            # 스카이스캐너는 가격이 로딩될 때 span 내에 숫자가 채워집니다.
            price_selector = "span[class*='Price_mainPrice']"
            await page.wait_for_selector(price_selector, timeout=30000)
            
            # 3. 현재 페이지에 노출된 모든 가격과 날짜 정보를 수집
            # 캘린더 모드일 경우 각 날짜 칸의 데이터를 긁습니다.
            prices = await page.eval_on_selector_all(
                "button[class*='CalendarDay']",
                "nodes => nodes.map(n => ({ date: n.getAttribute('aria-label'), price: n.innerText }))"
            )
            
            await browser.close()
            return prices
        except Exception as e:
            await browser.close()
            return None

# --- 3. 개별 왕복 가격 정밀 조회 (Fallback) ---
async def get_exact_roundtrip_price(origin, dest, dep_date, ret_date):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        d = dep_date.strftime("%y%m%d")
        r = ret_date.strftime("%y%m%d")
        url = f"https://www.skyscanner.co.kr/transport/flights/{origin}/{dest}/{d}/{r}/?adults=1&cabinclass=economy&ref=home"
        
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            # 가격이 뜰 때까지 랜덤하게 대기 (사람처럼 보이게)
            await asyncio.sleep(5) 
            
            price_element = await page.query_selector("span[class*='Price_mainPrice']")
            if price_element:
                text = await price_element.inner_text()
                price = int(text.replace(",", "").replace("원", "").strip())
                await browser.close()
                return price
            await browser.close()
            return None
        except:
            await browser.close()
            return None

# --- 4. UI 레이아웃 ---
st.set_page_config(page_title="항공권 가격 캘린더", layout="wide")
st.title("📅 스카이스캐너 정밀 스캔 (왕복 기준)")

with st.sidebar:
    st.header("🔍 검색 설정")
    origin = st.text_input("출발지 (예: ICN)", value="ICN").upper()
    dest = st.text_input("도착지 (예: NRT)", value="NRT").upper()
    
    st.divider()
    target_date = st.date_input("조회 시작일", datetime.date(2026, 5, 1))
    scan_count = st.slider("조회할 일수", 1, 7, 3)
    
    st.subheader("⏳ 숙박 일수")
    stays = st.multiselect("확인할 숙박 일수", [3, 4, 5, 6, 7], default=[3, 4])
    
    run_btn = st.button("🚀 검색 시작 (왕복 합산)", use_container_width=True)

if run_btn:
    all_data = []
    progress = st.progress(0)
    total_queries = scan_count * len(stays)
    count = 0

    async def start_scan():
        nonlocal count
        for i in range(scan_count):
            dep = target_date + datetime.timedelta(days=i)
            day_results = {"출발일": dep.strftime("%Y-%m-%d")}
            
            for stay in stays:
                ret = dep + datetime.timedelta(days=stay)
                st.write(f"🔄 {dep} ~ {ret} ({stay}박) 조회 중...")
                
                price = await get_exact_roundtrip_price(origin, dest, dep, ret)
                day_results[f"{stay}박"] = f"{price:,}원" if price else "확인불가"
                
                count += 1
                progress.progress(count / total_queries)
                # 너무 빠른 연타는 차단의 지름길입니다.
                await asyncio.sleep(3) 
            
            all_data.append(day_results)
        return all_data

    final_results = asyncio.run(start_scan())
    
    st.divider()
    st.subheader("📊 최종 왕복 요금표")
    st.table(pd.DataFrame(final_results))
