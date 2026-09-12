# 提交到 MCDReforged 官方插件库

官方库：https://github.com/MCDReforged/PluginCatalogue  
贡献指南：https://github.com/MCDReforged/PluginCatalogue/blob/master/CONTRIBUTING_zh_cn.md

## 当前进度

仓库：https://github.com/HzSKYMirror/Iridium  

| 步骤 | 状态 |
|------|------|
| 公开 GitHub 仓库 | 已创建（当前可能仍为空，需推送） |
| `plugin_info.json` | 已写好（`catalogue/plugin_info.json`） |
| GitHub Release + `.mcdr` 附件 | **待完成** |
| 官方库 PR | **待完成** |

## 硬性前提

1. **公开 GitHub 仓库**（官方脚本只认 GitHub，不认 git.skymirror.top）
2. **GitHub Release 标签正确，附件为 `.mcdr`**  
   建议 Tag：`v26.9.1`；附件：`Iridium.mcdr`
3. **根目录有 `README.md`**（已有）
4. **许可**：官方强烈建议 OSI 开源许可；专有许可可提但审阅更慢，且提交即授权社区从 GitHub Releases 下载使用
5. **一个 PR 只加一个插件**

## 提交步骤

### 1. 推送源码到 GitHub

```bash
cd /Users/l3126596029/Code/MCDR_plg/Iridium
git remote add github https://github.com/HzSKYMirror/Iridium.git
git push -u github main
```

### 2. 在 GitHub 发 Release

- Tag：`v26.9.1`
- 附件：本地执行 `./pack.sh` 得到的 `Iridium.mcdr`

### 3. 向官方库提 PR

1. Fork https://github.com/MCDReforged/PluginCatalogue  
2. 新建文件：`plugins/iridium/plugin_info.json`  
   内容直接使用本仓库 `catalogue/plugin_info.json`  
3. 向 `MCDReforged/PluginCatalogue` 的 `master` 发起 Pull Request  

### PR 标题

```text
Add plugin: iridium
```

### PR 描述

```markdown
## Plugin

- ID: `iridium`
- Name: Iridium
- Repository: https://github.com/HzSKYMirror/Iridium
- Release: https://github.com/HzSKYMirror/Iridium/releases/tag/v26.9.1
- Labels: `tool`

## Summary

物品展示（!!share）、戴头（!!hat）、获取玩家头颅（!!head）、
游戏内计算器（!!c）、进服 MOTD 与命令提示。

面向 Minecraft 1.7.10+，按版本分支；需要 MCDR >= 2.6.0。
打包插件为 `.mcdr`，Release 已附带成品。

## Checklist

- [x] Packaged plugin (.mcdr) with a release
- [x] README.md in repository root
- [x] plugin_id consistent (`iridium`)
- [x] One plugin per PR
```

## 可选优化

| 项 | 建议 |
|----|------|
| 许可 | 改为 MIT / Apache-2.0 更易过审 |
| 英文 README | 可另加 `README_en.md` 并写入 introduction |
| label | `tool`（官方标签：information / tool / management / api / handler） |

## 本地校验（可选）

官方脚本需 Python >= 3.11：

```bash
cd PluginCatalogue/scripts
pip3 install -r requirements.txt
python3 main.py check --help
```
