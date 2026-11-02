#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""BBC 实时语音转文字。

用 faster-whisper 在本地 CPU 上转录 HLS 直播分片，零 API 消耗、可离线。
每约 32 秒输出一段带时间戳的文本。

用法（模块）::

    from bbc_radio import transcribe
    for line in transcribe.stream("4"):
        print(line)

用法（命令行）::

    python3 -m bbc_radio.transcribe 4
"""

import os
import re
import subprocess
import sys
import tempfile
import time

from . import stations

# 国内网络走 HF 镜像，避免模型下载卡死
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")

DEFAULT_MODEL = "small.en"
WINDOW_SEGS = 5      # 每个转录窗口的分片数（每片约 6.4s → 约 32s）
SEG_SEC = 6.4
LANGUAGE = "en"


def _curl(url, timeout=10):
    """取一个 URL 的原始字节。"""
    return subprocess.run(
        ["curl", "-s", "--max-time", str(timeout), url],
        capture_output=True,
    ).stdout


def _playlist(url, timeout=10):
    """取 m3u8 文本。"""
    return subprocess.run(
        ["curl", "-s", "--max-time", str(timeout), url],
        capture_output=True, text=True,
    ).stdout


def _venv_python():
    """按优先级查找装有 faster-whisper 的 python 解释器。

    1. 环境变量 BBC_RADIO_PYTHON
    2. 项目 venv：~/.local/share/bbc-radio/venv
    3. 用户已有 venv：~/.local/venvs/whisper
    返回路径字符串，找不到返回 None。
    """
    import shutil as _shutil
    candidates = []
    env_py = os.environ.get("BBC_RADIO_PYTHON")
    if env_py:
        candidates.append(env_py)
    candidates.append(os.path.expanduser("~/.local/share/bbc-radio/venv/bin/python3"))
    candidates.append(os.path.expanduser("~/.local/venvs/whisper/bin/python3"))
    for path in candidates:
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path
    return None


def available_interpreter():
    """返回能 import faster_whisper 的 python 路径，找不到返回 None。"""
    import subprocess as _sp
    # 当前解释器优先
    if _has_faster_whisper():
        return sys.executable
    venv_py = _venv_python()
    if venv_py and venv_py != sys.executable:
        try:
            r = _sp.run([venv_py, "-c", "import faster_whisper"],
                        capture_output=True, timeout=25)
            if r.returncode == 0:
                return venv_py
        except (OSError, _sp.SubprocessError):
            pass
    return None


def _has_faster_whisper():
    try:
        import faster_whisper  # noqa: F401
        return True
    except ImportError:
        return False


def load_model(model_name=None, cpu_threads=4):
    """加载 faster-whisper 模型。首次会自动下载并缓存。"""
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise RuntimeError(
            "缺少 faster-whisper。请任选一种：\n"
            "  ./install.sh --with-asr          # 项目内建 venv\n"
            "  pip install faster-whisper==1.2.1 'av<19'\n"
            "  或设置 BBC_RADIO_PYTHON 指向已装好的 python"
        )
    name = model_name or os.environ.get("WHISPER_MODEL", DEFAULT_MODEL)
    return WhisperModel(name, device="cpu", compute_type="int8",
                        cpu_threads=cpu_threads)


def stream(station=None, model_name=None, on_line=None):
    """无限循环转录，逐行 yield 文本。

    推荐用 ``for line in stream(...)``。调用方负责在退出时 break。
    """
    key = stations.resolve(station)
    url = stations.url(key)
    base = url.rsplit("/", 1)[0] + "/"

    model = load_model(model_name)
    label = stations.label(key)
    yield "[启动] %s | 模型 %s | 约 %.0f 秒一个窗口" % (
        label, model_name or os.environ.get("WHISPER_MODEL", DEFAULT_MODEL),
        WINDOW_SEGS * SEG_SEC,
    )

    last_seq = -1
    prev_text = ""
    tmpf = os.path.join(tempfile.gettempdir(), "bbc_rt_chunk.ts")

    while True:
        try:
            playlist = _playlist(url)
            segs = []
            for line in playlist.splitlines():
                m = re.search(r"audio=\d+-(\d+)\.ts$", line.strip())
                if m:
                    segs.append((int(m.group(1)), line.strip()))

            new = [(s, f) for s, f in segs if s > last_seq]
            if not new:
                time.sleep(6)
                continue
            if len(new) > WINDOW_SEGS:      # 落后过多时只取最近一窗，控制延迟
                new = new[-WINDOW_SEGS:]
            last_seq = max(s for s, _ in new)

            with open(tmpf, "wb") as fh:
                for _, fname in new:
                    fh.write(_curl(base + fname))

            segments, _info = model.transcribe(
                tmpf,
                language=LANGUAGE,
                beam_size=1,
                condition_on_previous_text=True,
                initial_prompt=(prev_text[-150:] if prev_text else None),
                vad_filter=True,                      # 跳过静音，省 CPU
                vad_parameters={"min_silence_duration_ms": 500},
            )
            text = " ".join(s.text.strip() for s in segments)
            if text.strip():
                prev_text = text
                line = "[%s] %s" % (time.strftime("%H:%M:%S"), text)
                if on_line:
                    on_line(line)
                yield line
            time.sleep(3)
        except KeyboardInterrupt:
            raise
        except Exception as exc:            # 网络抖动等，重试即可
            yield "[警告] %s" % exc
            time.sleep(6)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    station = argv[0] if argv else stations.DEFAULT_STATION
    try:
        for line in stream(station):
            print(line, flush=True)
    except KeyboardInterrupt:
        print("\n[停止] 已结束转录。")
        return 0
    except Exception as exc:
        print("错误: %s" % exc, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
