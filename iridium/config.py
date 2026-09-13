import json
import shutil
from datetime import date
from io import StringIO
from pathlib import Path
from typing import Any, List, Optional

from mcdreforged.api.all import *

try:
	from ruamel.yaml import YAML
except ImportError:  # pragma: no cover
	YAML = None  # type: ignore


def _today() -> str:
	return date.today().strftime("%Y-%m-%d")


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
	# 开服日期，格式 YYYY-MM-DD；默认为配置生成当天（当天算第 1 天）
	motd_start_day: str = _today()
	# MOTD 文本行
	motd_lines: List[str] = [
		"§6欢迎 §e{player}§6 加入服务器！",
		"§7服务器已开服 §b{days}§7 天",
		"§7官网: {link:§b点击打开官网|https://www.skymirror.top}",
		"§7QQ群: {link:§f985402607|https://skymirror.top/qq}",
	]


# 当前配置：MCDR 数据目录 → config/iridium/iridium.yml
CONFIG_FILE_NAME = "iridium.yml"
# 历史路径（仅用于迁移）
LEGACY_JSON_NAMES = (
	"iridium.json",  # config/iridium/iridium.json
)


def build_default_config_text() -> str:
	"""带注释的默认 YAML 配置；开服日期为生成当天。"""
	today = _today()
	return f"""# Iridium 配置文件 (YAML)
# 修改后执行: !!MCDR reload plugin
# This file uses standard YAML. '#' starts a comment.

# 使用 !!share / !!hat / !!head / !!c 所需的最低权限等级
# 0=控制台  1=普通玩家  2=OP/管理员
permission: 1

# !!head 冷却时间（秒），0 表示不限制
head_cooldown_seconds: 60

# !!hat 冷却时间（秒），0 表示不限制
hat_cooldown_seconds: 3

# !!share 是否播放提示音
share_sound: true

# 强制指定 Minecraft 版本（如 "1.12.2"、"1.20.1"）
# 留空则自动检测；检测失败时可手动填写
force_version: ""

# 玩家进服时是否提示可用命令
join_tip: true

# 进服消息延迟（秒），0 为立即发送
join_tip_delay_seconds: 1.5

# 是否发送进服 MOTD（开服天数 + 自定义文案）
motd_enabled: true

# 开服日期，格式 YYYY-MM-DD（当天算第 1 天）
# 默认为本配置文件生成当天，可自行修改为真实开服日
motd_start_day: "{today}"

# MOTD 文本行
# 占位符: {{player}} 玩家名  {{days}} 开服天数  {{online}} 在线人数
# 链接:   {{link:显示文字|https://url}}  或  {{link:https://url}}
# 颜色:   支持原版 § 颜色代码
motd_lines:
  - "§6欢迎 §e{{player}}§6 加入服务器！"
  - "§7服务器已开服 §b{{days}}§7 天"
  - "§7官网: {{link:§b点击打开官网|https://www.skymirror.top}}"
  - "§7QQ群: {{link:§f985402607|https://skymirror.top/qq}}"
"""


DEFAULT_CONFIG_TEXT = build_default_config_text()

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


def _yaml():
	if YAML is None:
		raise RuntimeError("ruamel.yaml is required")
	return YAML(typ="safe")


def _load_yaml_text(text: str) -> Any:
	return _yaml().load(StringIO(text))


def _dump_yaml(data: dict) -> str:
	buf = StringIO()
	y = _yaml()
	y.default_flow_style = False
	y.dump(data, buf)
	return buf.getvalue()


def _strip_json_comments(text: str) -> str:
	"""Remove // line comments outside of strings (legacy JSON only)."""
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


def config_file_path(server: PluginServerInterface) -> Path:
	"""Canonical path: MCDR data folder → config/iridium/iridium.yml"""
	return Path(server.get_data_folder()) / CONFIG_FILE_NAME


def _working_dir(server: PluginServerInterface) -> Path:
	try:
		wd = server.get_mcdr_config().get("working_directory") or "."
		return Path(wd).expanduser()
	except Exception:
		return Path.cwd()


def _legacy_json_paths(server: PluginServerInterface) -> List[Path]:
	data_dir = Path(server.get_data_folder())
	wd = _working_dir(server)
	return [
		data_dir / "iridium.json",
		wd / "config" / "iridium.json",
	]


def _write_default(path: Path, server: PluginServerInterface) -> bool:
	try:
		path.parent.mkdir(parents=True, exist_ok=True)
		path.write_text(build_default_config_text(), encoding="utf-8")
		server.logger.info(f"已生成配置文件: {path}")
		return True
	except Exception as e:
		server.logger.error(f"写入配置文件失败 {path}: {e}")
		return False


def _try_load_dict_from_text(text: str) -> Optional[dict]:
	text = text.strip()
	if not text:
		return None
	if text.startswith("{"):
		return json.loads(_strip_json_comments(text))
	data = _load_yaml_text(text)
	return data if isinstance(data, dict) else None


def _migrate_legacy_json(server: PluginServerInterface, dest: Path) -> None:
	"""Convert old JSON config (with optional // comments) to YAML if dest is missing."""
	if dest.is_file():
		return
	for src in _legacy_json_paths(server):
		try:
			if not src.is_file():
				continue
			raw = src.read_text(encoding="utf-8")
			data = _try_load_dict_from_text(raw)
			if not data:
				continue
			dest.parent.mkdir(parents=True, exist_ok=True)
			# keep comments in default template + overlay known keys via dump
			cfg = Config.deserialize(data)
			overlay = {
				"permission": cfg.permission,
				"head_cooldown_seconds": cfg.head_cooldown_seconds,
				"hat_cooldown_seconds": cfg.hat_cooldown_seconds,
				"share_sound": cfg.share_sound,
				"force_version": cfg.force_version,
				"join_tip": cfg.join_tip,
				"join_tip_delay_seconds": cfg.join_tip_delay_seconds,
				"motd_enabled": cfg.motd_enabled,
				"motd_start_day": cfg.motd_start_day,
				"motd_lines": list(cfg.motd_lines),
			}
			# Prefer commented default template when values match defaults is complex;
			# dump parsed values with a short header for clarity.
			header = (
				"# Iridium 配置 (从旧 JSON 迁移)\n"
				"# Migrated from legacy JSON config\n\n"
			)
			dest.write_text(header + _dump_yaml(overlay), encoding="utf-8")
			server.logger.info(f"已从旧 JSON 迁移配置: {src} -> {dest}")
			return
		except Exception as e:
			server.logger.warning(f"迁移旧配置失败 {src}: {e}")


def load_config(server: PluginServerInterface) -> Config:
	"""
	Load config/iridium/iridium.yml (MCDR data folder).
	Create commented default if missing; migrate legacy JSON if needed.
	"""
	path = config_file_path(server)
	_migrate_legacy_json(server, path)

	if not path.is_file():
		_write_default(path, server)

	if not path.is_file():
		server.logger.warning(f"配置文件不存在且无法创建，使用内存默认值: {path}")
		return Config()

	try:
		raw = path.read_text(encoding="utf-8")
		data = _load_yaml_text(raw)
		if not isinstance(data, dict):
			raise ValueError("YAML root must be a mapping")
		server.logger.info(f"配置已加载: {path}")
		return Config.deserialize(data)
	except Exception as e:
		server.logger.error(f"读取/解析 YAML 配置失败 {path}: {e}，使用默认值")
		return Config()
