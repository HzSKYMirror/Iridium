# Changelog / 更新日志

本文件记录 Iridium 的重要变更。  
This file records notable changes to Iridium.

---

## [26.9.14] - 2026-09-14

### 修复 / Fixed
- 删除配置后重载可正确重新生成；配置写入 MCDR 数据目录
- Deleting config then reloading correctly recreates it; config stored under the MCDR data folder

### 变更 / Changed
- 配置格式为 **YAML**：`config/iridium/iridium.yml`（`#` 原生注释）
- Config format is **YAML**: `config/iridium/iridium.yml` (native `#` comments)
- 自动从旧 JSON（`config/iridium.json` 或 `config/iridium/iridium.json`）迁移
- Auto-migrates from legacy JSON configs
- `motd_start_day` 默认为配置生成当天（YYYY-MM-DD）
- `motd_start_day` defaults to the config creation date
- 去掉 MOTD 标题「服务器信息」/「Server Info」
- Removed the MOTD header title
- 默认 QQ 群可点击链接 `https://skymirror.top/qq`
- Default QQ group is a clickable link to `https://skymirror.top/qq`
- 进服命令提示文案去掉「已启用 Iridium」
- Join tip header no longer says “Iridium is enabled”

### 新增 / Added
- 英文文档 `README_en.md`
- English documentation `README_en.md`

### 清理 / Cleanup
- 移除未使用的常量、翻译键与导入
- Removed unused constants, translation keys, and imports

---

## [26.9.13] - 2026-09-13

### 新增 / Added
- 首次启动自动生成带中文注释的 `config/iridium.json`
- On first load, generate a commented `config/iridium.json`
- 配置文件支持 `//` 行注释
- Config file supports `//` line comments

### 变更 / Changed
- 提交信息改为中文
- Commit messages rewritten in Chinese
- 清理历史 Release，仅保留当前版本
- Cleaned old Releases; keep only the current version

---

## [26.9.8] - 2026-09-13

### 变更 / Changed
- `!!share`：去掉「点击复制完整数据」，仅保留物品名 + 悬停预览
- `!!share`: removed the copy-to-clipboard button; name + hover only

---

## [26.9.7] - 2026-09-13

### 修复 / Fixed
- `!!share`：无 NBT 改名时 fallback 为 ID 美化名（如 `Time Twister Wireless`）
- `!!share`: humanized ID fallback when the item has no NBT custom name

---

## [26.9.6] - 2026-09-13

### 修复 / Fixed
- `!!share`：使用客户端 `translate` 组件显示本地化名
- `!!share`: use client `translate` component for localized names
- `!!share`：提示音在玩家位置播放
- `!!share`: play sound at the player to avoid “too far away”

---

## [26.9.5] - 2026-09-13

### 修复 / Fixed
- `!!hat`（1.17+）：副手缓冲交换，避免复杂 NBT 重建失败导致物品消失
- `!!hat` (1.17+): offhand-buffer swap so complex NBT cannot wipe items
- `!!share`：优先显示自定义名 / translate
- `!!share`: prefer custom name / translate over raw item id

---

## [26.9.4] - 2026-09-13

### 新增 / Added
- 操作日志写入 MCDR 控制台
- Command operations logged to the MCDR console

---

## [26.9.3] - 2026-09-13

### 修复 / Fixed
- 版本比较在 `str` / `Version` 之间崩溃
- Version comparison crash between `str` and `Version`
- `!!c` 回调缺少 `server` 绑定
- `!!c` callback missing `server` binding

---

## [26.9.2] - 2026-09-13

### 修复 / Fixed
- 语言文件 YAML 因值中冒号未加引号而解析失败
- Language YAML failed when values contained unquoted colons
- 进服事件名：`PLAYER_JOIN` → `PLAYER_JOINED`
- Join event name: `PLAYER_JOIN` → `PLAYER_JOINED`

---

## [26.9.1] - 2026-09-13

### 新增 / Added
- `!!share` / `!!hat` / `!!head` / `!!c`、进服 MOTD 与命令提示
- `!!share` / `!!hat` / `!!head` / `!!c`, join MOTD and command tips
- 按 Minecraft 版本分支；不支持的功能会提示
- Minecraft-version branching with clear prompts when unsupported

### 安全 / Security
- 玩家名清洗、命令去换行、tellraw 转义、链接仅 http(s)
- Name sanitization, newline stripping, tellraw escaping, http(s)-only links
