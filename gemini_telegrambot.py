#!/usr/bin/env python3
"""
Gemini 뉴스 스크래퍼 - Telegram Bot 연동 버전
- Telegram 메시지를 받으면 Gemini에서 뉴스를 가져와서 응답
- JSON 파일로 저장 후 Markdown 형태로 텔레그램 전송
- Google Sheets에 로그 기록
"""

import json
import time
import asyncio
import gspread
from google.oauth2.service_account import Credentials
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

# 사용자별 언어/지역 설정을 저장할 딕셔너리
user_settings = {}

class GoogleSheetLogger:
    def __init__(self, credentials_file, sheet_name):
        try:
            scopes = ["https://www.googleapis.com/auth/spreadsheets"]
            creds = Credentials.from_service_account_file(credentials_file, scopes=scopes)
            self.client = gspread.authorize(creds)
            self.sheet = self.client.open(sheet_name).sheet1
            self.ensure_header()
        except Exception as e:
            logger.error(f"Google Sheets 연결 실패: {e}")
            self.client = None

    def ensure_header(self):
        if self.client and self.sheet.cell(1, 1).value != "Timestamp":
            header = ["Timestamp", "User ID", "Username", "Request", "Response", "Elapsed Time (s)"]
            self.sheet.insert_row(header, 1)

    def log(self, user_id, username, request, response, elapsed_time):
        if self.client:
            try:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                row = [timestamp, str(user_id), username, request, response, f"{elapsed_time:.2f}"]
                self.sheet.append_row(row)
            except Exception as e:
                logger.error(f"Google Sheets 로깅 실패: {e}")

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
        
    def access_gemini(self, lang='ko', region='KR'):
        """Gemini 웹사이트 접속 (언어 및 지역 설정 포함)"""
        try:
            logger.info(f"Gemini 웹사이트에 접속 중... (언어: {lang}, 지역: {region})")
            self.driver.get(f"https://gemini.google.com/?lang={lang}&region={region}")
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
        if filename == None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
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
            
    def run(self, custom_prompt="오늘의 주요 뉴스 알려줘", lang='ko', region='KR'):
        """메인 실행 함수"""
        try:
            logger.info("=== Gemini 스크래퍼 시작 ===")
            
            self.setup_driver()
            self.access_gemini(lang, region)
            
            logger.info(f"프롬프트 입력 중: {custom_prompt}")
            textarea = self.find_textarea()
            if not textarea:
                logger.error("입력창을 찾을 수 없습니다.")
                return None, None
            
            textarea.clear()
            textarea.send_keys(custom_prompt)
            self.send_message(textarea)
            
            logger.info("응답을 기다리는 중...")
            time.sleep(30)
            
            response_text = self.get_response_text()
            
            if response_text:
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
    def __init__(self, token, sheet_logger):
        self.token = token
        self.application = None
        self.sheet_logger = sheet_logger
        
    def get_user_settings(self, user_id):
        """사용자 설정 가져오기 (없으면 기본값)"""
        return user_settings.get(user_id, {'lang': 'ko', 'region': 'KR'})

    def format_response_to_markdown(self, response_data):
        """응답 데이터를 Markdown 형태로 포맷팅"""
        if not response_data or 'response' not in response_data:
            return "❌ 응답 데이터를 가져올 수 없습니다."
            
        response = response_data['response']
        timestamp = response_data['timestamp']
        prompt = response_data['prompt']
        
        is_news = "뉴스" in prompt
        icon = "📰" if is_news else "🤖"
        title = "오늘의 주요 뉴스" if is_news else "Gemini AI 응답"
        
        markdown = f"{icon} **{title}**\n"
        markdown += f"❓ *질문: {prompt}*\n"
        markdown += f"🕐 {datetime.fromisoformat(timestamp).strftime('%Y-%m-%d %H:%M')}\n\n"
        
        lines = response.split('\n')
        formatted_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if any(keyword in line for keyword in ['정치', '경제', '사회', '국제', '재난', '안전']):
                if ':' in line and len(line) < 50:
                    formatted_lines.append(f"\n**{line}**")
                else:
                    formatted_lines.append(line)
            elif line in ['오늘의 주요 뉴스 알려줘', 'Gemini는', '새 창에서 열기']:
                continue
            else:
                formatted_lines.append(line)
        
        markdown += '\n'.join(formatted_lines)
        
        if len(markdown) > 4000:
            markdown = markdown[:3950] + "\n\n... (내용이 길어 일부 생략됨)"
            
        return markdown
        
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """시작 명령어 처리"""
        user_id = update.message.from_user.id
        settings = self.get_user_settings(user_id)
        
        welcome_msg = f"""
🤖 **Gemini AI 봇에 오신 것을 환영합니다!**

📰 이 봇은 Gemini AI를 통해 다양한 질문에 답변을 드립니다.

**현재 설정:**
- 언어: `{settings['lang']}`
- 지역: `{settings['region']}`

**사용 방법:**
• `/news` - 오늘의 뉴스 가져오기
• `/msg [질문]` - 원하는 질문을 Gemini에게 물어보기
• `/setting [항목] [값]` - 언어/지역 설정 변경
• `/start` - 도움말 보기

**설정 예시:**
• `/setting lang en` (언어를 영어로 변경)
• `/setting region US` (지역을 미국으로 변경)

응답을 받는데 약 30-60초가 소요됩니다. 잠시만 기다려주세요! 🙏
        """
        await update.message.reply_text(welcome_msg, parse_mode=ParseMode.MARKDOWN)

    async def setting_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """언어/지역 설정 명령어 처리"""
        user_id = update.message.from_user.id
        args = context.args
        
        if len(args) != 2:
            await update.message.reply_text(
                "**잘못된 사용법입니다.**\n"
                "예시: `/setting lang ko` 또는 `/setting region KR`",
                parse_mode=ParseMode.MARKDOWN
            )
            return

        setting_type, value = args[0].lower(), args[1].upper()
        
        if user_id not in user_settings:
            user_settings[user_id] = {'lang': 'ko', 'region': 'KR'}
            
        if setting_type == 'lang':
            user_settings[user_id]['lang'] = value.lower()
            await update.message.reply_text(f"✅ 언어가 `{value.lower()}`로 설정되었습니다.")
        elif setting_type == 'region':
            user_settings[user_id]['region'] = value
            await update.message.reply_text(f"✅ 지역이 `{value}`로 설정되었습니다.")
        else:
            await update.message.reply_text("❌ 잘못된 설정 항목입니다. `lang` 또는 `region`을 사용하세요.")

    async def news_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """뉴스 명령어 처리"""
        start_time = time.time()
        user = update.message.from_user
        user_id = user.id
        settings = self.get_user_settings(user_id)
        lang, region = settings['lang'], settings['region']
        prompt = f"오늘의 {region} 주요 뉴스 알려줘"

        loading_msg = await update.message.reply_text(
            f"📰 뉴스를 가져오는 중입니다... (언어: {lang}, 지역: {region})\n"
            "⏰ 약 30-60초 소요됩니다. 잠시만 기다려주세요!"
        )
        
        response_text = ""
        try:
            scraper = GeminiNewsScraper()
            filename, news_data = scraper.run(prompt, lang, region)
            
            if news_data:
                markdown_response = self.format_response_to_markdown(news_data)
                response_text = markdown_response
                await loading_msg.delete()
                try:
                    await update.message.reply_text(markdown_response, parse_mode=ParseMode.MARKDOWN)
                except Exception as markdown_error:
                    logger.warning(f"Markdown 파싱 오류, 일반 텍스트로 전송: {markdown_error}")
                    plain_text = markdown_response.replace("**", "").replace("*", "").replace("_", "")
                    response_text = plain_text
                    await update.message.reply_text(plain_text)
                logger.info(f"뉴스 전송 완료. 파일: {filename}")
            else:
                response_text = "❌ 뉴스를 가져오는데 실패했습니다."
                await loading_msg.edit_text(response_text)
                
        except Exception as e:
            logger.error(f"뉴스 명령어 처리 중 오류: {e}")
            response_text = "❌ 오류가 발생했습니다."
            await loading_msg.edit_text(response_text)
        finally:
            elapsed_time = time.time() - start_time
            self.sheet_logger.log(user_id, user.username, prompt, response_text, elapsed_time)
            
    async def msg_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """사용자 정의 메시지 명령어 처리"""
        start_time = time.time()
        user = update.message.from_user
        user_id = user.id
        settings = self.get_user_settings(user_id)
        lang, region = settings['lang'], settings['region']
        
        user_prompt = ' '.join(context.args)
        if not user_prompt.strip():
            await update.message.reply_text(
                "❓ **사용법:** `/msg [질문]`\n"
                "예시: `/msg 파이썬으로 웹 크롤링하는 방법 알려줘`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        loading_msg = await update.message.reply_text(
            f"🤖 질문을 처리하는 중입니다...\n❓ *{user_prompt}*\n"
            f"(언어: {lang}, 지역: {region})\n"
            "⏰ 약 30-60초 소요됩니다."
        )
        
        response_text = ""
        try:
            scraper = GeminiNewsScraper()
            filename, response_data = scraper.run(user_prompt, lang, region)
            
            if response_data:
                markdown_response = self.format_response_to_markdown(response_data)
                response_text = markdown_response
                await loading_msg.delete()
                try:
                    await update.message.reply_text(markdown_response, parse_mode=ParseMode.MARKDOWN)
                except Exception as markdown_error:
                    logger.warning(f"Markdown 파싱 오류, 일반 텍스트로 전송: {markdown_error}")
                    plain_text = markdown_response.replace("**", "").replace("*", "").replace("_", "")
                    response_text = plain_text
                    await update.message.reply_text(plain_text)
                logger.info(f"사용자 질문 응답 완료. 파일: {filename}")
            else:
                response_text = "❌ 응답을 가져오는데 실패했습니다."
                await loading_msg.edit_text(response_text)
                
        except Exception as e:
            logger.error(f"사용자 질문 처리 중 오류: {e}")
            response_text = "❌ 오류가 발생했습니다."
            await loading_msg.edit_text(response_text)
        finally:
            elapsed_time = time.time() - start_time
            self.sheet_logger.log(user_id, user.username, user_prompt, response_text, elapsed_time)
            
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """일반 메시지 처리"""
        message_text = update.message.text.lower()
        
        if any(keyword in message_text for keyword in ['뉴스', 'news', '오늘', '오늘의']):
            await self.news_command(update, context)
        else:
            await self.start_command(update, context)
            
    def run_bot(self):
        """봇 실행"""
        logger.info("텔레그램 봇을 시작합니다...")
        
        self.application = Application.builder().token(self.token).build()
        
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("setting", self.setting_command))
        self.application.add_handler(CommandHandler("news", self.news_command))
        self.application.add_handler(CommandHandler("msg", self.msg_command))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        logger.info("봇이 시작되었습니다. Ctrl+C로 종료할 수 있습니다.")
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)

def main():
    import os
    
    BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    GOOGLE_CREDENTIALS_FILE = os.getenv('GOOGLE_CREDENTIALS_FILE', 'google_credentials.json')
    GOOGLE_SHEET_NAME = os.getenv('GOOGLE_SHEET_NAME', 'Gemini Bot Logs')
    
    if not BOT_TOKEN or not GEMINI_API_KEY:
        logger.error("TELEGRAM_BOT_TOKEN 또는 GEMINI_API_KEY가 설정되지 않았습니다.")
        return

    # Google Sheets 로거 초기화
    sheet_logger = GoogleSheetLogger(GOOGLE_CREDENTIALS_FILE, GOOGLE_SHEET_NAME)

    bot = TelegramNewsBot(BOT_TOKEN, sheet_logger)
    try:
        bot.run_bot()
    except KeyboardInterrupt:
        logger.info("봇을 종료합니다...")
    except Exception as e:
        logger.error(f"봇 실행 중 오류: {e}")

if __name__ == "__main__":
    main()
