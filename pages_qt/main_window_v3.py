"""Seeker 播放器 · v3 界面（美化版）

这是一份全新的界面实现，不改动 main.py / main_v2.py 以及 main_window*.py：

    python main_v3.py

外观：深色渐变 + 圆角卡片 + 紫色强调色
功能：在保留原播放内核（core/music_player.py）全部能力的基础上，
      增加了播放列表、上一首 / 下一首、拖拽添加、快捷键等界面层能力。
"""
import os
import sys

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor, QFont, QIcon, QKeySequence, QLinearGradient, QPainter, QPixmap
from PyQt5.QtWidgets import (
    QApplication, QWidget, QFrame, QLabel, QPushButton, QVBoxLayout,
    QHBoxLayout, QShortcut, QMessageBox, QSlider, QStackedWidget,
    QButtonGroup, QGraphicsDropShadowEffect,
)

from core.music_player import Music_player
from pages_qt.local_page_v3 import LocalMusicPage


# ═══════════════════════════════════════════════════════════
#  小工具
# ═══════════════════════════════════════════════════════════
def fmt_time(ms):
    ms = max(0, int(ms))
    return f"{ms // 60000}:{(ms // 1000) % 60:02d}"


def elide(text, limit=36):
    """过长文本做省略，避免撑破播放栏。"""
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def apply_shadow(widget, radius=30, dy=8, alpha=120):
    effect = QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(radius)
    effect.setOffset(0, dy)
    effect.setColor(QColor(0, 0, 0, alpha))
    widget.setGraphicsEffect(effect)


def make_window_icon():
    """用代码画一个渐变音符图标，避免依赖图片资源。"""
    size = 128
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.Antialiasing)
    grad = QLinearGradient(0, 0, size, size)
    grad.setColorAt(0.0, QColor("#8b5cf6"))
    grad.setColorAt(1.0, QColor("#4fd1c5"))
    painter.setBrush(grad)
    painter.setPen(Qt.NoPen)
    painter.drawRoundedRect(0, 0, size, size, 30, 30)
    painter.setPen(QColor("#ffffff"))
    font = QFont()
    font.setPixelSize(74)
    font.setBold(True)
    painter.setFont(font)
    painter.drawText(pix.rect(), Qt.AlignCenter, "♪")
    painter.end()
    return QIcon(pix)


