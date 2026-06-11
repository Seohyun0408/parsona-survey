# AI 대화와 이주민 태도 연구

Streamlit 기반 연구 실험 앱입니다. 응답은 Supabase에 영구 저장되며, Supabase 설정이 없는 로컬 환경에서는 `research_data.csv`에 저장됩니다.

## 로컬 실행

1. `.streamlit/secrets.toml.example`을 참고해 `.streamlit/secrets.toml`을 생성합니다.
2. 아래 명령으로 실행합니다.

```powershell
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

## Supabase 설정

1. Supabase 프로젝트를 생성합니다.
2. SQL Editor에서 `supabase_setup.sql`을 실행합니다.
3. Project Settings > API에서 Project URL과 `service_role` 키를 확인합니다.
4. Streamlit Secrets에 아래 값을 등록합니다.

```toml
OPENAI_API_KEY = "..."
OPENAI_MODEL = "gpt-4.1-mini"
SUPABASE_URL = "https://YOUR_PROJECT.supabase.co"
SUPABASE_SERVICE_ROLE_KEY = "..."
REQUIRE_REMOTE_STORAGE = "true"
RESEARCHER_CONTACT = "연구자 이메일 또는 기관 연락처"
```

`service_role` 키는 절대 GitHub에 커밋하지 마세요. 앱 서버의 Streamlit Secrets에서만 사용합니다.
공개 배포에서는 `REQUIRE_REMOTE_STORAGE = "true"`를 유지해야 원격 저장 설정 누락 시 데이터 손실을 방지할 수 있습니다.

## Streamlit Community Cloud 배포

1. 이 폴더를 비공개 GitHub 저장소에 올립니다.
2. [Streamlit Community Cloud](https://share.streamlit.io/)에서 저장소와 `app.py`를 선택합니다.
3. Advanced settings > Secrets에 위 시크릿 값을 등록합니다.
4. 배포 후 생성된 URL로 내부 테스트를 완료한 뒤 참여자에게 배포합니다.

상세 절차와 공개 전 확인 항목은 `DEPLOYMENT_CHECKLIST.md`를 따르세요.

## 운영 점검

- Supabase `research_responses` 테이블에 테스트 응답이 저장되는지 확인합니다.
- OpenAI API 사용 한도와 결제 설정을 확인합니다.
- 연구 참여 동의문과 개인정보 처리 내용을 기관 기준에 맞게 검토합니다.
- 공개 배포 전 모바일 환경에서 전체 흐름을 테스트합니다.
