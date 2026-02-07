import streamlit as st
import asyncio
import datetime
import pandas as pd
from playwright.async_api import async_playwright

# 로컬에서 실행할 때는 차단 확률을 낮추기 위해 headless=False(브라우저 보임) 옵션을 쓸 수 있습니다.
async def get_skyscanner_calendar(origin, dest, ym):
    async with async_playwright() as p:
        # 로컬 실행의 장점: 브라우저가 뜨는 걸 직접 볼 수 있음 (속 시원함)
        browser = await p.chromium.launch(headless=False) # 작동 확인 후 True로 변경 가능
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 1000},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        # 사용자님이 알려주신 마법의 URL
        url = f"https://www.skyscanner.co.kr/transport/flights/{origin}/{dest}/?oym={ym}&iym={ym}&rtn=1&cabinclass=economy&adultsv2=1"
        
        try:
            st.write(f"🔗 접속 중: {url}")
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            
            # 가격이 로딩될 때까지 기다림
            await page.wait_for_selector("span[class*='Price_mainPrice']", timeout=20000)
            await asyncio.sleep(2) # 안정적인 로딩을 위해 2초만 더 대기
            
            # 모든 캘린더 데이 추출
            data = await page.evaluate("""() => {
                const results = [];
                const buttons = document.querySelectorAll("button[class*='CalendarDay']");
                buttons.forEach(b => {
                    const label = b.getAttribute('aria-label');
                    const price = b.querySelector("span[class*='Price_mainPrice']")?.innerText;
                    if (label && price) results.push({ "날짜": label, "가격": price });
                });
                return results;
            }""")
            
            await browser.close()
            return data
        except Exception as e:
            await browser.close()
            return str(e)

# --- UI ---
st.set_page_config(page_title="로컬 항공권 스캐너", layout="wide")
st.title("🚀 로컬 IP 파워! 스카이스캐너 전광판 긁기")

with st.sidebar:
    origin = st.text_input("출발 (예: sela)", value="sela")
    dest = st.text_input("도착 (예: nrt)", value="nrt")
    target_date = st.date_input("조회 월", datetime.date(2026, 5, 1))
    ym = target_date.strftime("%y%m")
    run_btn = st.button("실시간 데이터 가져오기")

if run_btn:
    with st.spinner("로컬 브라우저 가동 중..."):
        result = asyncio.run(get_skyscanner_calendar(origin, dest, ym))
        
        if isinstance(result, list):
            st.success(f"데이터 {len(result)}건 수집 완료!")
            df = pd.DataFrame(result)
            
            # 여기서부터 사용자님이 원하시는 '조합' 로직 시작
            st.subheader("📊 수집된 전광판 데이터")
            st.dataframe(df, use_container_width=True)
            
            # (예시) 5월 4일 가격 찾기
            # target = df[df['날짜'].str.contains("5월 4일", na=False)]
            # st.write(target)
            
        else:
            st.error(f"실패 사유: {result}")