# ═══════════════════════════════════════════════════════════
#  主窗口
# ═══════════════════════════════════════════════════════════
class MainWindow(QWidget):
    PAGE_META = [
        ("首页", "欢迎回来，挑一首歌开始吧"),
        ("本地音乐", "添加本地文件，双击即可播放"),
        ("我的歌单", "歌单功能还在路上"),
        ("设置", "更多个性化选项即将到来"),
    ]

    def __init__(self):
        super().__init__()
        self.setObjectName("root")
        self.setWindowTitle("Seeker 音乐播放器")
        self.setWindowIcon(make_window_icon())
        self.resize(1060, 700)
        self.setMinimumSize(880, 600)

        # 播放内核（沿用原有 core/music_player.py）
        self.music_player = Music_player()

        # 界面状态
        self._state = "idle"          # idle / playing / paused
        self._current_index = -1
        self._user_dragging = False

        self._build_ui()
        self._bind_shortcuts()

        # 100ms 刷新进度条与时间
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(100)

    # ════════════════════════════════════════
    #  构建界面
    # ════════════════════════════════════════
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        body.addWidget(self._build_sidebar())

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(30, 24, 30, 6)
        right_layout.setSpacing(18)
        right_layout.addLayout(self._build_header())

        self.stack = QStackedWidget()
        self.stack.addWidget(self._build_home_page())          # 0
        self.local_page = LocalMusicPage()
        self.local_page.playRequested.connect(self.play_index)
        self.local_page.tracksChanged.connect(self._on_tracks_changed)
        self.local_page.trackRemoved.connect(self._on_track_removed)
        self.stack.addWidget(self.local_page)                  # 1
        self.stack.addWidget(self._build_placeholder("📋", "我的歌单", "收藏与自建歌单正在开发中"))  # 2
        self.stack.addWidget(self._build_placeholder("⚙", "设置", "主题、音质等选项即将上线"))     # 3
        right_layout.addWidget(self.stack, 1)

        body.addWidget(right, 1)
        root.addLayout(body, 1)
        root.addWidget(self._build_player_bar())

        self._go_page(0)

    # ── 左侧导航 ──
    def _build_sidebar(self):
        side = QFrame()
        side.setObjectName("sidebar")
        side.setFixedWidth(212)

        layout = QVBoxLayout(side)
        layout.setContentsMargins(14, 24, 14, 18)
        layout.setSpacing(6)

        # 品牌区
        brand_row = QHBoxLayout()
        brand_row.setSpacing(10)
        mark = QLabel("♪")
        mark.setObjectName("brand_mark")
        mark.setFixedSize(34, 34)
        mark.setAlignment(Qt.AlignCenter)
        brand_row.addWidget(mark)

        brand_text = QVBoxLayout()
        brand_text.setSpacing(0)
        name = QLabel("Seeker")
        name.setObjectName("brand_name")
        sub = QLabel("MUSIC PLAYER")
        sub.setObjectName("brand_sub")
        brand_text.addWidget(name)
        brand_text.addWidget(sub)
        brand_row.addLayout(brand_text)
        brand_row.addStretch(1)
        layout.addLayout(brand_row)
        layout.addSpacing(22)

        section = QLabel("音  乐  库")
        section.setObjectName("nav_section")
        layout.addWidget(section)
        layout.addSpacing(2)

        # 导航按钮
        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        self.nav_buttons = []
        for i, (icon, text) in enumerate(
            [("🏠", "首页"), ("♫", "本地音乐"), ("📋", "我的歌单"), ("⚙", "设置")]
        ):
            btn = QPushButton(f" {icon}    {text}")
            btn.setObjectName("nav_btn")
            btn.setCheckable(True)
            btn.setChecked(i == 0)
            btn.setFixedHeight(42)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFocusPolicy(Qt.NoFocus)
            self.nav_group.addButton(btn, i)
            self.nav_buttons.append(btn)
            layout.addWidget(btn)
        self.nav_group.buttonClicked[int].connect(self._go_page)

        layout.addStretch(1)

        hint = QLabel("空格  播放 / 暂停\n← →  快退 / 快进 5 秒\nF11  全屏    Esc  退出全屏")
        hint.setObjectName("side_hint")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        layout.addSpacing(8)

        ver = QLabel("v3 · 美化版")
        ver.setObjectName("side_hint")
        layout.addWidget(ver)

        return side

    # ── 顶部标题栏 ──
    def _build_header(self):
        row = QHBoxLayout()
        row.setSpacing(12)

        col = QVBoxLayout()
        col.setSpacing(2)
        self.page_title = QLabel("首页")
        self.page_title.setObjectName("page_title")
        self.page_sub = QLabel("")
        self.page_sub.setObjectName("page_sub")
        col.addWidget(self.page_title)
        col.addWidget(self.page_sub)
        row.addLayout(col)
        row.addStretch(1)

        self.count_chip = QLabel("共 0 首")
        self.count_chip.setObjectName("count_chip")
        row.addWidget(self.count_chip, 0, Qt.AlignVCenter)
        return row

    # ── 首页 ──
    def _build_home_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 8)
        layout.setSpacing(16)

        hero = QFrame()
        hero.setObjectName("hero")
        hero.setMinimumHeight(228)
        apply_shadow(hero, radius=34, dy=10, alpha=110)
        hero_row = QHBoxLayout(hero)
        hero_row.setContentsMargins(34, 32, 38, 30)
        hero_row.setSpacing(24)

        hero_left = QVBoxLayout()
        hero_left.setSpacing(10)
        hero_left.addStretch(1)

        hero_title = QLabel("让音乐陪你度过此刻")
        hero_title.setObjectName("hero_title")
        hero_left.addWidget(hero_title)

        hero_sub = QLabel(
            "Seeker 是一个轻量的本地音乐播放器 —— 无需 ffmpeg，开箱即用。"
        )
        hero_sub.setObjectName("hero_sub")
        hero_sub.setWordWrap(True)
        hero_left.addWidget(hero_sub)

        action_row = QHBoxLayout()
        action_row.setSpacing(14)
        open_btn = QPushButton("打开本地音乐")
        open_btn.setObjectName("primary_btn")
        open_btn.setFixedHeight(40)
        open_btn.setCursor(Qt.PointingHandCursor)
        open_btn.setFocusPolicy(Qt.NoFocus)
        open_btn.clicked.connect(lambda: self._go_page(1))
        action_row.addWidget(open_btn)

        tag = QLabel("点左侧「本地音乐」也可以进入")
        tag.setObjectName("hero_tag")
        action_row.addWidget(tag)
        action_row.addStretch(1)
        hero_left.addLayout(action_row)
        hero_left.addStretch(1)

        hero_row.addLayout(hero_left, 1)

        # 右侧装饰唱片
        disc = QFrame()
        disc.setObjectName("hero_disc")
        disc.setFixedSize(158, 158)
        disc_box = QVBoxLayout(disc)
        disc_box.setContentsMargins(0, 0, 0, 0)
        note = QLabel("♪")
        note.setObjectName("hero_disc_note")
        note.setAlignment(Qt.AlignCenter)
        disc_box.addWidget(note)
        hero_row.addWidget(disc, 0, Qt.AlignRight | Qt.AlignVCenter)

        layout.addWidget(hero, 1)

        cards = QHBoxLayout()
        cards.setSpacing(16)
        for icon, title, desc in [
            ("🎧", "拖拽即播", "把文件拖进窗口，自动加入播放列表"),
            ("⏱", "进度可拖", "点击或拖动进度条即可跳转"),
            ("⌨", "快捷键", "空格播放 / 暂停，F11 全屏"),
        ]:
            cards.addWidget(self._build_card(icon, title, desc), 1)
        layout.addLayout(cards)

        return page

    def _build_card(self, icon, title, desc):
        card = QFrame()
        card.setObjectName("card")
        card.setMinimumHeight(104)
        apply_shadow(card, radius=22, dy=6, alpha=80)

        box = QVBoxLayout(card)
        box.setContentsMargins(18, 16, 18, 16)
        box.setSpacing(4)

        icon_label = QLabel(icon)
        icon_label.setObjectName("card_icon")
        box.addWidget(icon_label)

        title_label = QLabel(title)
        title_label.setObjectName("card_title")
        box.addWidget(title_label)

        desc_label = QLabel(desc)
        desc_label.setObjectName("card_desc")
        desc_label.setWordWrap(True)
        box.addWidget(desc_label)
        box.addStretch(1)
        return card

    # ── 占位页 ──
    def _build_placeholder(self, icon, title, desc):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addStretch(1)

        box = QVBoxLayout()
        box.setSpacing(8)
        icon_label = QLabel(icon)
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setStyleSheet("font-size: 40px;")
        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 18px; font-weight: 600; color: #d8d8ea;")
        desc_label = QLabel(desc)
        desc_label.setAlignment(Qt.AlignCenter)
        desc_label.setObjectName("card_desc")
        box.addWidget(icon_label)
        box.addWidget(title_label)
        box.addWidget(desc_label)
        layout.addLayout(box)
        layout.addStretch(2)
        return page

    # ── 底部播放栏 ──
    def _build_player_bar(self):
        bar = QFrame()
        bar.setObjectName("player_bar")
        bar.setFixedHeight(92)

        row = QHBoxLayout(bar)
        row.setContentsMargins(26, 12, 26, 12)
        row.setSpacing(16)

        # 封面占位
        self.art = QLabel("♪")
        self.art.setObjectName("art")
        self.art.setFixedSize(52, 52)
        self.art.setAlignment(Qt.AlignCenter)
        row.addWidget(self.art)

        # 曲目信息
        info = QVBoxLayout()
        info.setSpacing(2)
        self.song_label = QLabel("未在播放")
        self.song_label.setObjectName("song_label")
        self.song_artist = QLabel("本地音乐")
        self.song_artist.setObjectName("song_artist")
        self.song_label.setMinimumWidth(150)
        self.song_label.setMaximumWidth(240)
        self.song_artist.setMaximumWidth(240)
        info.addStretch(1)
        info.addWidget(self.song_label)
        info.addWidget(self.song_artist)
        info.addStretch(1)
        row.addLayout(info)

        # 进度区
        self.time_label = QLabel("0:00")
        self.time_label.setObjectName("time_label")
        self.time_label.setFixedWidth(42)
        self.time_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self.progress = QSlider(Qt.Horizontal)
        self.progress.setObjectName("progress")
        self.progress.setRange(0, 1000)
        self.progress.setFixedHeight(18)
        self.progress.setCursor(Qt.PointingHandCursor)
        self.progress.wheelEvent = lambda e: None        # 屏蔽滚轮误触
        self.progress.sliderPressed.connect(self._on_slider_pressed)
        self.progress.sliderReleased.connect(self._on_slider_released)
        self._orig_mouse_press = self.progress.mousePressEvent
        self.progress.mousePressEvent = self._on_progress_click

        self.time_total = QLabel("0:00")
        self.time_total.setObjectName("time_total")
        self.time_total.setFixedWidth(42)
        self.time_total.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        progress_row = QHBoxLayout()
        progress_row.setSpacing(8)
        progress_row.addWidget(self.time_label)
        progress_row.addWidget(self.progress, 1)
        progress_row.addWidget(self.time_total)
        row.addLayout(progress_row, 1)

        # 控制按钮
        self.prev_btn = QPushButton("⏮")
        self.prev_btn.setObjectName("ctrl_btn")
        self.prev_btn.setFixedSize(36, 36)
        self.prev_btn.setCursor(Qt.PointingHandCursor)
        self.prev_btn.setFocusPolicy(Qt.NoFocus)
        self.prev_btn.setToolTip("上一首")
        self.prev_btn.setEnabled(False)
        self.prev_btn.clicked.connect(self.previous_track)

        self.play_btn = QPushButton("▶")
        self.play_btn.setObjectName("play_btn")
        self.play_btn.setFixedSize(46, 46)
        self.play_btn.setCursor(Qt.PointingHandCursor)
        self.play_btn.setFocusPolicy(Qt.NoFocus)
        self.play_btn.setToolTip("播放 / 暂停（空格）")
        self.play_btn.setEnabled(False)
        self.play_btn.clicked.connect(self.toggle_play)

        self.next_btn = QPushButton("⏭")
        self.next_btn.setObjectName("ctrl_btn")
        self.next_btn.setFixedSize(36, 36)
        self.next_btn.setCursor(Qt.PointingHandCursor)
        self.next_btn.setFocusPolicy(Qt.NoFocus)
        self.next_btn.setToolTip("下一首")
        self.next_btn.setEnabled(False)
        self.next_btn.clicked.connect(self.next_track)

        row.addWidget(self.prev_btn)
        row.addWidget(self.play_btn)
        row.addWidget(self.next_btn)
        return bar

    # ════════════════════════════════════════
    #  快捷键
    # ════════════════════════════════════════
    def _bind_shortcuts(self):
        self.is_fullscreen = False
        QShortcut(QKeySequence("F11"), self, activated=self.toggle_fullscreen)
        QShortcut(QKeySequence(Qt.Key_Space), self, activated=self.toggle_play)

    def seek_by(self, delta_ms):
        """±5 秒快进 / 快退（左右方向键）。"""
        if not self.music_player.is_load or self._state == "idle":
            return
        target = self.music_player.get_now_position() + delta_ms
        target = max(0, min(target, self.music_player.get_total_duration_ms()))
        self.music_player.seek(target)
        self._user_dragging = False
        self.progress.setValue(int(self.music_player.get_ratio() * 1000))

    # ════════════════════════════════════════
    #  页面切换
    # ════════════════════════════════════════
    def _go_page(self, index):
        index = int(index)
        if not 0 <= index < self.stack.count():
            return
        self.stack.setCurrentIndex(index)
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == index)
        title, sub = self.PAGE_META[index]
        self.page_title.setText(title)
        self.page_sub.setText(sub)
        self._update_count_chip()

    def _update_count_chip(self):
        count = len(self.local_page.tracks) if hasattr(self, "local_page") else 0
        self.count_chip.setText(f"共 {count} 首")

    # ════════════════════════════════════════
    #  播放控制
    # ════════════════════════════════════════
    def play_index(self, index):
        """加载并立即播放播放列表中的某一首。"""
        self._load_track(index, autoplay=True)

    def _load_track(self, index, autoplay):
        """加载某一首；autoplay=False 时只准备好，等用户点播放。"""
        track = self.local_page.track_at(index)
        if track is None:
            return False
        try:
            self.music_player.load_file(track["path"])
        except Exception as exc:
            self.music_player.is_load = False
            self._state = "idle"
            self.play_btn.setEnabled(False)
            self.play_btn.setText("▶")
            QMessageBox.critical(self, "无法播放", f"无法加载音频文件：\n{exc}")
            return False

        self._current_index = index
        self.local_page.set_current(index)
        self.song_label.setText(elide(track["name"]))
        self.song_label.setToolTip(track["name"])
        self.song_artist.setText(elide(os.path.dirname(track["path"]), 40))
        self.song_artist.setToolTip(track["path"])
        self.progress.setValue(0)
        self.time_label.setText("0:00")
        self.time_total.setText(fmt_time(self.music_player.get_total_duration_ms()))
        self.play_btn.setEnabled(True)
        self._state = "idle"
        self.play_btn.setText("▶")
        self._update_nav_controls()
        if autoplay:
            self.toggle_play()          # 双击即播
        return True

    def toggle_play(self):
        if not self.music_player.is_load:
            return
        if self._state == "playing":
            self.music_player.pause()
            self._state = "paused"
            self.play_btn.setText("▶")
        else:
            if self._state == "paused":
                self.music_player.pause()      # 取消暂停，从原位置继续
            else:
                self.music_player.play()       # 从头开始播放
            self._state = "playing"
            self.play_btn.setText("⏸")

    def previous_track(self):
        # 播放超过 3 秒时，先回到本曲开头（贴近主流播放器的手感）
        if self._state in ("playing", "paused") and self.music_player.get_now_position() > 3000:
            self.music_player.seek(0)
            self.progress.setValue(0)
            return
        if self._current_index > 0:
            self.play_index(self._current_index - 1)

    def next_track(self):
        if self._current_index + 1 < len(self.local_page.tracks):
            self.play_index(self._current_index + 1)

    def _update_nav_controls(self):
        total = len(self.local_page.tracks)
        self.prev_btn.setEnabled(self._current_index > 0)
        self.next_btn.setEnabled(0 <= self._current_index < total - 1)

    # ════════════════════════════════════════
    #  进度条交互
    # ════════════════════════════════════════
    def _on_progress_click(self, event):
        if (event.button() == Qt.LeftButton and self.music_player.is_load
                and self._state in ("playing", "paused")):
            ratio = max(0.0, min(1.0, event.x() / max(1, self.progress.width())))
            self.progress.setValue(int(ratio * 1000))
        self._orig_mouse_press(event)

    def _on_slider_pressed(self):
        self._user_dragging = True

    def _on_slider_released(self):
        self._user_dragging = False
        if not self.music_player.is_load or self._state == "idle":
            return
        ratio = self.progress.value() / 1000.0
        self.music_player.seek(int(ratio * self.music_player.get_total_duration_ms()))

    # ════════════════════════════════════════
    #  播放列表变化
    # ════════════════════════════════════════
    def _on_tracks_changed(self):
        self._update_count_chip()
        self._update_nav_controls()
        if not self.local_page.tracks:
            self._reset_player()
        elif self._current_index < 0:
            # 第一次往列表里添歌时，先装载第一首（不自动播放）
            self._load_track(0, autoplay=False)

    def _on_track_removed(self, index):
        if index == self._current_index:
            self._reset_player()
        elif index < self._current_index:
            self._current_index -= 1
            self.local_page.set_current(self._current_index)
        else:
            self.local_page.set_current(self._current_index)
        self._update_nav_controls()
        self._update_count_chip()

    def _reset_player(self):
        self.music_player.stop()
        self._state = "idle"
        self._current_index = -1
        self.local_page.set_current(-1)
        self.song_label.setText("未在播放")
        self.song_artist.setText("本地音乐")
        self.play_btn.setText("▶")
        self.play_btn.setEnabled(False)
        self.prev_btn.setEnabled(False)
        self.next_btn.setEnabled(False)
        self.progress.setValue(0)
        self.time_label.setText("0:00")
        self.time_total.setText("0:00")

    # ════════════════════════════════════════
    #  定时刷新
    # ════════════════════════════════════════
    def _tick(self):
        # 列表为空 / 没有选中曲目时，保持播放栏的复位状态
        if self._current_index < 0:
            return

        # 自然播放结束 → 自动下一首，否则复位
        if self.music_player.is_finished:
            self.music_player.is_finished = False
            if self._current_index >= 0 and self._current_index + 1 < len(self.local_page.tracks):
                self.play_index(self._current_index + 1)
            else:
                self._state = "idle"
                self.play_btn.setText("▶")

        pos = self.music_player.get_now_position()
        dur = self.music_player.get_total_duration_ms()
        self.time_label.setText(fmt_time(pos))
        self.time_total.setText(fmt_time(dur))
        if not self._user_dragging:
            self.progress.setValue(int(self.music_player.get_ratio() * 1000))

    # ════════════════════════════════════════
    #  窗口事件
    # ════════════════════════════════════════
    def toggle_fullscreen(self):
        if self.is_fullscreen:
            self.showNormal()
        else:
            self.showFullScreen()
        self.is_fullscreen = not self.is_fullscreen

    def keyPressEvent(self, event):
        # 列表获得焦点时方向键留给列表本身，其余情况下左右键用于快进 / 快退
        if event.key() == Qt.Key_Escape and self.is_fullscreen:
            self.toggle_fullscreen()
        elif event.key() == Qt.Key_Left:
            self.seek_by(-5000)
        elif event.key() == Qt.Key_Right:
            self.seek_by(5000)
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event):
        self.timer.stop()
        if hasattr(self, "music_player"):
            self.music_player.close()
        event.accept()


# ═══════════════════════════════════════════════════════════
#  入口
# ═══════════════════════════════════════════════════════════
def load_stylesheet(app):
    qss_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "style_v3.qss")
    if os.path.exists(qss_path):
        with open(qss_path, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())


def main():
    if hasattr(Qt, "AA_EnableHighDpiScaling"):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    if hasattr(Qt, "AA_UseHighDpiPixmaps"):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)

    app = QApplication(sys.argv)
    app.setStyle("Fusion")          # 统一基线样式，保证 QSS 效果稳定
    load_stylesheet(app)

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
