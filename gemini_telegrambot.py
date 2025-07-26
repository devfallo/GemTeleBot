#!/usr/bin/env python3
"""
Gemini 뉴스 스크래퍼 - Telegram Bot 연동 버전
- Telegram 메시지를 받으면 Gemini에서 뉴스를 가져와서 응답
- JSON 파일로 저장 후 Markdown 형태로 텔레그램 전송
"""

import json
import time
import asyncio
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.options import Options
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode
import logging

# 로깅 설정
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

class GeminiNewsScraper:
    def __init__(self):
        self.driver = None
        self.wait = None
        
    def setup_driver(self):
        """Chrome 드라이버 설정"""
        chrome_options = Options()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--headless")  # 백그라운드 실행
        chrome_options.add_argument("--user-data-dir=/tmp/chrome_profile")
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.wait = WebDriverWait(self.driver, 30)
        
    def access_gemini(self):
        """Gemini 웹사이트 접속"""
        try:
            logger.info("Gemini 웹사이트에 접속 중...")
            self.driver.get("https://gemini.google.com/")
            time.sleep(5)
            logger.info("페이지 로딩 완료")
            
        except Exception as e:
            logger.error(f"웹사이트 접속 중 오류: {e}")
            raise
            
    def find_textarea(self):
        """입력창 찾기"""
        textarea_selectors = [
            "textarea",
            "[contenteditable='true']",
            "input[type='text']",
            "[data-testid*='input']",
            "[placeholder*='message']",
            "[placeholder*='질문']",
            ".input-area textarea",
            "#prompt-textarea"
        ]
        
        for selector in textarea_selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    for element in elements:
                        if element.is_displayed() and element.is_enabled():
                            logger.info(f"입력창을 찾았습니다: {selector}")
                            return element
            except Exception:
                continue
                
        return None
        
    def send_message(self, textarea):
        """메시지 전송"""
        try:
            from selenium.webdriver.common.keys import Keys
            textarea.send_keys(Keys.RETURN)
            logger.info("Enter 키로 전송했습니다.")
            return
        except:
            pass
            
        send_button_selectors = [
            "button[aria-label*='Send']",
            "button[aria-label*='전송']",
            "[data-testid*='send']",
            "button[type='submit']",
            ".send-button",
            "button:has(svg)"
        ]
        
        for selector in send_button_selectors:
            try:
                buttons = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for button in buttons:
                    if button.is_displayed() and button.is_enabled():
                        button.click()
                        logger.info(f"전송 버튼을 클릭했습니다: {selector}")
                        return
            except Exception:
                continue
                
        # 마지막 시도
        textarea.send_keys(Keys.RETURN)
        
    def get_response_text(self):
        """응답 텍스트 추출"""
        try:
            body_text = self.driver.find_element(By.TAG_NAME, "body").text
            lines = body_text.split('\n')
            response_lines = []
            
            collecting = False
            for line in lines:
                if any(keyword in line for keyword in ['뉴스', 'News', '오늘', '주요']):
                    collecting = True
                    
                if collecting and line.strip():
                    response_lines.append(line.strip())
                    
            if response_lines:
                response_text = '\n'.join(response_lines)
                logger.info(f"응답 추출 완료 (길이: {len(response_text)} 문자)")
                return response_text
            else:
                logger.warning("뉴스 관련 응답을 찾을 수 없어 전체 페이지 텍스트를 반환합니다.")
                return body_text
                
        except Exception as e:
            logger.error(f"응답 텍스트 추출 중 오류: {e}")
            return "응답 추출 실패"
            
    def save_to_json(self, response_text, prompt="오늘의 주요 뉴스 알려줘", filename=None):
        """응답을 JSON 파일로 저장"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            # 뉴스가 아닌 경우 gemini_response로 파일명 변경
            prefix = "gemini_news" if "뉴스" in prompt else "gemini_response"
            filename = f"{prefix}_{timestamp}.json"
            
        data = {
            "timestamp": datetime.now().isoformat(),
            "prompt": prompt,
            "response": response_text,
            "source": "Gemini AI"
        }
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"결과가 {filename}에 저장되었습니다.")
            return filename, data
        except Exception as e:
            logger.error(f"JSON 파일 저장 중 오류: {e}")
            raise
            
    def run(self, custom_prompt="오늘의 주요 뉴스 알려줘"):
        """메인 실행 함수"""
        try:
            logger.info("=== Gemini 스크래퍼 시작 ===")
            
            # 드라이버 설정
            self.setup_driver()
            
            # 웹사이트 접속
            self.access_gemini()
            
            # 프롬프트 입력
            logger.info(f"프롬프트 입력 중: {custom_prompt}")
            textarea = self.find_textarea()
            if not textarea:
                logger.error("입력창을 찾을 수 없습니다.")
                return None, None
            
            textarea.clear()
            textarea.send_keys(custom_prompt)
            self.send_message(textarea)
            
            logger.info("응답을 기다리는 중...")
            time.sleep(30)  # 응답 대기
            
            # 응답 텍스트 가져오기
            response_text = self.get_response_text()
            
            if response_text:
                # JSON 파일로 저장
                filename, data = self.save_to_json(response_text, custom_prompt)
                logger.info("=== 작업 완료 ===")
                return filename, data
            else:
                logger.error("응답을 받지 못했습니다.")
                return None, None
            
        except Exception as e:
            logger.error(f"오류 발생: {e}")
            return None, None
        finally:
            if self.driver:
                self.driver.quit()

class TelegramNewsBot:
    def __init__(self, token):
        self.token = token
        self.application = None
        
    def format_response_to_markdown(self, response_data):
        """응답 데이터를 Markdown 형태로 포맷팅"""
        if not response_data or 'response' not in response_data:
            return "❌ 응답 데이터를 가져올 수 없습니다."
            
        response = response_data['response']
        timestamp = response_data['timestamp']
        prompt = response_data['prompt']
        
        # 뉴스인지 일반 질문인지 구분
        is_news = "뉴스" in prompt
        icon = "📰" if is_news else "🤖"
        title = "오늘의 주요 뉴스" if is_news else "Gemini AI 응답"
        
        # 기본 헤더
        markdown = f"{icon} **{title}**\n"
        markdown += f"❓ *질문: {prompt}*\n"
        markdown += f"🕐 {datetime.fromisoformat(timestamp).strftime('%Y-%m-%d %H:%M')}\n\n"
        
        # 응답 텍스트 처리
        lines = response.split('\n')
        formatted_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # 카테고리 헤더 처리
            if any(keyword in line for keyword in ['정치', '경제', '사회', '국제', '재난', '안전']):
                if ':' in line and len(line) < 50:
                    formatted_lines.append(f"\n**{line}**")
                else:
                    formatted_lines.append(line)
            # 불필요한 라인 제거
            elif line in ['오늘의 주요 뉴스 알려줘', 'Gemini는', '새 창에서 열기']:
                continue
            # 일반 텍스트
            else:
                formatted_lines.append(line)
        
        # 최종 마크다운 생성
        markdown += '\n'.join(formatted_lines)
        
        # 텔레그램 메시지 길이 제한 (4096자)
        if len(markdown) > 4000:
            markdown = markdown[:3950] + "\n\n... (내용이 길어 일부 생략됨)"
            
        return markdown
        
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """시작 명령어 처리"""
        welcome_msg = """
