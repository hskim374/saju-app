# saju-mvp

FastAPI + Jinja2 기반의 사주 MVP입니다.  
더미 데이터 대신 실제 만세력 기준 사주 8자를 계산하고, 대운/세운/월운/일운과 분야별 운세까지 규칙 기반으로 제공합니다.  
현재는 결과 페이지에서 이메일로 HTML 리포트를 발송하고, 리드 정보는 Google Sheets에 저장합니다.

## 사용한 계산 방식

- 양력 입력은 그대로 사용합니다.
- 음력 입력은 `korean_lunar_calendar`로 한국천문연구원(KARI) 기준 양력으로 변환합니다.
- 년주는 입춘 기준으로 계산합니다.
- 월주는 음력 월이 아니라 12절기 절입 시각 기준으로 계산합니다.
- 일주는 한국 기준 양력 날짜를 Julian Day Number(JDN)로 변환한 뒤, `2000-01-07 = 갑자일`을 기준 epoch로 하여 60갑자 순환으로 계산합니다.
- 일주 계산은 `lunar_python`, `korean_lunar_calendar`, 선택적으로 `sxtwl` 결과와 비교 검증합니다.
- 시주는 계산된 일간과 출생시를 기준으로 `오자원둔` 공식(갑기일 갑자시 시작, 을경일 병자시 시작, 병신일 무자시 시작, 정임일 경자시 시작, 무계일 임자시 시작)으로 계산합니다.
- 기본 시간대는 `Asia/Seoul`(UTC+9)입니다.
- 년주/월주 경계는 `lunar_python`의 절기 시각이 UTC+8 기준으로 동작하는 점을 반영해 한국 시간 기준으로 1시간 보정합니다.

## 오행 계산 기준

- 대상: 년주, 월주, 일주, 시주의 천간과 지지
- 집계 방식: 총 8개 글자의 오행을 각각 1개씩 집계
- 지지의 지장간은 현재 버전에서 제외합니다.
- 지지 오행은 주기운 기준으로 사용합니다.
  - 자/해: 수
  - 인/묘: 목
  - 사/오: 화
  - 신/유: 금
  - 축/진/미/술: 토
- dominant와 weak는 동일 개수일 때 고정 순서 `목 → 화 → 토 → 금 → 수`로 결정합니다.

## 십성 계산 기준

- 기준축: 일간(day stem)
- 계산 대상: 년간, 월간, 시간
- 현재 버전은 천간만 계산합니다.
- 오행 생극과 음양 일치/불일치를 조합해 아래 규칙을 사용합니다.
  - 동일 오행: 비견 / 겁재
  - 내가 생하는 오행: 식신 / 상관
  - 내가 극하는 오행: 편재 / 정재
  - 나를 극하는 오행: 편관 / 정관
  - 나를 생하는 오행: 편인 / 정인

## 해석 로직

- 해석은 AI 생성 문장이 아니라 규칙 기반(rule-based) 문장 선택 방식입니다.
- 오행 강약, 보조 오행, 부족 오행을 함께 사용해 문장을 구성합니다.
- 같은 입력에는 같은 문장이 나오도록 결정적 분기만 사용합니다.
- 문장 템플릿은 3~5개 분기형 표현 중 조건에 맞는 형태를 선택합니다.
- 부족 오행은 `0개 / 1개 / 2개 이상` 강도에 따라 보완 문장을 다르게 냅니다.
- 직장운과 관계운은 십성 흐름에 따라 `긍정 / 주의 / 변화` 톤과 강도를 나눠 해석합니다.
- 주요 해석 섹션은 `한 줄 요약 -> 쉬운 설명 -> 현실에서 이렇게 나타납니다 -> 장점과 주의점 -> 행동 조언` 5단 구조로 출력합니다.
- 해석 엔진은 전환 문장과 강조 문장을 함께 조합해 웹/메일/PDF에서 같은 리듬으로 읽히도록 구성합니다.
- 원국 해석은 `오행 중심 -> 보완 오행 -> 부족 오행 -> 현재 대운/세운 흐름` 순서로 연결합니다.
- 동일 오행이라도 성격, 재물, 직장, 관계 영역에서 표현을 다르게 분리합니다.
- 웹 결과, HTML 이메일, PDF 템플릿이 같은 5단 구조 데이터를 공유합니다.

## 해석 엔진 구조

