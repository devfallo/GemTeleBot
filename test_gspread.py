import os
import gspread
from google.oauth2.service_account import Credentials
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GoogleSheetLogger:
    def __init__(self, credentials_file, sheet_name):
        try:
            scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
            creds = Credentials.from_service_account_file(credentials_file, scopes=scopes)
            self.client = gspread.authorize(creds)
            self.sheet = self.client.open(sheet_name).sheet1
            logger.info(f"Google Sheets '{sheet_name}'에 성공적으로 연결되었습니다.")
        except Exception as e:
            logger.error(f"Google Sheets 연결 실패: {e}")
            self.client = None

if __name__ == "__main__":
    GOOGLE_CREDENTIALS_FILE = os.getenv('GOOGLE_CREDENTIALS_FILE', 'google_credentials.json')
    GOOGLE_SHEET_NAME = os.getenv('GOOGLE_SHEET_NAME', 'Gemini Bot Logs')

    logger.info(f"Google Credentials File: {GOOGLE_CREDENTIALS_FILE}")
    logger.info(f"Google Sheet Name: {GOOGLE_SHEET_NAME}")

    # 테스트를 위해 임시로 GoogleSheetLogger 인스턴스 생성
    sheet_logger = GoogleSheetLogger(GOOGLE_CREDENTIALS_FILE, GOOGLE_SHEET_NAME)

    if sheet_logger.client:
        logger.info("Google Sheets 연결 테스트 성공!")
    else:
        logger.error("Google Sheets 연결 테스트 실패.")
