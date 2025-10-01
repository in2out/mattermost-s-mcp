#!/usr/bin/env node

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import yaml from "js-yaml";
import { readFileSync, writeFileSync } from "fs";
import { fileURLToPath } from "url";
import { dirname, join } from "path";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const CONFIG_PATH =
  process.env.MATTERMOST_MCP_CONFIG ||
  join(__dirname, "config", "webhooks.yaml");

class MattermostMCP {
  constructor() {
    this.server = new Server(
      {
        name: "mattermost-s-mcp",
        version: "0.1.0",
      },
      {
        capabilities: {
          tools: {},
        },
      }
    );

    this.setupHandlers();
    this.setupErrorHandling();
  }

  loadConfig() {
    try {
      const fileContents = readFileSync(CONFIG_PATH, "utf8");
      const config = yaml.load(fileContents);

      if (!config || !config.webhooks || !Array.isArray(config.webhooks)) {
        throw new Error("Invalid config structure");
      }

      return config;
    } catch (error) {
      throw new Error(`Failed to load config: ${error.message}`);
    }
  }

  saveConfig(config) {
    try {
      const yamlStr = yaml.dump(config, { noRefs: true, sortKeys: false });
      writeFileSync(CONFIG_PATH, yamlStr, "utf8");
    } catch (error) {
      throw new Error(`Failed to save config: ${error.message}`);
    }
  }

  setupErrorHandling() {
    this.server.onerror = (error) => {
      console.error("[MCP Error]", error);
    };

    process.on("SIGINT", async () => {
      await this.server.close();
      process.exit(0);
    });
  }

  setupHandlers() {
    this.server.setRequestHandler(ListToolsRequestSchema, async () => ({
      tools: [
        {
          name: "mattermost_list_webhooks",
          description: "등록된 Mattermost 웹훅 채널 목록을 확인합니다.",
          inputSchema: {
            type: "object",
            properties: {},
          },
        },
        {
          name: "mattermost_set_default",
          description: "지정한 채널을 기본 웹훅으로 설정합니다.",
          inputSchema: {
            type: "object",
            properties: {
              channel: {
                type: "string",
                description: "기본으로 설정할 채널명",
              },
            },
            required: ["channel"],
          },
        },
        {
          name: "mattermost_send_message",
          description: "기본 또는 지정한 채널 웹훅으로 메시지를 전송합니다.",
          inputSchema: {
            type: "object",
            properties: {
              text: {
                type: "string",
                description: "전송할 메시지 텍스트",
              },
              channel: {
                type: "string",
                description: "메시지를 보낼 채널명 (선택)",
              },
            },
            required: ["text"],
          },
        },
      ],
    }));

    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      const { name, arguments: args } = request.params;

      try {
        switch (name) {
          case "mattermost_list_webhooks":
            return await this.listWebhooks();

          case "mattermost_set_default":
            return await this.setDefault(args.channel);

          case "mattermost_send_message":
            return await this.sendMessage(args.text, args.channel);

          default:
            throw new Error(`Unknown tool: ${name}`);
        }
      } catch (error) {
        return {
          content: [
            {
              type: "text",
              text: `Error: ${error.message}`,
            },
          ],
          isError: true,
        };
      }
    });
  }

  async listWebhooks() {
    const config = this.loadConfig();
    const result = {
      default: config.default_channel || null,
      channels: config.webhooks.map((w) => ({
        channel: w.channel,
        description: w.description || "",
      })),
    };

    return {
      content: [
        {
          type: "text",
          text: JSON.stringify(result, null, 2),
        },
      ],
    };
  }

  async setDefault(channel) {
    if (!channel || typeof channel !== "string") {
      throw new Error("channel 인자가 필요합니다.");
    }

    const config = this.loadConfig();
    const channelExists = config.webhooks.some((w) => w.channel === channel);

    if (!channelExists) {
      throw new Error(`등록되지 않은 채널입니다: ${channel}`);
    }

    config.default_channel = channel;
    this.saveConfig(config);

    return {
      content: [
        {
          type: "text",
          text: `기본 채널이 '${channel}' 으로 설정되었습니다.`,
        },
      ],
    };
  }

  async sendMessage(text, channel) {
    if (!text || typeof text !== "string" || !text.trim()) {
      throw new Error("text 인자가 필요합니다.");
    }

    const config = this.loadConfig();
    let webhook;

    if (channel) {
      webhook = config.webhooks.find((w) => w.channel === channel);
      if (!webhook) {
        throw new Error(`등록되지 않은 채널입니다: ${channel}`);
      }
    } else if (config.default_channel) {
      webhook = config.webhooks.find(
        (w) => w.channel === config.default_channel
      );
      if (!webhook) {
        throw new Error("기본 웹훅이 설정되어 있지 않습니다.");
      }
    } else {
      throw new Error("기본 웹훅이 설정되어 있지 않습니다.");
    }

    // Send webhook request
    try {
      const response = await fetch(webhook.url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ text }),
      });

      if (!response.ok) {
        throw new Error(
          `웹훅 응답 오류 ${response.status}: ${await response.text()}`
        );
      }

      const maskedUrl = this.maskWebhookUrl(webhook.url);
      return {
        content: [
          {
            type: "text",
            text: `채널 '${webhook.channel}' 에 메시지를 전송했습니다. (웹훅: ${maskedUrl})`,
          },
        ],
      };
    } catch (error) {
      throw new Error(`웹훅 요청 실패: ${error.message}`);
    }
  }

  maskWebhookUrl(url) {
    const tokenMarker = "/hooks/";
    if (url.includes(tokenMarker)) {
      const [prefix, token] = url.split(tokenMarker);
      if (token.length <= 4) {
        return `${prefix}${tokenMarker}${"*".repeat(token.length)}`;
      }
      return `${prefix}${tokenMarker}${token.substring(0, 3)}***${token.slice(
        -1
      )}`;
    }
    if (url.length <= 8) {
      return "*".repeat(url.length);
    }
    return `${url.substring(0, 4)}***${url.slice(-2)}`;
  }

  async run() {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    console.error("Mattermost MCP server running on stdio");
  }
}

const server = new MattermostMCP();
server.run().catch(console.error);
