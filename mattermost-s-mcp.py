#!/usr/bin/env python3
"""mattermost-s-mcp: Model Context Protocol adapter for Mattermost webhooks."""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

try:
    import yaml  # type: ignore
except ImportError as exc:  # pragma: no cover
    sys.stderr.write("PyYAML 모듈이 필요합니다. `pip install pyyaml` 로 설치하세요.\n")
    raise SystemExit(1) from exc

try:
    import requests  # type: ignore
except ImportError as exc:  # pragma: no cover
    sys.stderr.write("requests 모듈이 필요합니다. `pip install requests` 로 설치하세요.\n")
    raise SystemExit(1) from exc

JSONRPC_VERSION = "2.0"
PROTOCOL_VERSION = "2024-11-05"  # MCP 프로토콜 버전
SERVER_NAME = "mattermost-s-mcp"
SERVER_VERSION = "0.1.0"

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG_PATH = BASE_DIR / "config" / "webhooks.yaml"
DEFAULT_MANIFEST_PATH = BASE_DIR / "mcp.json"

LIST_TOOL_NAME = "mattermost.list_webhooks"
SET_DEFAULT_TOOL_NAME = "mattermost.set_default"
SEND_TOOL_NAME = "mattermost.send_message"


class ConfigError(RuntimeError):
    """설정 파일 로딩 또는 검증 중 발생한 오류."""


class MessageSendError(RuntimeError):
    """웹훅 메시지 전송 실패."""


@dataclass
class WebhookEntry:
    channel: str
    url: str
    description: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {"channel": self.channel, "url": self.url}
        if self.description:
            data["description"] = self.description
        return data


