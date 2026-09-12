import json
import re
from pathlib import Path
from typing import List, Optional

from mcdreforged.api.all import *


class Config(Serializable):
	# 使用 !!share / !!hat / !!head / !!c 所需的最低权限等级
	permission: int = 1
	# !!head 冷却时间（秒），0 表示不限制
	head_cooldown_seconds: int = 60
	# !!hat 冷却时间（秒），0 表示不限制
	hat_cooldown_seconds: int = 3
	# !!share 是否播放提示音
	share_sound: bool = True
	# 强制指定 MC 版本号（如 "1.12.2"），留空则自动检测
	force_version: str = ""
	# 玩家加入时是否提示可用命令
	join_tip: bool = True
	# 加入提示延迟（秒），避免和进服消息挤在一起
	join_tip_delay_seconds: float = 1.5
	# 是否发送进服 MOTD（开服天数 + 自定义行）
	motd_enabled: bool = True
	# 开服日期，格式 YYYY-MM-DD，用于计算开服天数；留空则不显示天数
	motd_start_day: str = ""
	# MOTD 文本行。支持：
	#   {player} 玩家名
	#   {days}   开服天数
	#   {online} 在线人数（拿不到时显示 ?）
	#   {link:显示文字|https://url}  可点击链接
	#   {link:https://url}           链接，显示为完整 URL
	#   § 颜色代码
	motd_lines: List[str] = [
		"§6欢迎 §e{player}§6 加入服务器！",
		"§7服务器已开服 §b{days}§7 天",
		"§7官网: {link:§b点击打开官网|https://www.skymirror.top}",
		"§7QQ群: §f985402607",
	]


CONFIG_FILE = "config/iridium.json"

# 首次生成时写入带注释的 JSON（MCDR 本身不写注释）
DEFAULT_CONFIG_TEXT = """{
	// 使用 !!share / !!hat / !!head / !!c 所需的最低权限等级
	// 0=控制台  1=普通玩家  2=OP/管理员
	"permission": 1,

	// !!head 冷却时间（秒），0 表示不限制
	"head_cooldown_seconds": 60,

	// !!hat 冷却时间（秒），0 表示不限制
	"hat_cooldown_seconds": 3,

	// !!share 是否播放提示音
	"share_sound": true,

	// 强制指定 Minecraft 版本（如 "1.12.2"、"1.20.1"）
	// 留空则自动检测；检测失败时可手动填写
	"force_version": "",

	// 玩家进服时是否提示可用命令
	"join_tip": true,

	// 进服消息延迟（秒），0 为立即发送
	"join_tip_delay_seconds": 1.5,

	// 是否发送进服 MOTD（开服天数 + 自定义文案）
	"motd_enabled": true,

	// 开服日期，格式 YYYY-MM-DD（当天算第 1 天）
	// 留空则不显示开服天数
	"motd_start_day": "",

	// MOTD 文本行
	// 占位符: {player} 玩家名  {days} 开服天数  {online} 在线人数
	// 链接:   {link:显示文字|https://url}  或  {link:https://url}
	// 颜色:   支持原版 § 颜色代码
	"motd_lines": [
		"§6欢迎 §e{player}§6 加入服务器！",
		"§7服务器已开服 §b{days}§7 天",
		"§7官网: {link:§b点击打开官网|https://www.skymirror.top}",
		"§7QQ群: §f985402607"
	]
}
"""

# 模块级单例；on_load 时原地更新字段，避免各模块持有过期引用
config = Config()


def apply_config(new_cfg: Config) -> None:
	config.permission = new_cfg.permission
	config.head_cooldown_seconds = new_cfg.head_cooldown_seconds
	config.hat_cooldown_seconds = new_cfg.hat_cooldown_seconds
	config.share_sound = new_cfg.share_sound
	config.force_version = new_cfg.force_version
	config.join_tip = new_cfg.join_tip
	config.join_tip_delay_seconds = new_cfg.join_tip_delay_seconds
	config.motd_enabled = new_cfg.motd_enabled
	config.motd_start_day = new_cfg.motd_start_day
	config.motd_lines = list(new_cfg.motd_lines)


def _strip_json_comments(text: str) -> str:
	"""Remove // line comments outside of strings."""
	out = []
	i = 0
	n = len(text)
	in_string = False
	while i < n:
		c = text[i]
		if in_string:
			out.append(c)
			if c == "\\" and i + 1 < n:
				out.append(text[i + 1])
				i += 2
				continue
			if c == '"':
				in_string = False
			i += 1
			continue
		if c == '"':
			in_string = True
			out.append(c)
			i += 1
			continue
		if c == "/" and i + 1 < n and text[i + 1] == "/":
			while i < n and text[i] != "\n":
				i += 1
			continue
		out.append(c)
		i += 1
	return "".join(out)


def _config_path(server: PluginServerInterface) -> Path:
	wd = Path(server.get_mcdr_config()["working_directory"])
	return wd / CONFIG_FILE


def load_config(server: PluginServerInterface) -> Config:
	"""Load config/iridium.json; create a commented default on first run."""
	path = _config_path(server)
	path.parent.mkdir(parents=True, exist_ok=True)
	if not path.exists():
		path.write_text(DEFAULT_CONFIG_TEXT, encoding="utf-8")
		server.logger.info(f"已生成配置文件: {CONFIG_FILE}")
	raw = path.read_text(encoding="utf-8")
	try:
		data = json.loads(_strip_json_comments(raw))
	except json.JSONDecodeError as e:
		server.logger.error(f"配置文件 JSON 解析失败，使用默认值: {e}")
		return Config()
	return Config.deserialize(data)
