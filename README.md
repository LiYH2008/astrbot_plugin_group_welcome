# AstrBot 群迎新与新好友欢迎

适配 **AstrBot v4.28.2**，主要面向 **OneBot v11（aiocqhttp）**。

## 功能

- 新成员入群时发送真正的 QQ `@` 消息和欢迎文本。
- 检测 `friend_add` 后自动给新好友发送私聊欢迎。
- 兼容部分实现的 `request_type=friend` 事件。
- 通过 AstrBot WebUI 配置群号、欢迎文本和新好友文本。
- 短时间重复事件自动去重。

## 安装

### 复制安装

1. 下载本仓库。
2. 将 `astrbot_plugin_group_welcome` 整个文件夹复制到 AstrBot 插件目录。
3. 重启 AstrBot，或在 WebUI 中重载插件。
4. 在插件配置页面保存配置。

### Git 安装

```bash
git clone https://github.com/LiYH2008/astrbot_plugin_group_welcome.git
```

## WebUI 配置

### 启用群迎新的群号

填写允许触发群迎新的群号。支持列表项，也支持在一个输入中使用英文逗号、中文逗号、分号或换行分隔，例如：

```text
123456,789012
```

只有填写的群号会触发群迎新；留空表示关闭群迎新。新好友欢迎不受此项影响。

### 入群欢迎文本

机器人会先 @ 新成员，再发送这里的文本。例如：

```text
欢迎加入本群！请先阅读群公告，祝大家聊天愉快～
```

### 新好友欢迎文本

检测到新好友事件后发送的私聊文本。例如：

```text
你好，已成功添加好友！很高兴认识你～
```

文本支持换行，保存后即可生效。

## OneBot v11 注意事项

1. 确认 AstrBot 已连接 OneBot v11（aiocqhttp）。
2. 机器人需要拥有目标群的发言权限。
3. 入群消息通过 `send_group_msg` 发送，会产生真正的 QQ @ 消息。
4. 新好友消息通过 `send_private_msg` 发送；其它平台需要能转换为 AstrBot 通用事件。

## 故障排查

**入群没有欢迎：**检查群号是否填写正确、目标群是否在列表中，并查看 AstrBot 和 OneBot 日志。

**新好友没有欢迎：**确认适配器产生了 `friend_add` 或 `request_type=friend` 事件，并确认机器人允许主动私聊。

## 文件说明

| 文件 | 作用 |
| --- | --- |
| `main.py` | 插件运行代码 |
| `_conf_schema.json` | WebUI 配置定义 |
| `metadata.yaml` | 插件元数据 |
| `README.md` | 使用教程 |
| `LICENSE` | AGPL-3.0 开源协议 |

## 开源协议

本项目采用 [GNU Affero General Public License v3.0](LICENSE)。

