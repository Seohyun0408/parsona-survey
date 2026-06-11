# 공개 배포 체크리스트

## 1. Supabase 준비

- Supabase 프로젝트를 생성합니다.
- SQL Editor에서 `supabase_setup.sql`을 실행합니다.
- Project URL과 `service_role` 키를 준비합니다.

## 2. GitHub 저장소 준비

- 이 프로젝트 폴더를 GitHub 저장소에 업로드합니다.
- `.streamlit/secrets.toml`과 `research_data.csv`가 업로드되지 않았는지 확인합니다.
- `assets/min.png`가 저장소에 포함되었는지 확인합니다.

## 3. Streamlit Community Cloud 배포

- [Streamlit Community Cloud](https://share.streamlit.io/)에서 `Create app`을 선택합니다.
- GitHub 저장소와 브랜치를 선택합니다.
- Main file path에 `app.py`를 입력합니다.
- Advanced settings의 Secrets에 아래 내용을 실제 값으로 입력합니다.

```toml
OPENAI_API_KEY = "직접 입력"
OPENAI_MODEL = "gpt-4.1-mini"
SUPABASE_URL = "직접 입력"
SUPABASE_SERVICE_ROLE_KEY = "직접 입력"
REQUIRE_REMOTE_STORAGE = "true"
RESEARCHER_CONTACT = "직접 입력"
```

## 4. 공개 전 최종 테스트

- 동의하지 않으면 시작 버튼이 비활성화되는지 확인합니다.
- 사전 설문을 완료해야 대화 단계로 이동하는지 확인합니다.
- 민의 답변이 정상 생성되는지 확인합니다.
- 3분 후 입력창이 비활성화되고 사후 설문으로 이동 가능한지 확인합니다.
- 최종 제출 후 Supabase `research_responses` 테이블에 한 행이 생성되는지 확인합니다.
- 모바일 화면에서 전체 흐름을 확인합니다.

## 5. 참여자 배포

- Streamlit에서 생성된 공개 URL만 참여자에게 전달합니다.
- 테스트 응답은 본 조사 전에 Supabase에서 삭제합니다.
- API 사용량과 Supabase 저장 상태를 조사 기간 동안 확인합니다.
