#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""BBC 电台清单：唯一数据源。

所有播放/转录入口都从这里取地址，避免多处重复。
流地址使用 Akamai ``ww`` 池（大陆可直连）与 World Service 官方直播源。
"""

from collections import OrderedDict

# key -> (显示名, 流地址, 别名列表)
STATIONS = OrderedDict([
    ("1", ("BBC Radio 1",
           "http://as-hls-ww-live.akamaized.net/pool_01505109/live/ww/bbc_radio_one/bbc_radio_one.isml/bbc_radio_one-audio=128000.norewind.m3u8",
           ["one", "r1"])),
    ("2", ("BBC Radio 2",
           "http://as-hls-ww-live.akamaized.net/pool_74208725/live/ww/bbc_radio_two/bbc_radio_two.isml/bbc_radio_two-audio=128000.norewind.m3u8",
           ["two", "r2"])),
    ("3", ("BBC Radio 3",
           "http://as-hls-ww-live.akamaized.net/pool_23461179/live/ww/bbc_radio_three/bbc_radio_three.isml/bbc_radio_three-audio=128000.norewind.m3u8",
           ["three", "r3"])),
    ("4", ("BBC Radio 4",
           "http://as-hls-ww-live.akamaized.net/pool_55057080/live/ww/bbc_radio_fourfm/bbc_radio_fourfm.isml/bbc_radio_fourfm-audio=128000.norewind.m3u8",
           ["four", "r4", "fourfm"])),
    ("5", ("BBC Radio 5 Live",
           "http://as-hls-ww-live.akamaized.net/pool_89021708/live/ww/bbc_radio_five_live/bbc_radio_five_live.isml/bbc_radio_five_live-audio=128000.norewind.m3u8",
           ["five", "r5", "fivelive"])),
    ("6", ("BBC Radio 6 Music",
           "http://as-hls-ww-live.akamaized.net/pool_81827798/live/ww/bbc_6music/bbc_6music.isml/bbc_6music-audio=128000.norewind.m3u8",
           ["six", "r6", "6music"])),
    ("1x", ("BBC Radio 1Xtra",
            "http://as-hls-ww-live.akamaized.net/pool_92079267/live/ww/bbc_1xtra/bbc_1xtra.isml/bbc_1xtra-audio=128000.norewind.m3u8",
            ["onextra", "r1x"])),
    ("1a", ("BBC Radio 1 Anthems",
            "http://as-hls-ww-live.akamaized.net/pool_11351741/live/ww/bbc_radio_one_anthems/bbc_radio_one_anthems.isml/bbc_radio_one_anthems-audio=128000.norewind.m3u8",
            ["anthems", "r1a"])),
    ("1d", ("BBC Radio 1 Dance",
            "http://as-hls-ww-live.akamaized.net/pool_62063831/live/ww/bbc_radio_one_dance/bbc_radio_one_dance.isml/bbc_radio_one_dance-audio=128000.norewind.m3u8",
            ["dance", "r1d"])),
    ("3u", ("BBC Radio 3 Unwind",
            "http://as-hls-ww-live.akamaized.net/pool_30624046/live/ww/bbc_radio_three_unwind/bbc_radio_three_unwind.isml/bbc_radio_three_unwind-audio=128000.norewind.m3u8",
            ["unwind", "r3u"])),
    ("4x", ("BBC Radio 4 Extra",
            "http://as-hls-ww-live.akamaized.net/pool_26173715/live/ww/bbc_radio_four_extra/bbc_radio_four_extra.isml/bbc_radio_four_extra-audio=128000.norewind.m3u8",
            ["fourextra", "r4x"])),
    ("ws", ("BBC World Service",
            "http://stream.live.vc.bbcmedia.co.uk/bbc_world_service",
            ["world", "worldservice", "bbcws"])),
])

DEFAULT_STATION = "4"


def resolve(name):
    """把用户输入解析成标准 key。支持别名与大小写。未知则抛 ValueError。"""
    if not name:
        return DEFAULT_STATION
    key = str(name).strip().lower()
    if key in STATIONS:
        return key
    for k, (_label, _url, aliases) in STATIONS.items():
        if key in aliases:
            return k
    raise ValueError(
        "未知电台: %s（可用: %s）" % (name, ", ".join(STATIONS))
    )


def label(key):
    """返回电台显示名。"""
    return STATIONS[key][0]


def url(key):
    """返回电台流地址。"""
    return STATIONS[key][1]


def choices():
    """返回 (key, 显示名) 列表，供 GUI 下拉框使用。"""
    return [(k, v[0]) for k, v in STATIONS.items()]
