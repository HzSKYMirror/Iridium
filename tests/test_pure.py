"""Pure-function unit tests (no live MCDR server required)."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcdreforged.api.all import Version

from iridium.calculator import CalcError, safe_eval
from iridium.hat import (
	_components_to_command_inner,
	_extract_head_item,
	_hand_slot,
	_head_slot,
	_item_to_command_form,
	_is_air,
)
from iridium.head import _give_head_command
from iridium.utils import (
	extract_compound,
	looks_like_item_snbt,
	parse_selected_item,
	sanitize_cmd,
	sanitize_name,
	strip_data_prefix,
)


def test_strip_prefix():
	payload = 'Notch has the following entity data: {id:"minecraft:stone",Count:1b}'
	assert strip_data_prefix(payload) == '{id:"minecraft:stone",Count:1b}'


def test_parse_selected_item():
	nbt = '{SelectedItem:{id:"minecraft:diamond_sword",Count:1b,tag:{Damage:1}},SelectedItemSlot:0}'
	assert parse_selected_item(nbt) == '{id:"minecraft:diamond_sword",Count:1b,tag:{Damage:1}}'


def test_extract_compound():
	nbt = '{foo:1,SelectedItem:{id:"minecraft:apple",Count:3b},bar:2}'
	assert extract_compound(nbt, "SelectedItem") == '{id:"minecraft:apple",Count:3b}'


def test_extract_list_field():
	nbt = '{HandItems:[{id:"minecraft:stone",Count:1b},{}]}'
	value = extract_compound(nbt, "HandItems")
	assert value is not None
	assert value.startswith("[")
	assert "minecraft:stone" in value


def test_parse_hand_items_fallback():
	nbt = '{HandItems:[{id:"minecraft:stone",Count:2b},{}]}'
	item = parse_selected_item(nbt)
	assert item == '{id:"minecraft:stone",Count:2b}'


def test_looks_like_item_snbt():
	assert looks_like_item_snbt('{id:"minecraft:stone",Count:1b}')
	assert not looks_like_item_snbt("No data found for SelectedItem")
	assert not looks_like_item_snbt("")
	assert not looks_like_item_snbt("{}")


def test_head_commands():
	assert (
		_give_head_command("Steve", "Notch", Version("1.20.5"))
		== 'give Steve minecraft:player_head[minecraft:profile="Notch"] 1'
	)
	assert (
		_give_head_command("Steve", "Notch", Version("1.16.5"))
		== 'give Steve minecraft:player_head{SkullOwner:"Notch"} 1'
	)
	assert (
		_give_head_command("Steve", "Notch", Version("1.12.2"))
		== 'give Steve minecraft:skull 1 3 {SkullOwner:"Notch"}'
	)
	assert (
		_give_head_command("Steve", 'Evil"name', Version("1.16.5"))
		== 'give Steve minecraft:player_head{SkullOwner:"Evilname"} 1'
	)
	assert (
		_give_head_command("Steve", 'Notch;give @a diamond', Version("1.16.5"))
		== 'give Steve minecraft:player_head{SkullOwner:"Notchgiveadiamond"} 1'
	)
	# component / NBT breakout attempts
	assert (
		_give_head_command("Steve", 'alex"}{id:"minecraft:stone', Version("1.16.5"))
		== 'give Steve minecraft:player_head{SkullOwner:"alexidminecraftstone"} 1'
	)
	assert (
		_give_head_command("Steve", 'x[minecraft:profile=y]', Version("1.20.5"))
		== 'give Steve minecraft:player_head[minecraft:profile="xminecraftprofiley"] 1'
	)
	# executor name is sanitized too
	assert (
		_give_head_command('Steve";give', "Notch", Version("1.16.5"))
		== 'give Stevegive minecraft:player_head{SkullOwner:"Notch"} 1'
	)
	# length cap
	assert (
		_give_head_command("Steve", "A" * 100, Version("1.16.5"))
		== 'give Steve minecraft:player_head{SkullOwner:"' + "A" * 32 + '"} 1'
	)


def test_item_form_modern():
	part, count = _item_to_command_form(
		'{id:"minecraft:diamond",count:2,components:{"minecraft:custom_name":"x"}}',
		Version("1.20.5"),
	)
	assert part == 'minecraft:diamond[minecraft:custom_name="x"]'
	assert count == 2


def test_components_to_command_inner():
	inner = _components_to_command_inner(
		'{"minecraft:custom_name":{text:"hi"}, "minecraft:damage":1, "minecraft:enchantments":{}}'
	)
	assert 'minecraft:custom_name={text:"hi"}' in inner
	assert "minecraft:damage=1" in inner
	assert "minecraft:enchantments={}" in inner


def test_item_form_legacy():
	part, count = _item_to_command_form(
		'{id:"minecraft:stone",Count:1b,tag:{display:{Name:"hi"}}}',
		Version("1.12.2"),
	)
	assert part == 'minecraft:stone{display:{Name:"hi"}}'
	assert count == 1


def test_slots():
	assert _head_slot(Version("1.20.1")) == "armor.head"
	assert _head_slot(Version("1.12.2")) == "slot.armor.head"
	assert _hand_slot(Version("1.20.1")) == "weapon.mainhand"
	assert _hand_slot(Version("1.12.2")) == "slot.weapon"
	assert _hand_slot(Version("1.8.9"), 3) == "slot.hotbar.3"
	assert _hand_slot(Version("1.8.9")) == "slot.hotbar.0"


def test_head_extract_1_12():
	payload = (
		'Steve has the following entity data: '
		'{SelectedItem:{id:"minecraft:stone",Count:1b},'
		'Inventory:[{Slot:103b,id:"minecraft:iron_helmet",Count:1b},{Slot:0b,id:"minecraft:dirt",Count:1b}]}'
	)
	item = _extract_head_item(payload, Version("1.12.2"))
	assert item is not None
	assert "iron_helmet" in item


def test_is_air():
	assert _is_air(None)
	assert _is_air("{}")
	assert _is_air('{id:"minecraft:air"}')
	assert not _is_air('{id:"minecraft:stone",Count:1b}')


def test_calculator():
	assert safe_eval("1+2*3") == 7
	assert safe_eval("(1+2)*(3-1)") == 6
	assert abs(safe_eval("10/4") - 2.5) < 1e-9
	assert safe_eval("2**10") == 1024
	assert safe_eval("2^10") == 1024
	try:
		safe_eval("__import__('os')")
		raise AssertionError("should reject")
	except CalcError:
		pass
	try:
		safe_eval("1;print(1)")
		raise AssertionError("should reject")
	except CalcError:
		pass


class _DummyServer:
	def get_server_information(self):
		return None


def test_motd_days_and_links():
	from datetime import datetime

	from iridium import join_tip
	from iridium.config import Config, apply_config

	cfg = Config()
	cfg.motd_start_day = "2020-01-01"
	cfg.motd_enabled = True
	apply_config(cfg)
	days = join_tip.server_days()
	assert days is not None
	assert days == (datetime.now() - datetime(2020, 1, 1)).days + 1

	pieces = join_tip.render_motd_line(
		"§e欢迎 §f{player}§e，官网 {link:§b打开|https://example.com}",
		"Steve",
		_DummyServer(),
	)
	assert pieces
	joined = "".join(p.to_plain_text() for p in pieces)
	assert "Steve" in joined
	assert "打开" in joined


def test_motd_placeholder_replacement():
	from iridium import join_tip
	from iridium.config import Config, apply_config

	cfg = Config()
	cfg.motd_start_day = ""
	cfg.motd_lines = ["hi {player} / {days} / {online}"]
	apply_config(cfg)
	text = join_tip.replace_placeholders("hi {player} / {days} / {online}", "Alex", _DummyServer())
	assert text == "hi Alex / ? / ?"


def test_sanitize_name_and_cmd():
	assert sanitize_name("Steve") == "Steve"
	assert sanitize_name('Evil";give') == "Evilgive"
	assert sanitize_name("A" * 100) == "A" * 32
	assert sanitize_name("") == ""
	assert sanitize_cmd("give x\ngive y") == "give x give y"
	assert sanitize_cmd("a\r\nb") == "a  b"


def test_is_at_least_accepts_str():
	from mcdreforged.api.all import Version

	from iridium.version_util import is_at_least

	assert is_at_least(Version("1.20.1"), "1.8") is True
	assert is_at_least("1.20.1", "1.8") is True
	assert is_at_least("1.7.10", "1.13") is False
	assert is_at_least("1.12.2", "1.13") is False
	assert is_at_least("not-a-version", "1.8") is False


def test_share_query_sanitizes_player():
	from mcdreforged.api.all import Version

	from iridium.share import _build_tellraw, _query_command

	cmd = _query_command('Steve";op', Version("1.16.5"))
	assert 'Steveop' in cmd
	assert '";' not in cmd
	tr = _build_tellraw('Bad"name', '{id:"minecraft:stone",Count:1b}', Version("1.20.1"))
	assert "Badname" in tr


def test_extract_display_name():
	from iridium.share import _display_json, _humanize_id, _item_id, _translate_key

	assert _item_id('{id:"minecraft:stone",Count:1b}') == "minecraft:stone"
	assert _translate_key("minecraft:diamond") == "item.minecraft.diamond"
	assert _translate_key("kubejs:time_twister_wireless") == "item.kubejs.time_twister_wireless"
	assert _humanize_id("kubejs:time_twister_wireless") == "Time Twister Wireless"
	assert _humanize_id("minecraft:fluix_covered_cable") == "Fluix Covered Cable"
	assert '"text"' in _display_json('{id:"minecraft:diamond",tag:{display:{Name:"Shiny"}}}')
	disp = _display_json('{id:"kubejs:time_twister_wireless",Count:1b}')
	assert '"translate"' in disp
	assert "Time Twister Wireless" in disp
	assert "fallback" in disp
	assert "kubejs:time_twister_wireless" not in disp


def test_strip_json_comments():
	import json

	from iridium.config import DEFAULT_CONFIG_TEXT, _strip_json_comments

	parsed = json.loads(_strip_json_comments(DEFAULT_CONFIG_TEXT))
	assert parsed["permission"] == 1
	assert "skymirror.top" in parsed["motd_lines"][2]
	# comment-looking text inside string is kept
	assert json.loads(_strip_json_comments('{"a": "http://x"}'))["a"] == "http://x"


if __name__ == "__main__":
	fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
	failed = 0
	for fn in fns:
		try:
			fn()
			print(f"PASS {fn.__name__}")
		except Exception as e:
			failed += 1
			print(f"FAIL {fn.__name__}: {e}")
	print(f"\n{len(fns) - failed}/{len(fns)} passed")
	sys.exit(1 if failed else 0)
