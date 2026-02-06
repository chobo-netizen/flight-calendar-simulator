import streamlit as st
import asyncio
import subprocess
import datetime
import pandas as pd
import re
from playwright.async_api import async_playwright

# --- 1. 브라우저 자동 설치 ---
@st.cache_resource
def install_playwright_browsers():
    try:
        subprocess.run(["playwright", "install", "chromium"], check=True)
    except:
        pass

install_playwright_browsers()

# --- 2. 핵심 로직: 1회 접속 후 날짜 클릭 및 전체 추출 ---
async def get_skyscanner_calendar(origin, dest, target_date, stays):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 1200},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        # 월간 뷰 URL (예: 2605)
        formatted_month = target_date.strftime("%y%m")
        url = f"https://www.skyscanner.co.kr/transport/flights/{origin}/{dest}/{formatted_month}/?adults=1&cabinclass=economy&ref=home"
        
        try:
            await page.goto(url, wait_until="networkidle", timeout=60000)
            
            # 1. 가는 날(출발일) 버튼 찾기 및 클릭
            # aria-label에 날짜 정보가 포함되어 있음 (예: "2026년 5월 1일")
            dep_label = target_date.strftime("%Y년 %-m월 %-d일") 
            dep_selector = f"button[aria-label*='{dep_label}']"
            
            await page.wait_for_selector(dep_selector, timeout=20000)
            await page.click(dep_selector)
            
            # 2. 클릭 후 귀국편 가격이 업데이트될 때까지 잠시 대기
            await asyncio.sleep(3) 
            
            # 3. 화면에 있는 모든 날짜/가격 데이터 긁기
            # 클릭된 상태이므로, 이제 각 날짜 칸에 표시된 가격은 '왕복 총액'이 됩니다.
            day_selector = "button[class*='CalendarDay']"
            raw_days = await page.eval_on_selector_all(
                day_selector,
                """nodes => nodes.map(n => ({
                    label: n.getAttribute('aria-label'),
                    price: n.querySelector("span[class*='Price_mainPrice']") ? n.querySelector("span[class*='Price_mainPrice']").innerText : null
                }))"""
            )
            
            await browser.close()
            return raw_days
        except Exception as e:
            await browser.close()
            st.error(f"데이터 추출 실패: {e}")
            return None

# --- 3. UI 구성 ---
st.set_page_config(page_title="초간편 항공권 스캐너", layout="wide")
st.title("✈️ 스카이스캐너 캘린더 원클릭 스캔")
st.info("한 번의 접속으로 선택하신 출발일 기준 모든 귀국일 가격을 가져옵니다.")

with st.sidebar:
    st.header("⚙️ 설정")
    origin = st.text_input("출발지", value="ICN").upper()
    dest = st.text_input("도착지", value="NRT").upper()
    dep_date = st.date_input("출발일 선택", datetime.date(2026, 5, 1))
    
    st.divider()
    stays = st.multiselect("확인할 체류 기간(박)", [1,2,3,4,5,6,7,10,14], default=[3,4,5])
    
    run_btn = st.button("🚀 가격 긁어오기", use_container_width=True)

if run_btn:
    with st.spinner(f"{dep_date} 출발 티켓 분석 중..."):
        data = asyncio.run(get_skyscanner_calendar(origin, dest, dep_date, stays))
        
    if data:
        results = []
        # 긁어온 데이터에서 내가 원하는 숙박일수(stay)에 해당하는 날짜 찾기
        for stay in stays:
            ret_date = dep_date + datetime.timedelta(days=stay)
            ret_label = ret_date.strftime("%-m월 %-d일") # 비교용 포맷
            
            found_price = "데이터 없음"
            for item in data:
                # 라벨에 귀국 날짜가 포함되어 있는지 확인
                if ret_label in item['label'] and item['price']:
                    found_price = item['price']
                    break
            
            results.append({
                "출발일": dep_date.strftime("%Y-%m-%d"),
                "귀국일": ret_date.strftime("%Y-%m-%d"),
                "체류기간": f"{stay}박",
                "왕복 총액": found_price
            })
            
        st.success("조회 완료!")
        st.table(pd.DataFrame(results))
    else:
        st.warning("가격을 가져오지 못했습니다. 출발일이 해당 월에 있는지 확인해주세요.")