- `services/interpretation_rules.py`
  - 오행 강약, 보완 오행, 부족 강도 같은 규칙 계산
- `services/interpretation_templates.py`
  - 오행 강/약, 성격/재물/직장/관계, 운세, 십성 설명 템플릿 풀 정의
- `services/interpretation_engine.py`
  - 원국, 십성, 대운, 세운 흐름을 합쳐 5단 구조 설명형 문장 조합
- `services/interpretation.py`
  - 기존 호출부와의 호환을 위한 얇은 래퍼

## 무료 / 프리미엄

- 무료 리포트는 기본 해석과 간단 운세 중심으로 구성됩니다.
- 프리미엄 리포트는 인생 흐름 타임라인, 결정 포인트, 재물 흐름 심층 분석, 직업/사업 방향, 관계 심층 분석, 리스크, 실행 전략까지 확장됩니다.
- 결과 페이지에서는 프리미엄 teaser와 CTA를 먼저 보여주고, 프리미엄 상태에서만 전체 심층 섹션과 PDF 다운로드가 열립니다.

## 대운 계산 기준

- 순행/역행은 년간 음양과 성별을 함께 사용합니다.
  - 양년 남성, 음년 여성: 순행
  - 음년 남성, 양년 여성: 역행
- 성별 입력은 필수입니다.
- 성별을 필수로 받는 이유는 대운 순행/역행 방향이 달라져 전체 운세 해석이 바뀌기 때문입니다.
- 대운 시작 시점은 출생 시각에서 순행이면 다음 절입, 역행이면 이전 절입까지의 실제 시간 차이를 사용합니다.
- 대운 시작 나이는 `절입까지의 일수 / 3`을 계산한 뒤 올림해 정수 나이로 잡습니다.
- 월주를 기준으로 다음 또는 이전 간지를 10년 단위로 순차 배치합니다.
- 현재 버전은 기본 8개 대운 주기를 생성합니다.
- 사용자 화면에는 `출생 직후`, `이른 시기`, `유년기 무렵` 같은 요약 표현을 사용하고, 내부 계산값은 그대로 유지합니다.

## 세운 / 월운 / 일운 계산 기준

### 세운

- 특정 연도의 세운은 해당 연도 `7월 1일 12:00 KST` 기준 년주를 사용해 경계 문제를 피합니다.
- 세운 해석은 원국 일간 기준 십성과 현재 작동 중인 대운 십성을 함께 봅니다.
- 결과에는 세운 간지, 십성, 활성 대운, 집중 키워드를 포함합니다.

### 월운

- 월운은 해당 연도 각 달의 `15일 12:00 KST` 기준 월주를 사용합니다.
- 월주는 절기 기준으로 계산되므로 단순 음력 월이 아닙니다.
- 12개월 전체를 생성하고, 선택 월이 있으면 화면에서 해당 월을 따로 강조합니다.

### 일운

- 일운은 대상 양력 날짜의 일주를 같은 JDN 기준식으로 계산합니다.
- 일간 대비 십성으로 그날의 요약과 키워드를 생성합니다.
- 현재 버전은 오늘 운세와 특정 날짜 운세를 같은 계산 방식으로 처리합니다.

## 직장운 / 결혼운 분석 기준

### 직장운

- 직장운은 관성(정관/편관)을 우선 신호로 보고, 인성/식상/재성 흐름을 보조 신호로 사용합니다.
- 세운 십성과 활성 대운 십성을 함께 봅니다.
- 결과는 `summary`, `strengths`, `warnings` 구조로 반환합니다.

### 결혼운 / 연애운

- 남성은 재성(정재/편재), 여성은 관성(정관/편관)을 중심 신호로 사용합니다.
- 현재 버전은 인연 흐름, 관계 안정성, 감정 속도 조절 중심의 1차 규칙만 반영합니다.

## 일주 계산 기준

- 기준일(epoch): `2000-01-07`
- 기준 간지: `갑자일`
- 기준 숫자: `JDN 2451551`
- 계산식:
  `cycle_index = (JDN(target_date) - 2451551) % 60`
