import asyncio
from playwright.async_api import async_playwright

EXPAND_BUTTON = "button:has(span:text('상세 정보 더 보기'))"

async def click_expand_button(page):
    """🔽 '상세 정보 더 보기' 버튼 클릭 with retry"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # 버튼 존재 확인 후 클릭
            expand_button = page.locator(EXPAND_BUTTON)
            if await expand_button.is_visible():
                await expand_button.click()
                await page.wait_for_timeout(7000)  # 로딩 대기 (headless 모드 최적화)
                # 네트워크 유휴 상태 확인 (더 긴 대기)
                await page.wait_for_load_state('networkidle', timeout=15000)
                return
            else:
                return
        except Exception as e:
            if attempt < max_retries - 1:
                await page.wait_for_timeout(2000)  # 재시도 전 대기
            else:
                print("else")

async def get_span_with_test_class_async():
    """🚀 비동기 버전"""
    async with async_playwright() as p:
        try:
            browser = await p.chromium.launch(headless=False)
            page = await browser.new_page()
        
            await page.goto("https://www.wanted.co.kr/wd/295402")
           
            # 버튼 클릭 
            await click_expand_button(page)
            
            # 🎯 요소 선택 및 대기
            await page.wait_for_selector('section.JobContent_descriptionWrapper__RMlfm')
            # div1 = await page.query_selector('div.JobDescription_JobDescription__paragraph__wrapper__WPrKC span.wds-h4ga6o')
            div2 = await page.query_selector_all('div.JobDescription_JobDescription__paragraph__87w8I')
            
            # text1 = await div1.text_content() 
            # print(f"포지션 상세: {text1}")
            
            # for title, text in zip(['주요 업무', '자격요건'], div2): 
            #     text2 = await text.text_content()
            #     print(f"{title}: {text2}")
            details = {}
            
            for factor in div2: 
                content = await factor.text_content()
                if '우대사항' in content: 
                    details['우대사항'] = content.replace('우대사항','')
                if '주요업무' in content: 
                    details['주요업무'] = content.replace('주요업무','')
                if '자격요건' in content: 
                    details['자격요건'] = content.replace('자격요건','')
                if '혜택 및 복지' in content: 
                    details['혜택 및 복지'] = content.replace('혜택 및 복지','')
                if '채용 전형' in content: 
                    details['채용 전형'] = content.replace('채용 전형','')
            # ul = await page.query_selector_all('ul.CompanyTags_CompanyTags__list__XmzkW li')
            
            # for li in ul: 
            #     tag = await li.text_content()
            #     print(tag)
            
            # deadline = await page.query_selector('span.wds-1u1yyy')
            # deadline_text = await deadline.text_content()
            # print(f'마감일: {deadline_text }')
            
            # region = await page.query_selector('span.wds-1td1qmv')
            # region_text = await region.text_content() 
            # print(f"지역 {region_text}")
            print(len(details))
        except Exception as error:
            print(f"⚠️ 오류 발생: {error}")
            
        finally:
            await browser.close()

if __name__ == "__main__": 
    asyncio.run(get_span_with_test_class_async())  # 비동기 함수 호출 시 await 사용