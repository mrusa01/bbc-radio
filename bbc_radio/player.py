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
    """是否有 BBC 播放会话在跑。"""
    return read_pid() is not None


def stop():
    """停止播放。返回 True 表示确实停掉了一个会话。"""
    stopped = False
    pid = read_pid()
    if pid is not None:
        try:
            os.kill(pid, 15)
            stopped = True
        except OSError:
            pass
    # 兜底：清理残留 socket 与 pidfile
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
