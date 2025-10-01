# mattermost-s-mcp 공개 자료

Mattermost 웹훅을 MCP(Model Context Protocol)로 노출해 Claude/ChatGPT 등 AI 도구에서 바로 메시지를 전송할 수 있게 해 주는 번들입니다. `public/` 디렉터리의 파일만 배포하면 동작에 필요한 모든 요소가 포함됩니다.

## 구성
- `mattermost-s-mcp.py` : STDIO 기반 MCP 서버 (Python)
- `config/webhooks.yaml` : 채널-웹훅 매핑 템플릿
- `mcp.json` : MCP 클라이언트용 manifest
- `requirements.txt` : 필요한 패키지 목록(PyYAML, requests)
- `docs/` : 설치/사용 가이드, 테스트 캡처 이미지 저장 위치

## 설치 절차
1. Python 3.10 이상을 준비합니다.
2. 가상환경이 필요하면 생성한 뒤 활성화합니다.
3. 의존성을 설치합니다.
   ```bash
   pip install -r requirements.txt
   ```
4. `config/webhooks.yaml`를 복사 후 실제 Mattermost 웹훅 정보로 수정합니다.
5. (선택) 설정 파일 위치를 바꾸려면 `MATTERMOST_MCP_CONFIG` 환경 변수를 원하는 경로로 지정합니다.

## 설정 파일 작성
```yaml
version: 1
default_channel: ops-alert
webhooks:
  - channel: ops-alert
    url: http://slack.axgate.com/hooks/<token>
    description: 운영 알림 채널
  - channel: dev-notice
    url: http://slack.axgate.com/hooks/<token>
```
- `channel`은 고유해야 합니다.
- `default_channel`은 목록 중 하나여야 합니다.
- 웹훅 URL은 HTTP/HTTPS를 사용합니다.

## MCP 등록 방법
1. `mcp.json` 파일을 AI 도구가 요구하는 위치에 복사합니다.
2. Manifest에서 정의한 명령은 `python mattermost-s-mcp.py`로 MCP 서버를 실행합니다.
3. Claude Desktop 예시
   - Settings → MCP Servers → `Add manifest file`
   - `mcp.json` 선택 후 저장
4. OpenAI ChatGPT (MCP 지원 베타) 예시
   - `~/.config/openai/mcp.json` 등에 symlink 또는 복사
   - ChatGPT 클라이언트를 재시작

초기 연결 후 도구 목록에서 `mattermost.list_webhooks`, `mattermost.set_default`, `mattermost.send_message`가 노출되어야 합니다.

## 수동 확인 절차
1. CLI 모드로 목록 확인
   ```bash
   python mattermost-s-mcp.py --config config/webhooks.yaml list
   ```
2. 메시지 전송 리허설
   ```bash
   python mattermost-s-mcp.py --config config/webhooks.yaml send --text "테스트" --dry-run
   ```
3. 실제 전송 테스트(운영 채널 주의)
   ```bash
   python mattermost-s-mcp.py --config config/webhooks.yaml send --text "테스트" --channel ops-alert
   ```
4. MCP 클라이언트에서 `mattermost.send_message` 호출 후 결과 캡처를 `docs/images/` 하위에 저장합니다. (예: `docs/images/test-send.png`)

## 장애 대응 메모
- 설정 파일 파싱 오류 → YAML 구조 확인 후 재시도
- "기본 웹훅이 설정되어 있지 않습니다." → `mattermost.set_default` 호출로 기본 채널 지정
- HTTP 4xx/5xx 반환 → URL/권한 검토 후 재시도, 로그에는 웹훅 토큰이 마스킹됩니다.

## 향후 업데이트 기록
- [ ] 실제 테스트 이미지 추가 예정 (`docs/images/`)
- [ ] 첨부파일 전송, 재시도 옵션 등 확장 시 본 문서를 갱신합니다.