🤖 **Gemini AI 봇에 오신 것을 환영합니다!**

📰 이 봇은 Gemini AI를 통해 다양한 질문에 답변을 드립니다.

**사용 방법:**
• `/news` - 오늘의 뉴스 가져오기
• `/msg [질문]` - 원하는 질문을 Gemini에게 물어보기
• `/start` - 도움말 보기

**사용 예시:**
• `/msg 파이썬으로 웹 크롤링하는 방법 알려줘`
• `/msg 오늘 날씨는 어때?`
• `/msg AI에 대해 설명해줘`

응답을 받는데 약 30-60초가 소요됩니다. 잠시만 기다려주세요! 🙏
        """
        await update.message.reply_text(welcome_msg, parse_mode=ParseMode.MARKDOWN)
        
    async def news_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """뉴스 명령어 처리"""
        # 로딩 메시지 전송
        loading_msg = await update.message.reply_text(
            "📰 뉴스를 가져오는 중입니다...\n⏰ 약 30-60초 소요됩니다. 잠시만 기다려주세요!"
        )
        
        try:
            # 스크래퍼 실행
            scraper = GeminiNewsScraper()
            filename, news_data = scraper.run("오늘의 주요 뉴스 알려줘")
            
            if news_data:
                # Markdown 형태로 포맷팅
                markdown_response = self.format_response_to_markdown(news_data)
                
                # 로딩 메시지 삭제
                await loading_msg.delete()
                
                # 뉴스 전송 (Markdown 파싱 오류 방지)
                try:
                    await update.message.reply_text(
                        markdown_response, 
                        parse_mode=ParseMode.MARKDOWN
                    )
                except Exception as markdown_error:
                    logger.warning(f"Markdown 파싱 오류, 일반 텍스트로 전송: {markdown_error}")
                    # Markdown 태그 제거하고 일반 텍스트로 전송
                    plain_text = markdown_response.replace("**", "").replace("*", "").replace("_", "")
                    await update.message.reply_text(plain_text)
                
                # 파일 정보 로그
                logger.info(f"뉴스 전송 완료. 파일: {filename}")
                
            else:
                await loading_msg.edit_text("❌ 뉴스를 가져오는데 실패했습니다. 잠시 후 다시 시도해주세요.")
                
        except Exception as e:
            logger.error(f"뉴스 명령어 처리 중 오류: {e}")
            try:
                await loading_msg.edit_text("❌ 오류가 발생했습니다. 잠시 후 다시 시도해주세요.")
            except:
                # 메시지 편집 실패 시 새 메시지 전송
                await update.message.reply_text("❌ 오류가 발생했습니다. 잠시 후 다시 시도해주세요.")
            
    async def msg_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """사용자 정의 메시지 명령어 처리"""
        # 명령어에서 질문 부분 추출
        user_prompt = ' '.join(context.args)
        
        if not user_prompt.strip():
            help_msg = """
