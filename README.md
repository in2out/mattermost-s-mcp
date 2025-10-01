# mattermost-s-mcp

Mattermost 웹훅을 MCP(Model Context Protocol)로 노출하여 Claude Desktop 등 AI 도구에서 바로 메시지를 전송할 수 있게 해주는 MCP 서버입니다.

## 특징

- **간단한 설정**: YAML 파일로 여러 웹훅 채널 관리
- **Claude Desktop 통합**: MCP 프로토콜로 Claude와 완벽하게 연동
- **기본 채널 지정**: 자주 사용하는 채널을 기본으로 설정
- **안전한 로깅**: 웹훅 URL이 자동으로 마스킹되어 로그에 기록

## 요구사항

- Node.js 18 이상
- npm

## 빠른 시작

### 1. 설치

```bash
git clone <repository-url> mattermost-s-mcp
cd mattermost-s-mcp
npm install
```

### 2. 설정

`config/webhooks.yaml` 파일을 편집하여 Mattermost 웹훅 정보를 추가합니다:

```yaml
version: 1
default_channel: ops-alert
webhooks:
  - channel: ops-alert
    url: https://your-mattermost-server/hooks/your-webhook-token
    description: 운영 알림 채널
  - channel: dev-notice
    url: https://your-mattermost-server/hooks/another-webhook-token
    description: 개발 공지 채널
```

### 3. Claude Desktop 등록

Claude Desktop 설정 파일에 다음을 추가합니다:

**위치**:
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Linux: `~/.config/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "mattermost-s-mcp": {
      "command": "node",
      "args": ["/절대/경로/mattermost-s-mcp/index.js"],
      "env": {
        "MATTERMOST_MCP_CONFIG": "/절대/경로/mattermost-s-mcp/config/webhooks.yaml"
      }
    }
  }
}
```

**중요**: 경로는 반드시 절대 경로로 지정해야 합니다.

### 4. Claude Desktop 재시작

Claude Desktop을 완전히 종료하고 다시 시작합니다.

## 사용 방법

Claude Desktop에서 다음과 같이 요청하면 됩니다:

### 예시 1: 메시지 전송
```
Mattermost로 "배포 완료" 메시지 보내줘
```

### 예시 2: 채널 목록 확인
```
Mattermost 채널 목록 보여줘
```

### 예시 3: 특정 채널로 전송
```
Mattermost dev-notice 채널로 "긴급 공지" 메시지 보내줘
```

## 사용 가능한 도구

1. **mattermost.list_webhooks**: 등록된 채널 목록과 기본 채널 확인
2. **mattermost.set_default**: 기본 채널 설정
3. **mattermost.send_message**: 메시지 전송

## 문제 해결

자세한 문제 해결 방법은 [INSTALL.md](./INSTALL.md)와 [USAGE.md](./USAGE.md)를 참고하세요.

### 주요 문제

**"server disconnected" 에러**
- Node.js 경로 확인: `which node` 또는 `where node`
- 절대 경로 사용 확인
- config/webhooks.yaml 파일 존재 확인

**메시지 전송 실패**
- 웹훅 URL이 올바른지 확인
- Mattermost 서버 접근 가능 여부 확인
- 웹훅이 활성화되어 있는지 확인

## 라이선스

MIT