- 천간 인덱스: `cycle_index % 10`
- 지지 인덱스: `cycle_index % 12`
- 이 기준은 현재 프로젝트에서 `korean_lunar_calendar`와 `sxtwl` 비교값에 맞춰 검증했습니다.
- UTC/KST 차이는 일주 자체에는 직접 적용하지 않고, 한국 입력 날짜(`Asia/Seoul` 기준 civil date)를 그대로 사용합니다.
- 다만 디버그 로그에는 동일 입력의 UTC 시각과 UTC 날짜도 함께 출력해 날짜 경계 오해를 점검할 수 있게 했습니다.

## 사용한 외부 라이브러리와 이유

### `korean_lunar_calendar`

- 한국식 음력/윤달을 양력으로 정확히 변환하기 위해 사용합니다.
- 패키지 설명과 소스 주석 기준으로 한국천문연구원(KARI) 기준 데이터를 따릅니다.
- 윤달 입력을 명시적으로 처리할 수 있습니다.

### `lunar_python`

- 절기 시각과 사주 8자 계산 기능을 제공합니다.
- `EightChar`를 통해 년주, 월주, 일주, 시주를 모두 계산할 수 있습니다.
- 순수 Python 기반이라 Windows + Python 3.13 환경에서도 C++ 빌드 도구 없이 설치가 가능합니다.

## 라이브러리 선택 이유

현재 조합은 다음과 같습니다.

- 음력/윤달 변환: `korean_lunar_calendar`
- 절기/간지 계산: `lunar_python`

이 조합을 선택한 이유는 아래와 같습니다.

- 한국식 음력/윤달 변환은 `korean_lunar_calendar`가 더 직접적입니다.
- `sxtwl`는 정확도는 좋지만 Windows에서 C++ 빌드가 필요한 경우가 있어 설치 장벽이 큽니다.
- `lunar_python`은 절기와 사주 계산을 순수 Python으로 제공해 배포와 테스트가 쉽습니다.
- `lunar_python`의 절기 시각은 UTC+8 기준 동작으로 보이므로, 한국 시간(UTC+9) 기준 년주/월주 경계는 코드에서 1시간 보정해 처리합니다.
- 일주는 라이브러리 내부 블랙박스 대신 기준일이 명시된 독립 계산식을 사용하도록 분리했습니다.

## 실행 방법

```bash
pip install -r requirements.txt
python -m uvicorn main:app --reload --port 8001
```

브라우저에서 `http://127.0.0.1:8001/`에 접속합니다.

`.env.example`를 복사해 `.env`를 만들면 SMTP/Google Sheets 환경변수를 자동으로 불러옵니다.

```bash
cp .env.example .env
```

## Render 배포 준비

현재 배포 기준은 Render Web Service입니다. Render 공식 문서 기준으로 FastAPI 서비스는 `pip install -r requirements.txt`로 빌드하고, `uvicorn main:app --host 0.0.0.0 --port $PORT`로 실행하는 구성이 가장 단순합니다. Render는 기본적으로 `0.0.0.0` 바인딩과 서비스 포트 바인딩을 요구하며, 기본 기대 포트는 `10000`이지만 실제 Start Command에서는 `$PORT` 사용이 권장됩니다. Python 버전은 `.python-version` 또는 `PYTHON_VERSION`으로 고정할 수 있습니다. 현재 프로젝트는 Python `3.11` 기준으로 맞추는 것을 권장합니다. 참고:

- https://render.com/docs/deploy-fastapi
- https://render.com/docs/web-services
- https://render.com/docs/python-version

### 배포용 의존성

Render 초기 배포에서는 아래 의존성만 사용합니다.

- `fastapi`
- `uvicorn`
- `jinja2`
- `python-multipart`
- `korean_lunar_calendar`
- `lunar_python`
- `gspread`
- `python-dotenv`
- `tzdata`

`weasyprint`는 Render에서 추가 시스템 라이브러리 구성이 필요하므로 기본 배포 의존성에서 제외했습니다. PDF 생성 코드는 유지되어 있지만, 초기 Render 배포에서는 비활성 상태로 보는 편이 안전합니다. `pytest`도 런타임에는 필요하지 않아 배포 의존성에서 제외했습니다.

### 환경변수 원칙

`.env`는 로컬 개발 전용입니다. Render에서는 Dashboard의 Environment 설정에 직접 값을 넣어야 합니다. 코드에서는 `os.getenv(...)` 기반으로 동작하고, 로컬에서는 `python-dotenv`가 있으면 `.env`를 자동으로 읽습니다.

Render에서 사용하는 주요 환경변수:

SMTP

- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USERNAME`
- `SMTP_PASSWORD`
- `SMTP_FROM_EMAIL`
- `SMTP_FROM_NAME`
- `SMTP_SUBJECT_PREFIX`
- `SMTP_USE_TLS`

Google Sheets

- `GOOGLE_SHEETS_SPREADSHEET_ID`
- `GOOGLE_SERVICE_ACCOUNT_JSON`

선택값:

- `LEAD_STORE_BACKEND=sheet`
- `PYTHON_VERSION=3.11.11` 또는 저장소 루트의 `.python-version`

### GitHub 업로드

```bash
git init
git add .
git commit -m "deploy ready"
git branch -M main
git remote add origin <repo-url>
git push -u origin main
```

`.env`, 서비스 계정 JSON, 기타 민감정보는 저장소에 올리지 않아야 합니다.

### Render 설정

Render Dashboard에서 `New > Web Service`를 선택한 뒤 GitHub 저장소를 연결합니다.

권장 설정:

- Build Command: `pip install -r requirements.txt`
- Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`

앱 내부 `__main__` 실행 경로도 `PORT` 환경변수를 우선 사용하고, 로컬 기본값은 `10000`으로 설정되어 있습니다.

### 배포 후 확인

1. Render가 발급한 URL에 접속합니다.
2. 입력 폼이 정상적으로 뜨는지 확인합니다.
3. 샘플 생년월일을 넣고 결과 페이지가 정상적으로 렌더링되는지 확인합니다.
4. Environment 설정을 넣었다면 이메일 발송과 Google Sheets 저장도 확인합니다.

### 배포 초기 전략

1단계는 무료 리포트 서비스와 기본 계산 안정화에 집중합니다.
2단계에서 이메일 입력 기능을 운영 환경에서 활성화합니다.
3단계에서 프리미엄 리포트 및 결제 흐름을 붙입니다.

현재 배포 준비 목표는 "내 PC에서 돌아가던 프로그램을 누구나 접속 가능한 서비스로 전환하는 것"이며, 이 기준에 맞춰 런타임 의존성과 실행 경로를 최소화했습니다.

## 이메일 / Google Sheets 설정

### Gmail SMTP 빠른 설정

