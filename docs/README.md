# mattermost-s-mcp 문서

Mattermost 웹훅을 MCP(Model Context Protocol)로 노출해 Claude Desktop 등 AI 도구에서 바로 메시지를 전송할 수 있게 해 주는 Node.js 기반 MCP 서버입니다.

## 구성

- **index.js**: STDIO 기반 MCP 서버 (Node.js, @modelcontextprotocol/sdk 사용)
- **package.json**: Node.js 프로젝트 설정 및 의존성
- **config/webhooks.yaml**: 채널-웹훅 매핑 설정
- **docs/**: 설치/사용 가이드

## 주요 특징

1. **공식 MCP SDK 사용**: @modelcontextprotocol/sdk를 사용하여 표준 MCP 프로토콜 구현
2. **간단한 설정**: YAML 파일로 여러 채널 관리
3. **안전한 로깅**: 웹훅 토큰 자동 마스킹
4. **크로스 플랫폼**: Windows, macOS, Linux 모두 지원

## 설치 절차

### 1. Node.js 설치
Node.js 18 이상이 필요합니다.
- https://nodejs.org/ 에서 다운로드

### 2. 프로젝트 설치
```bash
npm install
```

### 3. 설정 파일 작성 (config/webhooks.yaml)

```yaml
version: 1
default_channel: ops-alert
webhooks:
  - channel: ops-alert
    url: https://your-mattermost-server/hooks/<token>
    description: 운영 알림 채널
  - channel: dev-notice
    url: https://your-mattermost-server/hooks/<token>
    description: 개발 공지 채널
```

**설정 규칙**:
- `channel`은 고유해야 합니다
- `default_channel`은 webhooks 목록 중 하나여야 합니다
- 웹훅 URL은 HTTP/HTTPS로 시작해야 합니다

### 4. Claude Desktop 등록

**설정 파일 위치**:
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Linux: `~/.config/Claude/claude_desktop_config.json`

**설정 예시**:
```json
{
  "mcpServers": {
    "mattermost-s-mcp": {
      "command": "node",
      "args": ["/absolute/path/to/mattermost-s-mcp/index.js"],
      "env": {
        "MATTERMOST_MCP_CONFIG": "/absolute/path/to/mattermost-s-mcp/config/webhooks.yaml"
      }
    }
  }
}
```

## MCP 도구

초기 연결 후 Claude Desktop에서 다음 도구를 사용할 수 있습니다:

### 1. mattermost.list_webhooks
등록된 웹훅 채널 목록과 기본 채널을 확인합니다.

**입력**: 없음

**출력 예시**:
```json
{
  "default": "ops-alert",
  "channels": [
    {
      "channel": "ops-alert",
      "description": "운영 알림 채널"
    },
    {
      "channel": "dev-notice",
      "description": "개발 공지 채널"
    }
  ]
}
```

### 2. mattermost.set_default
기본 채널을 설정합니다.

**입력**:
- `channel` (string, required): 기본으로 설정할 채널명

**출력**: 설정 완료 메시지

### 3. mattermost.send_message
메시지를 전송합니다.

**입력**:
- `text` (string, required): 전송할 메시지 텍스트
- `channel` (string, optional): 메시지를 보낼 채널명 (미지정 시 기본 채널)

**출력**: 전송 완료 메시지 (웹훅 URL은 마스킹됨)

## 수동 테스트

### 1. 서버 시작 테스트
```bash
node index.js
```

정상 시작 시 stderr에 다음이 출력됩니다:
```
Mattermost MCP server running on stdio
```

### 2. Claude Desktop에서 테스트

**채널 목록 확인**:
```
Mattermost 채널 목록 보여줘
```

**메시지 전송**:
```
Mattermost로 "테스트 메시지" 보내줘
```

**특정 채널로 전송**:
```
Mattermost dev-notice 채널로 "긴급 공지" 메시지 보내줘
```

## 장애 대응

### 설정 파일 파싱 오류
- YAML 구조 및 들여쓰기 확인
- `node -e "const yaml = require('js-yaml'); const fs = require('fs'); console.log(yaml.load(fs.readFileSync('config/webhooks.yaml', 'utf8')))"` 실행하여 검증

### "기본 웹훅이 설정되어 있지 않습니다"
- `mattermost.set_default` 도구로 기본 채널 지정
- 또는 `config/webhooks.yaml`의 `default_channel` 설정

### HTTP 4xx/5xx 반환
- 웹훅 URL 확인
- Mattermost 서버 접근 권한 확인
- 웹훅 활성화 상태 확인

### Claude Desktop 연결 실패
- Claude Desktop 로그 확인: `%APPDATA%\Claude\logs\mcp-server-mattermost-s-mcp.log`
- Node.js 절대 경로 확인
- index.js 절대 경로 확인
- config/webhooks.yaml 파일 존재 확인

## 기술 스택

- **Node.js**: JavaScript 런타임
- **@modelcontextprotocol/sdk**: 공식 MCP SDK
- **js-yaml**: YAML 파서

## 향후 계획

- [ ] 테스트 스크린샷 추가 (`docs/images/`)
- [ ] 첨부파일 전송 기능
- [ ] 재시도 로직
- [ ] 타임아웃 설정

## 관련 문서

- [설치 가이드](../INSTALL.md)
- [사용 방법](../USAGE.md)
- [메인 README](../README.md)
