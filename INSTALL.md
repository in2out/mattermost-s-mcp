# Mattermost-S-MCP 설치 가이드

## 1. 요구사항

- Python 3.10 이상
- pip

## 2. 설치

```bash
# 1. 저장소 클론 또는 다운로드
git clone <repository-url> mattermost-s-mcp
cd mattermost-s-mcp/public

# 2. 의존성 설치
pip install -r requirements.txt

# 3. 설정 파일 수정
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

## 4. Claude Code에 등록

Claude Code의 설정 파일에 다음과 같이 추가합니다:

**위치**: `~/.config/claude-code/config.json` (Linux/Mac) 또는 `%APPDATA%\claude-code\config.json` (Windows)

```json
{
  "mcpServers": {
    "mattermost-s-mcp": {
      "command": "python3",
      "args": [
        "/절대/경로/mattermost-s-mcp/public/mattermost-s-mcp.py"
      ],
      "env": {
        "MATTERMOST_MCP_LOG_FILE": "/tmp/mattermost-s-mcp.log"
      }
    }
  }
}
```

**중요**:
- `command`는 `python3` 또는 `python` (시스템에 따라)
- `args`의 경로는 **절대 경로**로 지정해야 합니다
- 로그는 `/tmp/mattermost-s-mcp.log`에 저장됩니다

## 5. 테스트

### 5.1 CLI 테스트

```bash
# 웹훅 목록 확인
python3 mattermost-s-mcp.py list

# 메시지 전송 (dry-run)
python3 mattermost-s-mcp.py send --text "테스트 메시지" --dry-run

# 실제 메시지 전송
python3 mattermost-s-mcp.py send --text "테스트 메시지"
```

### 5.2 MCP 프로토콜 테스트

```bash
# 상위 디렉터리에서
python3 test-mcp.py
```

### 5.3 Claude Code에서 테스트

Claude Code를 재시작한 후:

1. `mattermost.list_webhooks` 도구가 보이는지 확인
2. "Mattermost에 테스트 메시지를 보내줘" 라고 요청

## 6. 문제 해결

### "server disconnected" 에러

로그 파일을 확인하세요:
```bash
tail -f /tmp/mattermost-s-mcp.log
```

일반적인 원인:
1. Python 경로가 잘못됨 → `which python3` 결과를 `command`에 사용
2. 스크립트 경로가 상대 경로 → 절대 경로로 변경
3. 설정 파일이 없음 → `config/webhooks.yaml` 존재 확인
4. 의존성 미설치 → `pip install -r requirements.txt` 실행

### 메시지 전송 실패

1. 웹훅 URL이 올바른지 확인
2. Mattermost 서버가 접근 가능한지 확인
3. 웹훅이 활성화되어 있는지 확인

### 로그 레벨 변경

환경 변수로 조정:
```json
{
  "mcpServers": {
    "mattermost-s-mcp": {
      "env": {
        "MATTERMOST_MCP_LOG_LEVEL": "DEBUG"
      }
    }
  }
}
```
