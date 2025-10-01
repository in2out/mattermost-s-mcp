# Mattermost MCP 사용 방법

## Claude Desktop 설정

### 1. 설정 파일 위치
Windows: `C:\Users\{사용자명}\AppData\Roaming\Claude\claude_desktop_config.json`

### 2. 설정 파일 내용
```json
{
  "mcpServers": {
    "mattermost-s-mcp": {
      "command": "python",
      "args": ["C:\\Users\\in2out\\mcp\\mattermost-s-mcp\\mattermost-s-mcp.py"],
      "env": {
        "MATTERMOST_MCP_CONFIG": "C:\\Users\\in2out\\mcp\\mattermost-s-mcp\\config\\webhooks.yaml"
      }
    }
  }
}
```

### 3. Claude Desktop 재시작
- 설정을 적용하려면 Claude Desktop을 완전히 종료하고 다시 시작

## Claude Desktop에서 사용하기

### 연결 확인
Claude Desktop을 다시 시작하면 자동으로 MCP 서버에 연결됩니다.
- 하단에 MCP 아이콘/상태 표시
- 설정에서 MCP 서버 목록 확인 가능

### 사용 예시

#### 1. 등록된 채널 목록 확인
```
Mattermost 채널 목록 보여줘
```

#### 2. 기본 채널로 메시지 전송
```
Mattermost로 "테스트 완료했습니다!" 메시지 보내줘
```

#### 3. 특정 채널로 메시지 전송
```
Mattermost AI비서 채널로 "작업 완료" 메시지 보내줘
```

#### 4. 기본 채널 변경
```
Mattermost 기본 채널을 general로 변경해줘
```

## 사용 가능한 도구

Claude가 자동으로 다음 3가지 도구를 사용할 수 있습니다:

### mattermost.list_webhooks
등록된 Mattermost 웹훅 채널 목록을 확인합니다.

### mattermost.set_default
지정한 채널을 기본 웹훅으로 설정합니다.
- 파라미터: `channel` (채널명)

### mattermost.send_message
기본 또는 지정한 채널 웹훅으로 메시지를 전송합니다.
- 파라미터:
  - `text` (필수): 전송할 메시지 텍스트
  - `channel` (선택): 메시지를 보낼 채널명

## CLI 모드 사용

MCP 서버 없이 명령줄에서 직접 사용할 수도 있습니다.

### 채널 목록 확인
```bash
python mattermost-s-mcp.py list
```

### 메시지 전송
```bash
python mattermost-s-mcp.py send --text "테스트 메시지"
```

### 특정 채널로 전송
```bash
python mattermost-s-mcp.py send --text "테스트 메시지" --channel "AI비서"
```

### 기본 채널 설정
```bash
python mattermost-s-mcp.py set-default general
```

### 전송 테스트 (실제 전송 안 함)
```bash
python mattermost-s-mcp.py send --text "테스트" --dry-run
```

## 트러블슈팅

### 로그 확인
Windows: `/tmp/mattermost-s-mcp.log`

로그 레벨 변경:
```json
{
  "mcpServers": {
    "mattermost-s-mcp": {
      "command": "python",
      "args": ["C:\\Users\\in2out\\mcp\\mattermost-s-mcp\\mattermost-s-mcp.py"],
      "env": {
        "MATTERMOST_MCP_CONFIG": "C:\\Users\\in2out\\mcp\\mattermost-s-mcp\\config\\webhooks.yaml",
        "MATTERMOST_MCP_LOG_LEVEL": "DEBUG"
      }
    }
  }
}
```

### 설정 파일 확인
웹훅 URL과 채널이 올바르게 설정되어 있는지 확인:
```bash
python mattermost-s-mcp.py list
```

### MCP 서버 수동 테스트
```bash
python test_mcp.py
```