class WebhookRegistry:
    """웹훅 설정을 로딩하고 관리한다."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._version = 1
        self._default_channel: Optional[str] = None
        self._entries: List[WebhookEntry] = []
        self.reload()

    def reload(self) -> None:
        if not self.path.exists():
            raise ConfigError(f"설정 파일이 존재하지 않습니다: {self.path}")
        with self.path.open("r", encoding="utf-8") as handle:
            raw = yaml.safe_load(handle) or {}
        if not isinstance(raw, dict):
            raise ConfigError("webhooks.yaml 구조가 올바르지 않습니다.")

        version = raw.get("version", 1)
        default_channel = raw.get("default_channel")
        raw_webhooks = raw.get("webhooks", [])

        if not isinstance(raw_webhooks, list):
            raise ConfigError("webhooks 항목은 리스트여야 합니다.")

        entries: List[WebhookEntry] = []
        known_channels: set[str] = set()
        for item in raw_webhooks:
            if not isinstance(item, dict):
                raise ConfigError("webhooks 항목에 잘못된 값이 포함되어 있습니다.")
            channel = item.get("channel")
            url = item.get("url")
            description = item.get("description")
            if not isinstance(channel, str) or not channel.strip():
                raise ConfigError("channel 값이 비어 있습니다.")
            if not isinstance(url, str) or not url.startswith(("http://", "https://")):
                raise ConfigError(f"채널 {channel} 의 url 이 유효하지 않습니다.")
            if channel in known_channels:
                raise ConfigError(f"채널 {channel} 이 중복되었습니다.")
            known_channels.add(channel)
            entries.append(WebhookEntry(channel=channel, url=url, description=description))

        if default_channel is not None and default_channel not in known_channels:
            raise ConfigError("default_channel 이 webhooks 목록에 없습니다.")

        self._version = version
        self._default_channel = default_channel
        self._entries = entries

    def list_entries(self) -> List[WebhookEntry]:
        return list(self._entries)

    @property
    def default_channel(self) -> Optional[str]:
        return self._default_channel

    def _index(self) -> Dict[str, WebhookEntry]:
        return {entry.channel: entry for entry in self._entries}

    def resolve_channel(self, channel: Optional[str]) -> WebhookEntry:
        index = self._index()
        if channel:
            if channel not in index:
                raise ConfigError(f"등록되지 않은 채널입니다: {channel}")
            return index[channel]
        if self._default_channel and self._default_channel in index:
            return index[self._default_channel]
        raise ConfigError("기본 웹훅이 설정되어 있지 않습니다.")

    def set_default(self, channel: str) -> None:
        index = self._index()
        if channel not in index:
            raise ConfigError(f"등록되지 않은 채널입니다: {channel}")
        self._default_channel = channel
        self.save()

    def save(self) -> None:
        data = {
            "version": self._version,
            "default_channel": self._default_channel,
            "webhooks": [entry.to_dict() for entry in self._entries],
        }
        with self.path.open("w", encoding="utf-8") as handle:
            yaml.safe_dump(data, handle, allow_unicode=True, sort_keys=False)


class MessageSender:
    def __init__(self, timeout: float = 10.0) -> None:
        self.timeout = timeout

    def send(self, entry: WebhookEntry, text: str) -> None:
        if not text.strip():
            raise MessageSendError("메시지 본문이 비어 있습니다.")
        payload = {"text": text}
        try:
            response = requests.post(entry.url, json=payload, timeout=self.timeout)
        except requests.RequestException as exc:  # pragma: no cover
            masked = mask_webhook(entry.url)
            raise MessageSendError(f"웹훅 요청 실패 ({masked}): {exc}") from exc
        if response.status_code >= 400:
            masked = mask_webhook(entry.url)
            detail = response.text.strip()
            if len(detail) > 120:
                detail = detail[:117] + "..."
            raise MessageSendError(
                f"웹훅 응답 오류 {response.status_code} ({masked}): {detail or '본문 없음'}"
            )


def mask_webhook(url: str) -> str:
    token_marker = "/hooks/"
    if token_marker in url:
        prefix, token = url.split(token_marker, 1)
        if len(token) <= 4:
            masked_token = "*" * len(token)
        else:
            masked_token = token[:3] + "***" + token[-1:]
        return f"{prefix}{token_marker}{masked_token}"
    if len(url) <= 8:
        return "*" * len(url)
    return url[:4] + "***" + url[-2:]


class MCPServer:
    def __init__(self, registry: WebhookRegistry, manifest_path: Path) -> None:
        self.registry = registry
        self.sender = MessageSender()
        self.manifest_path = manifest_path
        self.instructions = (
            "Mattermost 웹훅으로 메시지를 전송하는 MCP입니다. `mattermost.list_webhooks`로 "
            "채널 목록을 확인하고, `mattermost.set_default`로 기본 채널을 지정한 뒤 "
            "`mattermost.send_message`로 메시지를 전송하세요."
        )
        self.tool_definitions = self._build_tool_definitions()

    def serve(self) -> None:
        while True:
            message = _read_message()
            if message is None:
                break
            try:
                if not isinstance(message, dict):
                    _write_error(None, -32600, "Invalid request")
                    continue
                if message.get("jsonrpc") != JSONRPC_VERSION:
                    _write_error(message.get("id"), -32600, "Invalid JSON-RPC version")
                    continue
                method = message.get("method")
                if not isinstance(method, str):
                    _write_error(message.get("id"), -32600, "Method must be a string")
                    continue
                if "id" in message:
                    response = self._handle_request(method, message.get("params"), message["id"])
                    if response is not None:
                        _write_response(message["id"], response)
                else:
                    self._handle_notification(method, message.get("params"))
            except SystemExit:
                raise
            except Exception as exc:  # pragma: no cover
                logging.exception("요청 처리 중 예외 발생")
                _write_error(message.get("id"), -32603, "Internal error", {"detail": str(exc)})

    def _handle_request(self, method: str, params: Any, request_id: Any) -> Optional[Dict[str, Any]]:
        if method == "initialize":
            return self._handle_initialize(params)
        if method == "tools/list":
            return self._handle_tools_list(params)
        if method == "tools/call":
            return self._handle_tools_call(params)
        if method == "ping":
            return {}
        if method == "get_manifest":
            return self._handle_get_manifest()
        _write_error(request_id, -32601, f"Unknown method: {method}")
        return None

    def _handle_notification(self, method: str, params: Any) -> None:
        if method == "notifications/initialized":
            logging.debug("클라이언트 초기화 완료 알림 수신")
        elif method == "notifications/progress":
            token = params.get("progressToken") if isinstance(params, dict) else None
            logging.debug("진행 상황 알림(%s) 무시", token)
        else:
            logging.debug("지원하지 않는 알림 무시: %s", method)

    def _handle_initialize(self, params: Any) -> Dict[str, Any]:
        client_info = params.get("clientInfo") if isinstance(params, dict) else {}
        client_protocol = params.get("protocolVersion") if isinstance(params, dict) else PROTOCOL_VERSION
        logging.info(
            "클라이언트 연결: %s %s (protocol: %s)",
            client_info.get("name", "unknown"),
            client_info.get("version", "unknown"),
            client_protocol,
        )
        return {
            "protocolVersion": client_protocol,  # 클라이언트 버전 그대로 반환
            "capabilities": {"tools": {}},
            "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
        }

    def _handle_tools_list(self, params: Any) -> Dict[str, Any]:
        logging.debug("tools/list 호출")
        return {"tools": self.tool_definitions}

    def _handle_tools_call(self, params: Any) -> Dict[str, Any]:
        if not isinstance(params, dict):
            raise ConfigError("tools/call 파라미터가 잘못되었습니다.")
        name = params.get("name")
        arguments = params.get("arguments") or {}
        try:
            if name == LIST_TOOL_NAME:
                return self._tool_list_webhooks()
            if name == SET_DEFAULT_TOOL_NAME:
                return self._tool_set_default(arguments)
            if name == SEND_TOOL_NAME:
                return self._tool_send_message(arguments)
            raise ConfigError(f"알 수 없는 툴입니다: {name}")
        except (ConfigError, MessageSendError) as exc:
            logging.warning("툴 실행 실패: %s", exc)
            return self._tool_text_result(str(exc), is_error=True)

    def _handle_get_manifest(self) -> Dict[str, Any]:
        if not self.manifest_path.exists():
            raise ConfigError("manifest 파일이 존재하지 않습니다.")
        with self.manifest_path.open("r", encoding="utf-8") as handle:
            manifest = json.load(handle)
        return manifest

    def _tool_list_webhooks(self) -> Dict[str, Any]:
        self.registry.reload()
        payload = {
            "default": self.registry.default_channel,
            "channels": [
                {"channel": entry.channel, "description": entry.description or ""}
                for entry in self.registry.list_entries()
            ],
        }
        return self._tool_text_result(json.dumps(payload, ensure_ascii=False, indent=2))

    def _tool_set_default(self, arguments: Any) -> Dict[str, Any]:
        if not isinstance(arguments, dict):
            raise ConfigError("set_default 인자가 잘못되었습니다.")
        channel = arguments.get("channel")
        if not isinstance(channel, str) or not channel.strip():
            raise ConfigError("channel 인자가 필요합니다.")
        self.registry.reload()
        self.registry.set_default(channel)
        message = f"기본 채널이 '{channel}' 으로 설정되었습니다."
        return self._tool_text_result(message)

    def _tool_send_message(self, arguments: Any) -> Dict[str, Any]:
        if not isinstance(arguments, dict):
            raise ConfigError("send_message 인자가 잘못되었습니다.")
        text = arguments.get("text")
        channel = arguments.get("channel")
        if not isinstance(text, str) or not text.strip():
            raise ConfigError("text 인자가 필요합니다.")
        if channel is not None and not isinstance(channel, str):
            raise ConfigError("channel 인자는 문자열이어야 합니다.")
        self.registry.reload()
        target = self.registry.resolve_channel(channel)
        masked = mask_webhook(target.url)
        self.sender.send(target, text)
        message = (
            f"채널 '{target.channel}' 에 메시지를 전송했습니다. "
            f"(웹훅: {masked})"
        )
        return self._tool_text_result(message)

    @staticmethod
    def _tool_text_result(text: str, *, is_error: bool = False) -> Dict[str, Any]:
        return {
            "content": [{"type": "text", "text": text}],
            "isError": is_error or None,
        }

    @staticmethod
    def _build_tool_definitions() -> List[Dict[str, Any]]:
        return [
            {
                "name": LIST_TOOL_NAME,
                "description": "등록된 Mattermost 웹훅 채널 목록을 확인합니다.",
                "inputSchema": {"type": "object", "properties": {}},
            },
            {
                "name": SET_DEFAULT_TOOL_NAME,
                "description": "지정한 채널을 기본 웹훅으로 설정합니다.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "channel": {
                            "type": "string",
                            "description": "기본으로 설정할 채널명",
                        }
                    },
                    "required": ["channel"],
                },
            },
            {
                "name": SEND_TOOL_NAME,
                "description": "기본 또는 지정한 채널 웹훅으로 메시지를 전송합니다.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "text": {
                            "type": "string",
                            "description": "전송할 메시지 텍스트",
                        },
                        "channel": {
                            "type": "string",
                            "description": "메시지를 보낼 채널명 (선택)",
                        },
                    },
                    "required": ["text"],
                },
            },
        ]


def _read_message() -> Optional[Dict[str, Any]]:
    headers: Dict[str, str] = {}
    while True:
        line = sys.stdin.buffer.readline()
        if not line:
            return None
        # 빈 라인(헤더 종료)을 찾습니다
        if line.strip() == b"":
            break
        header_line = line.decode("ascii", errors="ignore").strip()
        if not header_line or ":" not in header_line:
            continue
        key, value = header_line.split(":", 1)
        headers[key.strip().lower()] = value.strip()

    length_str = headers.get("content-length")
    if length_str is None:
        return None
    try:
        length = int(length_str)
    except ValueError:
        return None
    body = sys.stdin.buffer.read(length)
    if not body:
        return None
    try:
        return json.loads(body.decode("utf-8"))
    except json.JSONDecodeError as e:  # pragma: no cover
        logging.error(f"JSON 파싱 실패: {e}, 본문: {body[:200]}")
        return None


def _write_response(request_id: Any, result: Dict[str, Any]) -> None:
    payload = {"jsonrpc": JSONRPC_VERSION, "id": request_id, "result": _strip_none(result)}
    _write_json(payload)


def _write_error(request_id: Any, code: int, message: str, data: Optional[Dict[str, Any]] = None) -> None:
    error_body = {"code": code, "message": message}
    if data:
        error_body["data"] = data
    payload = {"jsonrpc": JSONRPC_VERSION, "id": request_id, "error": error_body}
    _write_json(payload)


def _write_json(payload: Dict[str, Any]) -> None:
    encoded = json.dumps(_strip_none(payload), ensure_ascii=False).encode("utf-8")
    sys.stdout.buffer.write(f"Content-Length: {len(encoded)}\r\n\r\n".encode("ascii"))
    sys.stdout.buffer.write(encoded)
    sys.stdout.buffer.flush()


def _strip_none(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _strip_none(v) for k, v in obj.items() if v is not None}
    if isinstance(obj, list):
        return [_strip_none(v) for v in obj]
    return obj


def parse_args(argv: Optional[Iterable[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Mattermost 웹훅 MCP")
    parser.add_argument("--config", help="설정 파일 경로")
    parser.add_argument("--log-level", default=os.environ.get("MATTERMOST_MCP_LOG_LEVEL", "INFO"))

    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("list", help="등록된 웹훅 목록 출력")

    set_default_parser = subparsers.add_parser("set-default", help="기본 채널 설정")
    set_default_parser.add_argument("channel", help="기본으로 설정할 채널명")

    send_parser = subparsers.add_parser("send", help="메시지 전송")
    send_parser.add_argument("--text", required=True, help="전송할 메시지")
    send_parser.add_argument("--channel", help="전송할 채널명")

    send_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="요청만 출력하고 실제 전송은 수행하지 않습니다.",
    )

    return parser.parse_args(argv)


def configure_logging(level_text: str) -> None:
    # MCP는 STDIO를 사용하므로 로그를 파일로 출력합니다
    log_file = os.environ.get("MATTERMOST_MCP_LOG_FILE", "/tmp/mattermost-s-mcp.log")
    logging.basicConfig(
        level=getattr(logging, level_text.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(message)s",
        filename=log_file,
        filemode="a",
    )


def resolve_config_path(args: argparse.Namespace) -> Path:
    if args.config:
        return Path(args.config).expanduser().resolve()
    env_value = os.environ.get("MATTERMOST_MCP_CONFIG")
    if env_value:
        return Path(env_value).expanduser().resolve()
    return DEFAULT_CONFIG_PATH


def cli_list(registry: WebhookRegistry) -> None:
    entries = registry.list_entries()
    if not entries:
        print("등록된 웹훅이 없습니다.")
        return
    print("채널명\t기본여부\t설명")
    for entry in entries:
        marker = "*" if registry.default_channel == entry.channel else ""
        desc = entry.description or ""
        print(f"{entry.channel}\t{marker}\t{desc}")


def cli_set_default(registry: WebhookRegistry, channel: str) -> None:
    registry.set_default(channel)
    print(f"기본 채널이 '{channel}' 으로 설정되었습니다.")


def cli_send(registry: WebhookRegistry, text: str, channel: Optional[str], dry_run: bool) -> None:
    entry = registry.resolve_channel(channel)
    masked = mask_webhook(entry.url)
    if dry_run:
        print(f"[DRY-RUN] {entry.channel} ({masked}) -> {text}")
        return
    sender = MessageSender()
    sender.send(entry, text)
    print(f"채널 '{entry.channel}' 으로 메시지를 전송했습니다. (웹훅: {masked})")


def main(argv: Optional[Iterable[str]] = None) -> None:
    args = parse_args(argv)
    config_path = resolve_config_path(args)

    if args.command:
        # CLI 모드: 일반 로그
        configure_logging(args.log_level)
        registry = WebhookRegistry(config_path)
        if args.command == "list":
            cli_list(registry)
            return
        if args.command == "set-default":
            cli_set_default(registry, args.channel)
            return
        if args.command == "send":
            cli_send(registry, args.text, args.channel, args.dry_run)
            return
        raise SystemExit(f"알 수 없는 명령입니다: {args.command}")

    # MCP 서버 모드: 로그는 나중에 (설정 파일 로딩 후)
    try:
        configure_logging(args.log_level)
        registry = WebhookRegistry(config_path)
        server = MCPServer(registry, DEFAULT_MANIFEST_PATH)
        server.serve()
    except Exception as e:
        # stderr로 에러 출력 (Claude Desktop이 볼 수 있도록)
        import traceback
        sys.stderr.write(f"FATAL ERROR: {e}\n")
        sys.stderr.write(traceback.format_exc())
        sys.stderr.flush()
        raise


if __name__ == "__main__":
    main()