1. Google 계정에서 2단계 인증을 켭니다.
2. Google 계정 보안 메뉴에서 앱 비밀번호를 생성합니다.
3. 프로젝트 루트에서 `.env.example`를 `.env`로 복사합니다.
4. 아래 항목만 실제 값으로 채웁니다.

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=youraddress@gmail.com
SMTP_PASSWORD=your-gmail-app-password
SMTP_FROM_EMAIL=youraddress@gmail.com
SMTP_FROM_NAME=내 사주 리포트
SMTP_SUBJECT_PREFIX=saju-mvp
SMTP_USE_TLS=true
```

Gmail SMTP 사용 시 `SMTP_USERNAME`과 `SMTP_FROM_EMAIL`은 같은 Gmail 주소로 맞추는 편이 안전합니다.

### SMTP 환경변수

- `SMTP_HOST`
- `SMTP_PORT` (기본값 `587`)
- `SMTP_USERNAME`
- `SMTP_PASSWORD`
- `SMTP_FROM_EMAIL`
- `SMTP_FROM_NAME` (선택)
- `SMTP_SUBJECT_PREFIX` (선택)
- `SMTP_USE_TLS` (기본값 `true`)

Gmail 기준 권장값:

- `SMTP_HOST=smtp.gmail.com`
- `SMTP_PORT=587`
- `SMTP_USE_TLS=true`
- `SMTP_USERNAME=<Gmail 주소>`
- `SMTP_FROM_EMAIL=<Gmail 주소>`

### Google Sheets 환경변수

- `LEAD_STORE_BACKEND=sheet`
- `GOOGLE_SHEETS_SPREADSHEET_ID`
- `GOOGLE_SERVICE_ACCOUNT_JSON` 또는 `GOOGLE_SERVICE_ACCOUNT_FILE`

Google Sheets 시트 이름은 `leads`이며, 첫 행은 아래 컬럼으로 자동 생성됩니다.

- `email`
- `name`
- `birth_input`
- `solar_date`
- `year_pillar`
- `month_pillar`
- `day_pillar`
- `time_pillar`
- `created_at`
- `consent`

`created_at`은 Google Sheets 저장 시 `Asia/Seoul` 기준 ISO 시각으로 기록합니다.

서비스 계정 인증 방식은 `gspread`의 service account 인증 방식을 사용합니다.

### 실제 발송 확인 절차

1. `.env`에 Gmail SMTP와 Google Sheets 값을 입력합니다.
2. 서버를 재시작합니다.
3. 결과 페이지에서 이메일 주소를 입력하고 `이메일로 리포트 받기`를 누릅니다.
4. 확인 포인트:
   - 화면에 성공 메시지가 뜨는지
   - 메일함에 HTML 리포트가 도착하는지
   - Google Sheets `leads` 시트에 한 줄이 추가되는지

## 테스트 방법

```bash
pytest
```

서버 실행 중에는 일주 계산 진단 로그가 출력됩니다. 로그에는 아래 항목이 포함됩니다.

- 입력의 KST 시각 / UTC 시각
- KST 날짜 / UTC 날짜
- 대상 날짜의 JDN
- 기준 epoch 날짜와 offset days
- 독립 계산식 결과
- `lunar_python` 결과
- `korean_lunar_calendar` 결과
- `sxtwl`가 설치된 환경에서는 `sxtwl` 결과
- 모든 계산 방식 일치 여부

## 알려진 한계

- `korean_lunar_calendar`의 음력 입력 지원 범위는 패키지 데이터 범위에 따릅니다.
  현재 소스 기준 음력 `1000-01-01`부터 `2050-11-18`, 양력 `1000-02-13`부터 `2050-12-31`입니다.
- `lunar_python`의 절기 시각은 UTC+8 기준 동작으로 해석되므로, 한국 시간 기준 년주/월주 계산에는 코드에서 1시간 보정을 적용합니다.
- 일주는 한국 입력 날짜를 직접 사용하며, UTC 날짜는 진단용으로만 기록합니다.
- 야자시 기준으로 일주까지 넘겨 계산하는 별도 학파 옵션은 아직 넣지 않았습니다.
- 시간 미상 입력은 지원하지만, 절입일에는 정확한 년주/월주 판정을 위해 시간이 필요합니다.
- 월운은 각 월 15일 기준 대표 월주를 사용하므로 월초 절입 직전 며칠의 세부 체감 차이까지는 분리하지 않습니다.
- 직장운/결혼운은 합충형파해, 지장간, 용신, 격국까지 반영한 고급 해석이 아닙니다.
- 관계운은 결혼운/연애운을 별도 모델로 분리하지 않고 1차 공통 구조로 제공합니다.
- 현재 UX는 핵심 요약 카드와 섹션형 결과 페이지를 우선하며, 접기/툴팁 같은 고급 상호작용은 아직 제한적입니다.
- 이메일 발송과 Google Sheets 저장은 환경변수가 준비되어 있어야 실제 동작합니다.
- PDF 생성 기능은 내부적으로 유지하지만 현재 UI에서는 노출하지 않습니다.

## 현재 구현 범위

- 원국 8자 계산
- 오행 분석
- 십성 계산
- 기초 성향 해석
- 대운 계산
- 세운 계산
- 월운 12개월 계산
- 특정 날짜 일운 계산
- 직장운
- 결혼운 / 연애운
- 핵심 요약 카드
- 성별 필수 입력 기반 UX
- 가독성 중심 결과 페이지
- HTML 이메일 리포트 발송
- Google Sheets 리드 저장
- PDF 생성 로직 내부 유지

## 현재 미구현 범위

- 지장간 반영
- 합충형파해 상세 반영
- 용신 분석
- 격국 분석
- 궁합
- PDF 리포트
- 유료 상세 리포트
- 월별 직장운 / 월별 관계운 세부 분리
- 대운세운과 지지 관계의 고급 점수화
- 개발자 모드 기반 상세 디버그 패널 분리

## 향후 확장 포인트

- 용신 분석
- 격국 분석
- 궁합
- 대운/세운과 합충형파해 결합 해석
- 직장운/관계운의 월운·일운 세부 버전
- 이메일 발송 이후 PostgreSQL 등 DB 저장으로 교체
- 이메일 자동화/마케팅 워크플로 연계
- 유료 PDF 리포트 재노출
- 유료 상세 리포트
- 시간대별 지역 확장
- 야자시 일주 경계 옵션 분리
- 지장간 반영
- 십성의 지지 확장
