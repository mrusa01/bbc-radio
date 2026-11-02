#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""BBC Radio 图形界面（PyQt5）。

功能：选台 / 播放 / 停止 / 音量 / 实时转录（语音转文字）。

底层复用 ``bbc_radio`` 包：播放用 mpv + IPC，转录用 faster-whisper。
所有路径都相对本文件解析，可直接迁移到任意目录。
"""

import os
import sys
import threading
import time

if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from PyQt5.QtCore import Qt, QTimer
    from PyQt5.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QLabel, QPushButton, QSlider, QPlainTextEdit, QFrame,
        QGroupBox, QGridLayout, QTabWidget,
    )
except ImportError:
    sys.stderr.write(
        "缺少 PyQt5。安装：\n"
        "  sudo apt install python3-pyqt5\n"
        "  或 pip install PyQt5\n"
    )
    raise

from bbc_radio import __version__, player, stations, transcribe


class RadioWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BBC Radio 控制面板")
        self.setMinimumSize(600, 680)
        self.cur_station = stations.DEFAULT_STATION
        self.vol = 100
        self.tr_thread = None
        self.tr_stop = None

        self._build_ui()
        self._init_timers()
        self._log("欢迎使用 BBC Radio 控制面板 v%s" % __version__)

    # ---------- UI ----------
    def _build_ui(self):
        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(10)

        title = QLabel("BBC Radio 控制面板")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        root.addWidget(title)

        # 选台
        sel_box = QGroupBox("选台")
        grid = QGridLayout(sel_box)
        grid.setSpacing(6)
        self.station_btns = {}
        for i, (key, name) in enumerate(stations.choices()):
            b = QPushButton(name)
            b.setCheckable(True)
            b.setProperty("station", key)
            b.clicked.connect(lambda _, k=key: self._select_station(k))
            grid.addWidget(b, i // 3, i % 3)
            self.station_btns[key] = b
        self.station_btns[self.cur_station].setChecked(True)
        root.addWidget(sel_box)

        # 播放 / 停止
        ctrl = QHBoxLayout()
        self.play_btn = QPushButton("播放")
        self.play_btn.setStyleSheet("font-weight:bold;padding:8px;")
        self.play_btn.clicked.connect(self.play)
        self.stop_btn = QPushButton("停止")
        self.stop_btn.setStyleSheet("padding:8px;")
        self.stop_btn.clicked.connect(self.stop)
        ctrl.addWidget(self.play_btn)
        ctrl.addWidget(self.stop_btn)
        root.addLayout(ctrl)

        # 状态
        status = QFrame()
        status.setFrameShape(QFrame.StyledPanel)
        sl = QHBoxLayout(status)
        self.status_dot = QLabel("●")
        self.status_dot.setStyleSheet("color:#999;font-size:16px;")
        self.status_lbl = QLabel("未播放")
        self.status_lbl.setStyleSheet("font-size:14px;")
        sl.addWidget(self.status_dot)
        sl.addWidget(self.status_lbl, 1)
        root.addWidget(status)

        # 音量
        vol_box = QGroupBox("音量")
        vl = QHBoxLayout(vol_box)
        self.vol_lbl = QLabel("100%")
        self.vol_lbl.setMinimumWidth(44)
        self.vol_slider = QSlider(Qt.Horizontal)
        self.vol_slider.setRange(0, 100)
        self.vol_slider.setValue(100)
        self.vol_slider.valueChanged.connect(self._on_vol_change)
        vl.addWidget(self.vol_lbl)
        vl.addWidget(self.vol_slider, 1)
        root.addWidget(vol_box)

        # 选项卡
        tabs = QTabWidget()

        tr = QWidget()
        trl = QVBoxLayout(tr)
        trow = QHBoxLayout()
        self.tr_btn = QPushButton("开始转录")
        self.tr_btn.clicked.connect(self.toggle_transcribe)
        self.tr_clear = QPushButton("清空")
        self.tr_clear.clicked.connect(lambda: self.tr_text.clear())
        trow.addWidget(self.tr_btn)
        trow.addWidget(self.tr_clear)
        trow.addStretch(1)
        trl.addLayout(trow)
        self.tr_text = QPlainTextEdit()
        self.tr_text.setReadOnly(True)
        self.tr_text.setPlaceholderText(
            "点击“开始转录”，这里会滚动显示实时转文字结果…")
        trl.addWidget(self.tr_text, 1)
        tabs.addTab(tr, "转录（语音转文字）")

        log = QWidget()
        logl = QVBoxLayout(log)
        self.log_text = QPlainTextEdit()
        self.log_text.setReadOnly(True)
        logl.addWidget(self.log_text)
        tabs.addTab(log, "日志")

        root.addWidget(tabs, 1)
        self.setCentralWidget(central)

    def _init_timers(self):
        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self._refresh_status)
        self.status_timer.start(1500)
        self.vol_timer = QTimer(self)
        self.vol_timer.setSingleShot(True)
        self.vol_timer.timeout.connect(self._apply_volume)

    # ---------- 辅助 ----------
    def _log(self, msg):
        self.log_text.appendPlainText("[%s] %s" % (time.strftime("%H:%M:%S"), msg))

    def _select_station(self, key):
        self.cur_station = key
        for k, b in self.station_btns.items():
            b.setChecked(k == key)
        name = stations.label(key)
        self.status_lbl.setText("已选择：%s（未播放）" % name)
        self._log("选择电台：%s" % name)

    def _station_name(self):
        return stations.label(self.cur_station)

    # ---------- 播放 ----------
    def play(self):
        try:
            player.play(self.cur_station)
        except (RuntimeError, ValueError) as exc:
            self._log("启动播放失败：%s" % exc)
            self.status_lbl.setText("启动失败")
            return
        self.status_lbl.setText("正在启动：%s…" % self._station_name())
        self._log("开始播放：%s" % self._station_name())
        QTimer.singleShot(1200, self._apply_volume)

    def stop(self):
        player.stop()
        self.status_lbl.setText("已停止")
        self.status_dot.setStyleSheet("color:#999;font-size:16px;")
        self._log("停止播放")

    def _on_vol_change(self, v):
        self.vol_lbl.setText("%d%%" % v)
        self.vol = v
        self.vol_timer.start(150)

    def _apply_volume(self):
        if player.is_playing() and not player.set_volume(self.vol):
            self._log("设置音量 %d%% 失败（mpv 未响应）" % self.vol)

    def _refresh_status(self):
        if player.is_playing():
            self.status_dot.setStyleSheet("color:#2ecc71;font-size:16px;")
            self.status_lbl.setText(
                "播放中：%s  ·  音量 %d%%" % (self._station_name(), self.vol))
        else:
            self.status_dot.setStyleSheet("color:#999;font-size:16px;")
            if "播放中" in self.status_lbl.text():
                self.status_lbl.setText("未播放")

    # ---------- 转录 ----------
    def toggle_transcribe(self):
        if self.tr_thread is not None and self.tr_thread.is_alive():
            self._stop_transcribe()
        else:
            self._start_transcribe()

    def _start_transcribe(self):
        key = self.cur_station
        self.tr_stop = threading.Event()
        stop_event = self.tr_stop

        def worker():
            try:
                for line in transcribe.stream(key):
                    if stop_event.is_set():
                        break
                    self._on_tr_line(line)
            except Exception as exc:            # 后台线程不能让它崩掉界面
                self._on_tr_line("[错误] %s" % exc)
            finally:
                self._on_tr_finished()

        self.tr_thread = threading.Thread(target=worker, daemon=True)
        self.tr_thread.start()
        self.tr_btn.setText("停止转录")
        self._log("开始转录：%s" % self._station_name())

    def _stop_transcribe(self):
        if self.tr_stop is not None:
            self.tr_stop.set()
            self.tr_stop = None
        self.tr_btn.setText("开始转录")
        self._log("停止转录（当前窗口处理完后退出）")

    def _on_tr_line(self, text):
        if text.strip():
            self.tr_text.appendPlainText(text)
            sb = self.tr_text.verticalScrollBar()
            sb.setValue(sb.maximum())

    def _on_tr_finished(self):
        self.tr_btn.setText("开始转录")
        self.tr_stop = None

    # ---------- 关闭 ----------
    def closeEvent(self, event):
        player.stop()
        if self.tr_stop is not None:
            self.tr_stop.set()
        super().closeEvent(event)


def main():
    app = QApplication(sys.argv)
    w = RadioWindow()
    w.show()
    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
