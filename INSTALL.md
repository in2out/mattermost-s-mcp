# Mattermost-S-MCP 설치 가이드

## 1. 요구사항

- Node.js 18 이상
- npm

## 2. 설치

```bash
# 1. 저장소 클론 또는 다운로드
git clone <repository-url> mattermost-s-mcp
cd mattermost-s-mcp

# 2. 의존성 설치
npm install

# 3. 설정 파일 수정
# Windows
notepad config\webhooks.yaml

# Linux/Mac
vi config/webhooks.yaml
```

## 3. 설정 파일 (config/webhooks.yaml)

```yaml
version: 1
default_channel: your-channel-name
webhooks:
  - channel: your-channel-name
    url: https://your-mattermost-server/hooks/your-webhook-token
    description: 설명
```

**주의사항**:
- `channel`은 각각 고유해야 합니다
- `default_channel`은 webhooks 목록에 있어야 합니다
- URL은 `http://` 또는 `https://`로 시작해야 합니다

## 4. Claude Desktop에 등록

Claude Desktop의 설정 파일에 다음과 같이 추가합니다:

**설정 파일 위치**:
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

**설정 내용**:

```json
{
  "mcpServers": {
    "mattermost-s-mcp": {
      "command": "node",
      "args": [
        "C:\\Users\\your-username\\mcp\\mattermost-s-mcp\\index.js"
      ],
      "env": {
        "MATTERMOST_MCP_CONFIG": "C:\\Users\\your-username\\mcp\\mattermost-s-mcp\\config\\webhooks.yaml"
      }
    }
  }
}
```

**중요**:
- **절대 경로** 사용 필수
- Windows에서는 백슬래시(`\`)를 두 번(`\\`) 사용
- Node.js 실행 파일의 절대 경로를 확인하려면:
  - Windows: `where node`
  - Linux/Mac: `which node`

## 5. 테스트

### 5.1 서버 시작 테스트

```bash
node index.js
```

정상 시작 시 다음 메시지가 stderr에 출력됩니다:
```
Mattermost MCP server running on stdio
```

`Ctrl+C`로 중단하세요.

### 5.2 Claude Desktop에서 테스트

1. Claude Desktop을 **완전히 종료**합니다
2. Claude Desktop을 다시 시작합니다
3. 새 대화에서 다음과 같이 요청합니다:

```
Mattermost 채널 목록 보여줘
```

채널 목록이 JSON 형식으로 표시되면 성공입니다.

### 5.3 메시지 전송 테스트

```
Mattermost로 "테스트 메시지" 보내줘
```

Mattermost 채널에 메시지가 도착하면 성공입니다.

## 6. 문제 해결

### "server disconnected" 에러

**원인과 해결 방법**:

1. **Node.js 경로 문제**
   ```bash
   # Node.js 경로 확인
   which node  # Linux/Mac
   where node  # Windows

   # 설정 파일의 command에 절대 경로 사용
   "command": "/usr/local/bin/node"
   ```

2. **스크립트 경로가 상대 경로**
   - `args`에 절대 경로 사용 확인
   - 예: `["C:\\Users\\...\\index.js"]`

3. **설정 파일이 없음**
   ```bash
   # 파일 존재 확인
   ls config/webhooks.yaml
   ```

4. **의존성 미설치**
   ```bash
   npm install
   ```

### Claude Desktop 로그 확인

**로그 파일 위치**:
- **Windows**: `%APPDATA%\Claude\logs\mcp-server-mattermost-s-mcp.log`
- **macOS**: `~/Library/Logs/Claude/mcp-server-mattermost-s-mcp.log`
- **Linux**: `~/.config/Claude/logs/mcp-server-mattermost-s-mcp.log`

```bash
# Windows
type "%APPDATA%\Claude\logs\mcp-server-mattermost-s-mcp.log"

# Linux/Mac
tail -f ~/Library/Logs/Claude/mcp-server-mattermost-s-mcp.log
```

### 메시지 전송 실패

1. **웹훅 URL 확인**
   - Mattermost 서버 설정에서 웹훅 URL 복사
   - YAML 파일에 정확히 입력되었는지 확인

2. **네트워크 연결 확인**
   ```bash
   curl -X POST https://your-mattermost-server/hooks/your-token \
     -H "Content-Type: application/json" \
     -d '{"text":"테스트"}'
   ```

3. **웹훅 활성화 확인**
   - Mattermost 관리자 콘솔에서 웹훅이 활성화되어 있는지 확인

### YAML 파싱 에러

```bash
# YAML 구조 검증
node -e "const yaml = require('js-yaml'); const fs = require('fs'); console.log(yaml.load(fs.readFileSync('config/webhooks.yaml', 'utf8')))"
```

YAML 들여쓰기와 구조가 올바른지 확인하세요.

## 7. 고급 설정

### 환경 변수로 설정 파일 위치 변경

```json
{
  "mcpServers": {
    "mattermost-s-mcp": {
      "command": "node",
      "args": ["C:\\path\\to\\index.js"],
      "env": {
        "MATTERMOST_MCP_CONFIG": "C:\\custom\\path\\to\\webhooks.yaml"
      }
    }
  }
}
```

### 여러 MCP 서버와 함께 사용

```json
{
  "mcpServers": {
    "mattermost-s-mcp": {
      "command": "node",
      "args": ["C:\\path\\to\\mattermost-s-mcp\\index.js"]
    },
    "another-mcp-server": {
      "command": "python",
      "args": ["C:\\path\\to\\another-server.py"]
    }
  }
}
```

## 8. 다음 단계

설치가 완료되었으면 [USAGE.md](./USAGE.md)에서 사용 방법을 확인하세요.
