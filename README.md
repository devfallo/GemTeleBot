# Gemini 뉴스 텔레그램 봇

이 프로젝트는 Google Gemini AI를 활용하여 최신 뉴스를 스크래핑하고, 사용자의 질문에 답변하며, 모든 상호작용을 Google Sheets에 기록하는 텔레그램 봇입니다. Selenium을 사용하여 웹 브라우저를 자동화하고, GitHub Actions를 통해 간편하게 배포할 수 있습니다.

## ✨ 주요 기능

- **📰 뉴스 스크래핑**: Google Gemini 웹사이트에 접속하여 오늘의 주요 뉴스를 가져옵니다.
- **🤖 사용자 맞춤 질문**: `/msg` 명령어를 통해 사용자가 원하는 모든 질문을 Gemini AI에게 할 수 있습니다.
- **⚙️ 언어 및 지역 설정**: `/setting` 명령어로 사용자별로 뉴스 및 응답의 언어(`lang`)와 지역(`region`)을 맞춤 설정할 수 있습니다.
- **📊 Google Sheets 로깅**: 모든 사용자 요청과 봇의 응답, 그리고 처리 시간을 Google Sheets에 자동으로 기록하여 사용 현황을 쉽게 파악할 수 있습니다.
- **🚀 자동 배포**: `main` 브랜치에 코드가 푸시되면 GitHub Actions를 통해 자동으로 서버에 배포됩니다.
- **🛡️ 안전한 자격 증명 관리**: 모든 API 키와 인증서는 `.env` 파일과 GitHub Secrets를 통해 안전하게 관리됩니다.

---

## 🛠️ 설치 및 설정 방법

### 1. 프로젝트 클론

```bash
git clone https://github.com/devfallo/GemTeleBot.git
cd GemTeleBot
```

### 2. 가상 환경 생성 및 활성화

```bash
# 가상 환경 생성
python3 -m venv venv

# 가상 환경 활성화 (macOS/Linux)
source venv/bin/activate

# 가상 환경 활성화 (Windows)
.\venv\Scripts\activate
```

### 3. 의존성 설치

프로젝트에 필요한 라이브러리들을 `requirements.txt` 파일을 이용해 설치합니다.

```bash
pip install -r requirements.txt
```

### 4. Google Cloud 설정

이 봇은 Google Sheets에 로그를 기록하기 위해 Google Cloud 서비스 계정이 필요합니다.

1.  **Google Cloud 프로젝트를 생성**하고, **Google Sheets API**와 **Google Drive API**를 활성화합니다.
2.  **서비스 계정(Service Account)을 생성**하고, 키(Key)를 JSON 형식으로 다운로드합니다.
3.  다운로드한 JSON 파일의 이름을 `google_credentials.json`으로 변경하고 프로젝트 루트 디렉토리에 배치합니다.
4.  생성된 서비스 계정의 이메일 주소(예: `your-bot@your-project.iam.gserviceaccount.com`)를 복사합니다.
5.  로그를 기록할 **Google Sheet 파일을 생성**하고, 오른쪽 상단의 **"공유"** 버튼을 눌러 복사한 서비스 계정 이메일을 추가한 뒤 **"편집자(Editor)"** 권한을 부여합니다.

### 5. `.env` 파일 설정

프로젝트 루트 디렉토리에 `.env` 파일을 생성하고 아래 내용을 채워넣습니다.

```env
# 텔레그램 봇 토큰 (BotFather에게 발급)
TELEGRAM_BOT_TOKEN="YOUR_TELEGRAM_BOT_TOKEN"

# Gemini API 키 (현재 코드에서는 직접 사용되지 않으나, 추후 확장성을 위해 유지)
GEMINI_API_KEY="YOUR_GEMINI_API_KEY"

# Google Cloud 인증 정보 파일 경로
GOOGLE_CREDENTIALS_FILE="google_credentials.json"

# 로그를 기록할 Google Sheet의 이름
GOOGLE_SHEET_NAME="Your Google Sheet Name"
```

---

## ▶️ 실행 방법

### 로컬에서 실행하기

모든 설정이 완료되었다면, 아래 명령어로 봇을 실행할 수 있습니다.

```bash
python gemini_telegrambot.py
```

봇이 성공적으로 실행되면 "텔레그램 봇을 시작합니다..." 라는 메시지가 터미널에 출력됩니다.

### 텔레그램 명령어

- `/start`: 환영 메시지와 명령어 도움말을 표시합니다.
- `/news`: 오늘의 주요 뉴스를 가져옵니다.
- `/msg [질문 내용]`: Gemini AI에게 원하는 질문을 합니다.
  - 예시: `/msg 파이썬으로 웹 크롤링하는 법 알려줘`
- `/setting [lang 또는 region] [값]`: 언어 또는 지역 설정을 변경합니다.
  - 예시: `/setting lang en` (언어를 영어로 변경)
  - 예시: `/setting region US` (지역을 미국으로 변경)

---

## 🚀 배포 (GitHub Actions)

이 프로젝트는 `main` 브랜치에 변경사항이 푸시되면 GitHub Actions를 통해 자동으로 배포되도록 설정되어 있습니다.

배포를 위해, GitHub 리포지토리의 `Settings` > `Secrets and variables` > `Actions`에 다음 Secret들을 등록해야 합니다.

- `TELEGRAM_BOT_TOKEN`: 텔레그램 봇 토큰.
- `GEMINI_API_KEY`: Gemini API 키.
- `GOOGLE_SHEET_NAME`: 로그를 기록할 Google Sheet의 이름.
- `GOOGLE_CREDENTIALS_JSON`: `google_credentials.json` 파일의 **내용 전체**를 복사하여 붙여넣습니다.
