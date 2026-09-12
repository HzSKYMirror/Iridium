from typing import List

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
