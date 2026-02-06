import streamlit as st
import asyncio
import subprocess
import datetime
import pandas as pd
from playwright.async_api import async_playwright

# --- 1. 브라우저 설치 (생략 가능하면 패스) ---
@st.cache_resource
def install_playwright_browsers():
    try:
        subprocess.run(["playwright", "install", "chromium"], check=True)
    except: pass

install_playwright_browsers()

# --- 2. 캘린더 화면에서 데이터 통째로 긁기 ---
async def get_combined_calendar(origin, dest, year_month):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1400, 'height': 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        # 사용자님이 알려주신 직관적인 URL 구조 활용
        ym = year_month.strftime("%y%m")
        url = f"https://www.skyscanner.co.kr/transport/flights/{origin}/{dest}/?oym={ym}&iym={ym}&rtn=1&cabinclass=economy&adultsv2=1"
        
        try:
            # networkidle 대신 commit(주소 확정)까지만 기다리고 직접 대기
            await page.goto(url, wait_until="commit", timeout=30000)
            
            # 가격 숫자가 보일 때까지 최대 15초만 대기
            price_selector = "span[class*='Price_mainPrice']"
            await page.wait_for_selector(price_selector, timeout=15000)
            
            # 왼쪽(출발), 오른쪽(귀국) 캘린더의 모든 날짜와 가격 긁기
            # 스카이스캐너는 보통 하나의 화면에 두 달치 혹은 두 캘린더를 띄움
            days_data = await page.eval_on_selector_all(
                "button[class*='CalendarDay']",
                """nodes => nodes.map(n => ({
                    label: n.getAttribute('aria-label'),
                    price: n.innerText.split('\\n').filter(t => t.includes('원'))[0] || null
                }))"""
            )
            
            await browser.close()
            return days_data
        except Exception as e:
            await browser.close()
            return None

# --- 3. 간단한 UI ---
st.title("✈️ 스카이스캐너 캘린더 전광판 긁기")

col1, col2 = st.columns(2)
with col1:
    origin = st.text_input("출발 (예: sela)", value="sela")
    dest = st.text_input("도착 (예: nrt)", value="nrt")
with col2:
    target_date = st.date_input("조회 월", datetime.date(2026, 5, 1))
    run_btn = st.button("🚀 캘린더 데이터 한 번에 가져오기")

if run_btn:
    with st.spinner("화면 분석 중..."):
        raw_data = asyncio.run(get_combined_calendar(origin, dest, target_date))
        
    if raw_data:
        # 중복 제거 및 데이터 정리
        clean_list = []
        seen = set()
        for item in raw_data:
            if item['price'] and item['label'] not in seen:
                clean_list.append({"날짜": item['label'], "가격": item['price']})
                seen.add(item['label'])
        
        df = pd.DataFrame(clean_list)
        st.success(f"총 {len(df)}개의 날짜별 가격을 찾았습니다!")
        st.dataframe(df, use_container_width=True)
        
        st.info("💡 이제 이 리스트에서 '5/1 가격' + '5/4 가격'을 조합하면 사용자님이 원하시는 결과가 됩니다.")
    else:
        st.error("타임아웃 또는 차단 발생. URL 구조나 인터넷 연결을 확인해주세요.")
