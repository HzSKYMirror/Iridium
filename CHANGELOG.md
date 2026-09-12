# Changelog

本文件记录 Iridium 的重要变更。

## [26.9.4] - 2026-09-13

### Added
- 操作日志：`!!share` / `!!hat` / `!!head` / `!!c` 成功时写入 MCDR 控制台（`[Iridium] ...`）

## [26.9.3] - 2026-09-13

### Fixed
- `!!share` / `!!hat` / `!!head`：`info.version` 若为字符串时比较崩溃（`Cannot compare Version and str`）
- `!!c`：命令回调少绑定 `server` 导致 `do_calc() missing ... context`

## [26.9.2] - 2026-09-13

### Fixed
- 语言文件 YAML 解析失败（值中含 `:` 未加引号导致 `mapping values are not allowed`）
- 进服事件名错误：`PLAYER_JOIN` → `PLAYER_JOINED`（否则插件 on_load 失败）

## [26.9.1] - 2026-09-13

### Added
- `!!share`：展示主手物品（悬停完整数据，1.16+ 点击复制，可选提示音）
- `!!hat`：主手物品与头部装备互换（需 RCON）
- `!!head [player]`：获取一个玩家头颅，支持冷却与权限
- `!!c <expression>`：游戏内四则运算计算器（AST 白名单，零依赖）
- 进服 MOTD：开服天数、自定义文案、可点击链接、`§` 颜色
- 进服命令提示（可点击填入聊天框）
- 按 Minecraft 版本分支；不支持的功能会明确提示

### Security
- 玩家名统一清洗为 `[A-Za-z0-9_]` 并限长后再拼进 `/give`、`data get`、`item replace`
- 控制台命令去除换行，防止拆成多行二次执行
- tellraw 对物品 SNBT 做 JSON 转义与长度截断
- MOTD 链接仅允许 `http://` / `https://`