❓ **사용법:** `/msg [질문]`

**예시:**
• `/msg 파이썬으로 웹 크롤링하는 방법 알려줘`
• `/msg 오늘 날씨는 어때?`
• `/msg AI에 대해 설명해줘`
            """
            await update.message.reply_text(help_msg, parse_mode=ParseMode.MARKDOWN)
            return
        
        # 로딩 메시지 전송
        loading_msg = await update.message.reply_text(
            f"🤖 질문을 처리하는 중입니다...\n❓ *{user_prompt}*\n⏰ 약 30-60초 소요됩니다. 잠시만 기다려주세요!"
        )
        
        try:
            # 스크래퍼 실행
            scraper = GeminiNewsScraper()
            filename, response_data = scraper.run(user_prompt)
            
            if response_data:
                # Markdown 형태로 포맷팅
                markdown_response = self.format_response_to_markdown(response_data)
                
                # 로딩 메시지 삭제
                await loading_msg.delete()
                
                # 응답 전송 (Markdown 파싱 오류 방지)
                try:
                    await update.message.reply_text(
                        markdown_response, 
                        parse_mode=ParseMode.MARKDOWN
                    )
                except Exception as markdown_error:
                    logger.warning(f"Markdown 파싱 오류, 일반 텍스트로 전송: {markdown_error}")
                    # Markdown 태그 제거하고 일반 텍스트로 전송
                    plain_text = markdown_response.replace("**", "").replace("*", "").replace("_", "")
                    await update.message.reply_text(plain_text)
                
                # 파일 정보 로그
                logger.info(f"사용자 질문 응답 완료. 파일: {filename}")
                
            else:
                await loading_msg.edit_text("❌ 응답을 가져오는데 실패했습니다. 잠시 후 다시 시도해주세요.")
                
        except Exception as e:
            logger.error(f"사용자 질문 처리 중 오류: {e}")
            try:
                await loading_msg.edit_text("❌ 오류가 발생했습니다. 잠시 후 다시 시도해주세요.")
            except:
                # 메시지 편집 실패 시 새 메시지 전송
                await update.message.reply_text("❌ 오류가 발생했습니다. 잠시 후 다시 시도해주세요.")
            
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """일반 메시지 처리"""
        message_text = update.message.text.lower()
        
        # 뉴스 관련 키워드 감지
        if any(keyword in message_text for keyword in ['뉴스', 'news', '오늘', '오늘의']):
            await self.news_command(update, context)
        else:
            help_msg = """
📝 **사용 가능한 명령어:**

• `/news` - 오늘의 뉴스 가져오기
• `/msg [질문]` - 원하는 질문을 Gemini에게 물어보기
• `/start` - 도움말 보기

또는 "뉴스", "오늘의 뉴스" 등의 메시지를 보내주세요!
            """
            await update.message.reply_text(help_msg, parse_mode=ParseMode.MARKDOWN)
            
    def run_bot(self):
        """봇 실행"""
        logger.info("텔레그램 봇을 시작합니다...")
        
        # 애플리케이션 생성
        self.application = Application.builder().token(self.token).build()
        
        # 핸들러 등록
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("news", self.news_command))
        self.application.add_handler(CommandHandler("msg", self.msg_command))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        # 봇 실행
        logger.info("봇이 시작되었습니다. Ctrl+C로 종료할 수 있습니다.")
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)

def main():
    # 봇 토큰 설정 (환경변수)
    import os
    
    BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY') # Gemini API 키 추가
    
    if not BOT_TOKEN or not GEMINI_API_KEY:
        logger.error("TELEGRAM_BOT_TOKEN 또는 GEMINI_API_KEY가 설정되지 않았습니다.")
        return

    # 봇 실행
    bot = TelegramNewsBot(BOT_TOKEN)
    try:
        bot.run_bot()
    except KeyboardInterrupt:
        logger.info("봇을 종료합니다...")
    except Exception as e:
        logger.error(f"봇 실행 중 오류: {e}")

if __name__ == "__main__":
    main()