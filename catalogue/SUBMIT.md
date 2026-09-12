# 提交到 MCDReforged 官方插件库

官方库：https://github.com/MCDReforged/PluginCatalogue  
贡献指南：https://github.com/MCDReforged/PluginCatalogue/blob/master/CONTRIBUTING_zh_cn.md

## 硬性前提（当前还缺）

1. **必须有公开 GitHub 仓库**  
   官方脚本用 `GithubRepository` 拉取 Release / README。  
   `https://git.skymirror.top/...` **不会被收录**。

2. **GitHub Release 标签正确，且附件为 `.mcdr`**  
   建议 Tag：`v26.9.1`（与版本对应，带 `v` 前缀较常见）。  
   附件名建议：`Iridium-26.9.1.mcdr` 或 `Iridium.mcdr`。

3. **仓库根目录有 `README.md`**（已有）。

4. **许可**  
   官方强烈建议 OSI 开源许可。当前为 All Rights Reserved：  
   - 仍可提交，但审阅可能更慢  
   - 提交即视为授权社区从 GitHub Releases 下载使用（见贡献指南）  
   - 若希望更顺利，可改为 MIT / Apache-2.0 等后再提 PR

5. **一个 PR 只加一个插件**（只加 Iridium）。

## 提交步骤

### 1. 把源码同步到 GitHub

```bash
# 在 GitHub 建公开仓库 Iridium 后
cd /Users/l3126596029/Code/MCDR_plg/Iridium
git remote add github git@github.com:你的用户名/Iridium.git
git push -u github main
```

### 2. 在 GitHub 发 Release

- Tag：`v26.9.1`
- 附件：用本地 `./pack.sh` 生成的 `Iridium.mcdr`

### 3. 修改 catalogue/plugin_info.json

把 `repository` 改成真实 GitHub 地址，例如：

```json
"repository": "https://github.com/你的用户名/Iridium"
```

`authors.link` 也可改成 GitHub 主页。

### 4. 向官方库提 PR

1. Fork https://github.com/MCDReforged/PluginCatalogue  
2. 在 fork 中新建路径：`plugins/iridium/plugin_info.json`  
   内容使用修改后的 `catalogue/plugin_info.json`  
3. 向 `MCDReforged/PluginCatalogue` 的 `master` 发起 Pull Request  

### PR 标题建议

```text
Add plugin: iridium
```

### PR 描述模板

```markdown
## Plugin

- ID: `iridium`
- Name: Iridium
- Repository: https://github.com/你的用户名/Iridium
- Release: https://github.com/你的用户名/Iridium/releases/tag/v26.9.1
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

## 可选优化（提高过审概率）

| 项 | 建议 |
|----|------|
| 许可 | 改为 MIT / Apache-2.0 |
| 名称冲突 | 官方库无 `iridium`；与现有插件名称距离足够 |
| label | 用 `tool`（信息/工具类） |
| 英文 README | 目前 `introduction` 中英文都指向中文 README，可另加 `README_en.md` |

## 本地校验（可选）

官方脚本需 Python >= 3.11：

```bash
# 克隆官方库后
cd PluginCatalogue/scripts
pip3 install -r requirements.txt
python3 main.py check --help
```
