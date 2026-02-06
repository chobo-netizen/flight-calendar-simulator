import streamlit as st
import asyncio
import subprocess
import datetime
import pandas as pd
from playwright.async_api import async_playwright

# --- 1. 환경 설정 (최적화) ---
@st.cache_resource
def install_browsers():
    subprocess.run(["playwright", "install", "chromium"], check=True)

install_browsers()

async def get_skyscanner_data(origin, dest, ym):
    async with async_playwright() as p:
        # 차단 방지를 위해 실제 브라우저와 거의 흡사한 옵션 부여
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            viewport={'width': 1280, 'height': 800},
            locale="ko-KR"
        )
        page = await context.new_page()
        
        # 사용자님이 알려주신 직관적인 캘린더 전용 URL
        # selectedoday/iday=01로 설정해서 캘린더를 강제로 활성화
        url = f"https://www.skyscanner.co.kr/transport/flights/{origin}/{dest}/?oym={ym}&iym={ym}&selectedoday=01&selectediday=01&rtn=1&cabinclass=economy&adultsv2=1&ref=home"
        
        try:
            # 1. 페이지 접속 (최소한의 로딩만 기다림)
            await page.goto(url, wait_until="commit", timeout=30000)
            
            # 2. 캘린더 레이아웃이 보일 때까지 대기
            # 가격 정보가 담긴 span이나 버튼이 보이면 바로 진행
            try:
                await page.wait_for_selector("button[class*='CalendarDay']", timeout=15000)
            except:
                # 만약 차단 페이지(Captcha)가 떴다면 여기서 에러 발생
                return "BLOCKED"

            # 3. 데이터 추출 (자바스크립트로 실행해서 속도 극대화)
            # 출발/귀국 캘린더가 나뉘어 있으므로 모든 데이터를 일단 긁음
            data = await page.evaluate("""() => {
                const results = [];
                const nodes = document.querySelectorAll("button[class*='CalendarDay']");
                nodes.forEach(n => {
                    const label = n.getAttribute('aria-label');
                    const priceSpan = n.querySelector("span[class*='Price_mainPrice']");
                    if (label && priceSpan) {
                        results.append({ label, price: priceSpan.innerText });
                    }
                });
                return results;
            }""")
            
            await browser.close()
            return data
        except Exception as e:
            await browser.close()
            return str(e)

# --- 2. UI ---
st.title("⚡ 스카이스캐너 '전광판' 고속 추출")

c1, c2 = st.columns(2)
with c1:
    origin = st.text_input("출발 (예: sela)", value="sela")
    dest = st.text_input("도착 (예: nrt)", value="nrt")
with c2:
    target_date = st.date_input("조회 월", datetime.date(2026, 5, 1))
    ym = target_date.strftime("%y%m")

if st.button("🚀 데이터 낚아채기"):
    with st.spinner("스카이스캐너 서버와 밀당 중..."):
        result = asyncio.run(get_skyscanner_data(origin, dest, ym))
    
    if result == "BLOCKED":
        st.error("🚨 스카이스캐너가 접속을 차단했습니다. (IP 차단 가능성)")
        st.info("해결책: 1. 잠시 후 시도 2. 로컬(내 컴퓨터)에서 실행 3. 출발/도착 코드를 다시 확인")
    elif isinstance(result, list) and len(result) > 0:
        st.success(f"성공! {len(result)}개의 가격 데이터를 찾았습니다.")
        df = pd.DataFrame(result)
        st.dataframe(df)
    else:
        st.warning(f"데이터를 찾지 못했습니다. (사유: {result})")
