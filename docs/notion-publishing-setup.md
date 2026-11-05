# Notion → GitHub Actions 게시 설정

## 1. Notion 통합 생성
1. https://www.notion.so/profile/integrations 에서 내부 통합을 생성합니다.
2. Notion 페이지에서 연결(Connections) 메뉴를 열고 해당 통합을 추가합니다.
3. 통합의 내부 API 토큰을 복사합니다. **토큰을 코드나 PR에 붙여넣지 마세요.**

## 2. GitHub Secret
저장소 Settings → Secrets and variables → Actions → New repository secret에서 다음을 추가합니다.

- Name: `NOTION_TOKEN`
- Value: Notion 통합 토큰

GitHub Actions가 PR을 만들도록 저장소 Settings → Actions → General → Workflow permissions에서 **Read and write permissions** 및 **Allow GitHub Actions to create and approve pull requests**를 활성화해야 할 수 있습니다. 조직 정책에 따라 선택지가 제한될 수 있습니다.

## 3. 실행
이 PR이 병합된 다음 저장소 Actions → **Publish Notion page as PR** → Run workflow에서 `notion_url`을 입력합니다. `slug`와 `post_date`는 선택입니다.

새 글은 `_posts/`에, 이미지는 `assets/images/posts/<date-slug>/`에 저장됩니다. 같은 경로가 이미 있으면 **덮어쓰지 않고 실패**합니다. 별도의 브랜치와 Draft PR이 생성되며 자동 병합되지 않습니다.

## 4. 확인 및 제한
- Notion API의 이미지 다운로드 URL은 임시 주소이므로 실행 중에 바로 내려받아 저장소에 보관합니다.
- Notion 페이지의 첨부 이미지는 20MB 이하 PNG/JPEG/WebP/GIF/SVG만 지원합니다.
- 일반 텍스트, 제목, 목록, 코드, 표, 이미지, 인용, 구분선 및 일부 임베드를 처리합니다. 복잡한 Notion 데이터베이스/수식/중첩 레이아웃은 검토가 필요합니다.
- 실패 시 부분 결과를 게시하지 않습니다. 토큰, API 키, 실제 계정 비밀번호가 포함되지 않았는지 PR에서 검토하세요.
- 기존 PR #3의 이미지 8개는 아직 업로드되지 않았습니다. 이 자동화는 **향후 새 글용**이며, 기존 PR #3 이미지 업로드를 자동으로 소급 처리하지 않습니다.
- 원본 Notion 페이지는 수정하지 않습니다.
