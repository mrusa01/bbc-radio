#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bbc-radio 命令行入口。

示例::

    bbc-radio play 4          # 播放 Radio 4
    bbc-radio play            # 不带参数默认 Radio 4
    bbc-radio stop            # 停止
    bbc-radio list            # 列出所有电台
    bbc-radio status          # 当前播放状态
    bbc-radio volume 60       # 设置音量
    bbc-radio transcribe 4    # 实时转录 Radio 4
"""

import argparse
import sys

if __package__ in (None, ""):
    # 允许 `python3 bbc_radio_cli.py` 直接运行
    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from bbc_radio import __version__, player, stations, transcribe
else:
    from . import __version__, player, stations, transcribe


def cmd_play(args):
    try:
        key, label = player.play(args.station)
    except (RuntimeError, ValueError) as exc:
        print("错误: %s" % exc, file=sys.stderr)
        return 1
    print("正在播放: %s（pid %s）" % (label, player.read_pid()))
    return 0


def cmd_stop(_args):
    if player.stop():
        print("已停止播放。")
    else:
        print("当前没有在播放。")
    return 0


def cmd_list(_args):
    for key, (label, _url, aliases) in stations.STATIONS.items():
        alias = ", ".join(aliases)
        print("  %-3s %-26s %s" % (key, label, alias))
    return 0


def cmd_status(_args):
    pid = player.read_pid()
    if pid is None:
        print("状态: 未播放")
        return 0
    vol = player.get_volume()
    print("状态: 播放中（pid %s）" % pid)
    if vol is not None:
        print("音量: %d%%" % vol)
    return 0


def cmd_volume(args):
    if not player.is_playing():
        print("错误: 当前没有在播放。", file=sys.stderr)
        return 1
    if player.set_volume(args.level):
        print("音量已设为 %d%%" % max(0, min(100, args.level)))
        return 0
    print("错误: 设置音量失败。", file=sys.stderr)
    return 1


def cmd_transcribe(args):
    # 若当前解释器缺 faster-whisper，自动切换到已装好的解释器
    py = transcribe.available_interpreter()
    if py is None:
        print(
            "错误: 找不到装有 faster-whisper 的 Python 环境。\n"
            "  安装：./install.sh --with-asr\n"
            "  或设置 BBC_RADIO_PYTHON 指向已装好的 python",
            file=sys.stderr,
        )
        return 1
    if py != sys.executable:
        import os
        import subprocess
        cli = os.path.abspath(__file__)
        cmd = [py, cli, "transcribe"]
        if args.station:
            cmd.append(args.station)
        if args.model:
            cmd += ["--model", args.model]
        try:
            return subprocess.call(cmd)
        except KeyboardInterrupt:
            print("\n已结束转录。")
            return 0

    try:
        for line in transcribe.stream(args.station, args.model):
            print(line, flush=True)
    except KeyboardInterrupt:
        print("\n已结束转录。")
    except (RuntimeError, ValueError) as exc:
        print("错误: %s" % exc, file=sys.stderr)
        return 1
    return 0


def build_parser():
    p = argparse.ArgumentParser(
        prog="bbc-radio",
        description="BBC 电台播放器（播放 / 停止 / 音量 / 实时转录）",
    )
    p.add_argument("--version", action="version",
                   version="bbc-radio %s" % __version__)
    sub = p.add_subparsers(dest="command")

    sp = sub.add_parser("play", help="播放电台")
    sp.add_argument("station", nargs="?",
                    default=stations.DEFAULT_STATION,
                    help="电台代号，如 1-6 / 1x / 4x / ws（默认 4）")
    sp.set_defaults(func=cmd_play)

    sp = sub.add_parser("stop", help="停止播放")
    sp.set_defaults(func=cmd_stop)

    sp = sub.add_parser("list", help="列出所有电台")
    sp.set_defaults(func=cmd_list)

    sp = sub.add_parser("status", help="查看播放状态")
    sp.set_defaults(func=cmd_status)

    sp = sub.add_parser("volume", help="设置音量 0-100")
    sp.add_argument("level", type=int, help="音量百分比")
    sp.set_defaults(func=cmd_volume)

    sp = sub.add_parser("transcribe", help="实时语音转文字")
    sp.add_argument("station", nargs="?",
                    default=stations.DEFAULT_STATION,
                    help="电台代号（默认 4）")
    sp.add_argument("--model", default=None,
                    help="whisper 模型，默认 small.en（可选 base.en 更省资源）")
    sp.set_defaults(func=cmd_transcribe)

    return p


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        parser.print_help()
        return 0
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
