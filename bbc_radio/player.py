#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mpv 播放控制：启动、停止、音量、状态查询。

兼容两种 mpv 安装方式：
  * 系统包管理安装的 ``mpv``
  * flatpak 版 ``io.mpv.Mpv``

mpv 以 IPC socket 方式运行，路径在 /tmp 下，flatpak 已共享 /tmp。
"""

import json
import os
import shutil
import socket
import subprocess
import time

from . import stations

MPV_SOCK = "/tmp/bbc_mpv.sock"
PIDFILE = "/tmp/bbc_mpv.pid"
FLATPAK_APP = "io.mpv.Mpv"


# ---------------- mpv 定位 ----------------

def is_flatpak_available():
    """检查是否装的是 flatpak 版 mpv。"""
    if not shutil.which("flatpak"):
        return False
    try:
        out = subprocess.run(
            ["flatpak", "list", "--app", "--columns=application"],
            capture_output=True, text=True, timeout=5,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return False
    return FLATPAK_APP in out.split()


def mpv_command_prefix():
    """返回启动 mpv 的命令前缀，找不到则抛 RuntimeError。"""
    if shutil.which("mpv"):
        return ["mpv"]
    if is_flatpak_available():
        return ["flatpak", "run", FLATPAK_APP]
    raise RuntimeError(
        "未找到 mpv。请安装：sudo apt install mpv  或  "
        "flatpak install flathub io.mpv.Mpv"
    )


# ---------------- IPC ----------------

def ipc(command, timeout=2.0):
    """向运行中的 mpv 发命令，返回响应 dict 或 None（未运行）。"""
    sock = None
    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect(MPV_SOCK)
        sock.sendall(json.dumps({"command": command, "request_id": 1}).encode() + b"\n")
        buf = b""
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            buf += chunk
            if b"\n" in buf:
                break
        return json.loads(buf.split(b"\n", 1)[0].decode())
    except (OSError, ValueError):
        return None
    finally:
        if sock is not None:
            try:
                sock.close()
            except OSError:
                pass


# ---------------- 进程控制 ----------------

def _pid_alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except (OSError, TypeError, ValueError):
        return False


def read_pid():
    """读取记录的 mpv pid，若进程已不存在则返回 None。"""
    try:
        with open(PIDFILE) as f:
            pid = int(f.read().strip())
    except (OSError, ValueError):
        return None
    return pid if _pid_alive(pid) else None


def is_playing():
    """是否有 BBC 播放会话在跑。

    同时检查 pidfile 与实际进程，避免 pidfile 丢失时误报未播放。
    """
    return read_pid() is not None or find_players() != []


# 用于识别本项目启动的 mpv 进程的流地址特征
_STREAM_MARKERS = ("as-hls-ww-liv", "stream.live.vc.bbcmedi")


def find_players():
    """扫描系统里所有正在播 BBC 的 mpv 进程 pid。

    无论是否由本项目启动、pidfile 是否还在，都能找到。
    flatpak 版 mpv 会多一层 bwrap 包装进程，两者都返回。
    """
    pids = []
    try:
        out = subprocess.run(
            ["pgrep", "-f", "mpv.*as-hls-ww-liv[e]"],
            capture_output=True, text=True, timeout=5,
        ).stdout
        pids += [int(x) for x in out.split() if x.isdigit()]
        out = subprocess.run(
            ["pgrep", "-f", "mpv.*stream.live.vc.bbcmedi[a]"],
            capture_output=True, text=True, timeout=5,
        ).stdout
        pids += [int(x) for x in out.split() if x.isdigit()]
    except (OSError, subprocess.SubprocessError, ValueError):
        pass

    # 本机拥有的 mpv 主进程（覆盖启动瞬间还没读到流地址的情况）
    pid = read_pid()
    if pid is not None:
        pids.append(pid)

    return sorted(set(pids))


def stop():
    """停止播放。返回 True 表示确实停掉了至少一个进程。

    不依赖 pidfile：按流地址特征扫描并终止所有 BBC mpv 进程，
    避免多次 play 后残留孤儿进程继续出声。
    """
    stopped = False
    targets = find_players()

    if targets:
        # 先用 SIGTERM 让 mpv 正常退出
        for sig in (15, 9):
            alive = []
            for pid in targets:
                try:
                    os.kill(pid, sig)
                    stopped = True
                    alive.append(pid)
                except OSError:
                    pass
            if not alive:
                break
            if sig == 15:
                # 等最多 3 秒再升级为 SIGKILL
                for _ in range(15):
                    time.sleep(0.2)
                    if all(not _pid_alive(p) for p in alive):
                        break
                targets = [p for p in alive if _pid_alive(p)]
                if not targets:
                    break

    # 清理残留 socket 与 pidfile
    for path in (PIDFILE, MPV_SOCK):
        try:
            os.remove(path)
        except OSError:
            pass

    return stopped


def play(station=None):
    """播放指定电台，返回 (key, 显示名)。会先停掉旧会话。

    mpv 以分离进程方式运行，本函数立即返回，不阻塞。
    """
    key = stations.resolve(station)
    prefix = mpv_command_prefix()

    stop()
    time.sleep(0.6)
    try:
        os.remove(MPV_SOCK)
    except OSError:
        pass

    cmd = prefix + [
        "--no-video",
        "--input-ipc-server=" + MPV_SOCK,
        "--really-quiet",
        stations.url(key),
    ]
    logf = open("/tmp/bbc_mpv.log", "ab")
    try:
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=logf,
            stderr=logf,
            start_new_session=True,   # 脱离当前会话，关掉终端也不影响
        )
    finally:
        logf.close()

    with open(PIDFILE, "w") as f:
        f.write(str(proc.pid))

    # 等待 socket 就绪（最多约 6 秒）
    for _ in range(30):
        if os.path.exists(MPV_SOCK):
            break
        if proc.poll() is not None:
            raise RuntimeError(
                "mpv 启动失败，可查看 /tmp/bbc_mpv.log"
            )
        time.sleep(0.2)

    return key, stations.label(key)


# ---------------- 音量 ----------------

def get_volume():
    """返回当前音量 0-100，未运行返回 None。"""
    resp = ipc(["get_property", "volume"])
    if resp and resp.get("error") == "success":
        try:
            return int(round(float(resp.get("data"))))
        except (TypeError, ValueError):
            return None
    return None


def set_volume(value):
    """设置音量 0-100，返回是否成功。"""
    value = max(0, min(100, int(value)))
    resp = ipc(["set_property", "volume", value])
    return bool(resp and resp.get("error") == "success")
