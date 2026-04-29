#DS自动创建GUI


import sys
import os
from PyQt5.QtWidgets import (
    QApplication, QWidget, QGridLayout,
    QShortcut, QVBoxLayout, QPushButton,
    QLabel, QFrame, QHBoxLayout, QMessageBox, QSlider
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QKeySequence
from core.music_player import Music_player
from pages_qt.local_page_v2 import LocalMusicPage


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Seeker 播放器")
        self.resize(900, 600)
        self.setMinimumSize(700, 500)

        # 定时器 — 100ms 刷新进度条和时间
        self.process_qt = QTimer(self)
        self.process_qt.timeout.connect(self.update_fortime)
        self.process_qt.start(100)

        # 全局播放器实例
        self.music_player = Music_player()

        # ── 主布局 ──
        self.main_layout = QGridLayout()
        self.main_layout.setSpacing(0)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.main_layout)

        # ── 左侧导航 ──
        self._setup_nav()

        # ── 内容区域（默认首页） ──
        self.content_widget = QLabel("Seeker · 音乐播放器")
        self.content_widget.setObjectName("welcome_label")       # QSS 选择器
        self.content_widget.setAlignment(Qt.AlignCenter)

        # ── 底部播放栏 ──
        self._setup_player_bar()

        # ── 网格布局 ──
        self.main_layout.addWidget(self.nav_widget, 0, 0)
        self.main_layout.addWidget(self.content_widget, 0, 1)
        self.main_layout.addWidget(self.player_bar, 1, 0, 1, 2)
        self.main_layout.setColumnStretch(1, 1)

        # ── 快捷键 ──
        self.fullscreen_shortcut = QShortcut(QKeySequence("F11"), self)
        self.fullscreen_shortcut.activated.connect(self.toggle_fullscreen)
        self.is_fullscreen = False

        # ── 导航按钮绑定 ──
        self.btn_local.clicked.connect(self.show_local_music)

        # ── 播放按钮绑定 ──
        self.global_play_state = "stopped"
        self.play_btn.clicked.connect(self.toggle_global_play)

        # ── 进度条交互逻辑 ──
        self._setup_progress_interaction()

    # ════════════════════════════════════════
    #  左侧导航
    # ════════════════════════════════════════
    def _setup_nav(self):
        self.nav_widget = QWidget()
        self.nav_widget.setObjectName("nav_widget")
        self.nav_widget.setFixedWidth(180)

        nav_layout = QVBoxLayout()
        nav_layout.setSpacing(6)
        nav_layout.setContentsMargins(12, 24, 12, 16)

        # Logo / 品牌名
        brand = QLabel("Seeker")
        brand.setStyleSheet(
            "font-size: 20px; font-weight: 700; color: #c8c8d8;"
            "padding: 4px 8px 16px 8px; letter-spacing: 2px;"
        )
        nav_layout.addWidget(brand)

        # 分隔线
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: #2a2a32;")
        nav_layout.addWidget(sep)
        nav_layout.addSpacing(8)

        # 导航按钮
        self.btn_home = QPushButton("🏠  首页")
        self.btn_local = QPushButton("🎵  本地音乐")
        self.btn_list = QPushButton("📋  我的歌单")
        self.btn_settings = QPushButton("⚙  设置")

        for btn in [self.btn_home, self.btn_local, self.btn_list, self.btn_settings]:
            btn.setObjectName("nav_btn")
            btn.setFixedHeight(42)
            btn.setCursor(Qt.PointingHandCursor)
            nav_layout.addWidget(btn)

        nav_layout.addStretch(1)

        # 底部版本号
        ver = QLabel("v1.0")
        ver.setStyleSheet("font-size: 11px; color: #3a3a45; padding: 8px;")
        ver.setAlignment(Qt.AlignCenter)
        nav_layout.addWidget(ver)

        self.nav_widget.setLayout(nav_layout)

    # ════════════════════════════════════════
    #  底部播放栏
    # ════════════════════════════════════════
    def _setup_player_bar(self):
        self.player_bar = QFrame()
        self.player_bar.setObjectName("player_bar")
        self.player_bar.setFixedHeight(72)

        player_layout = QHBoxLayout()
        player_layout.setContentsMargins(16, 0, 16, 0)
        player_layout.setSpacing(12)

        # 歌曲名称
        self.song_label = QLabel("未在播放")
        self.song_label.setObjectName("song_label")
        self.song_label.setMinimumWidth(140)

        # 进度条区域（滑块 + 时间）
        self.progress_widget = QWidget()
        progress_layout = QVBoxLayout(self.progress_widget)
        progress_layout.setContentsMargins(0, 10, 0, 4)
        progress_layout.setSpacing(2)

        self.progress = QSlider()
        self.progress.setOrientation(Qt.Horizontal)
        self.progress.setMinimum(0)
        self.progress.setMaximum(1000)
        self.progress.wheelEvent = lambda e: None          # 屏蔽滚轮

        self.music_time = QLabel("00:00 / 00:00")
        self.music_time.setObjectName("time_label")
        self.music_time.setAlignment(Qt.AlignCenter)

        progress_layout.addWidget(self.progress)
        progress_layout.addWidget(self.music_time)

        # 播放按钮
        self.play_btn = QPushButton("▶")
        self.play_btn.setObjectName("play_btn")
        self.play_btn.setEnabled(False)
        self.play_btn.setCursor(Qt.PointingHandCursor)

        player_layout.addWidget(self.song_label)
        player_layout.addWidget(self.progress_widget, 1)   # stretch=1 撑满
        player_layout.addWidget(self.play_btn)

        self.player_bar.setLayout(player_layout)

    # ════════════════════════════════════════
    #  进度条交互（点击 / 拖动均松开鼠标时统一 seek）
    # ════════════════════════════════════════
    def _setup_progress_interaction(self):
        self._user_dragging = False

        self.progress.sliderPressed.connect(self._on_slider_pressed)
        self.progress.sliderReleased.connect(self._on_slider_released)

        # 点击轨道 → 仅移动滑块（不 seek），seek 统一在 sliderReleased 中执行
        self._orig_mouse = self.progress.mousePressEvent

        def click_jump(event):
            if self.global_play_state == "stopped":
                return
            if event.button() == Qt.LeftButton and self.music_player.is_load:
                ratio = max(0.0, min(1.0, event.x() / self.progress.width()))
                self.progress.setValue(int(ratio * 1000))
            self._orig_mouse(event)

        self.progress.mousePressEvent = click_jump

    def _on_slider_pressed(self):
        self._user_dragging = True

    def _on_slider_released(self):
        if not self.music_player.is_load:
            self._user_dragging = False
            return

        ratio = self.progress.value() / 1000.0
        target_ms = int(ratio * self.music_player.get_total_duration_ms())
        self.music_player.seek(target_ms)
        self._user_dragging = False

    # ════════════════════════════════════════
    #  页面切换
    # ════════════════════════════════════════
    def show_local_music(self):
        if hasattr(self, 'content_widget') and self.content_widget:
            self.main_layout.removeWidget(self.content_widget)
            self.content_widget.deleteLater()

        self.content_widget = LocalMusicPage(
            on_file_selected=self.load_music
        )
        self.main_layout.addWidget(self.content_widget, 0, 1)

    # ════════════════════════════════════════
    #  加载音乐文件
    # ════════════════════════════════════════
    def load_music(self, file_path, filename):
        try:
            self.music_player.load_file(file_path)
            self.song_label.setText(filename)
            self.play_btn.setEnabled(True)
            self.global_play_state = "stopped"
            self.play_btn.setText("▶")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法加载音频文件:\n{str(e)}")
            self.play_btn.setEnabled(False)

    # ════════════════════════════════════════
    #  播放 / 暂停
    # ════════════════════════════════════════
    def toggle_global_play(self):
        if not self.music_player.is_load:
            return

        if self.global_play_state == "stopped":
            self.music_player.play()
            self.global_play_state = "playing"
            self.play_btn.setText("⏸")
        elif self.global_play_state == "playing":
            self.music_player.pause()
            self.global_play_state = "paused"
            self.play_btn.setText("▶")
        elif self.global_play_state == "paused":
            self.music_player.pause()
            self.global_play_state = "playing"
            self.play_btn.setText("⏸")

    # ════════════════════════════════════════
    #  全屏切换
    # ════════════════════════════════════════
    def toggle_fullscreen(self):
        if self.is_fullscreen:
            self.showNormal()
            self.is_fullscreen = False
        else:
            self.showFullScreen()
            self.is_fullscreen = True

    # ════════════════════════════════════════
    #  事件
    # ════════════════════════════════════════
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape and self.is_fullscreen:
            self.toggle_fullscreen()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event):
        if hasattr(self, 'music_player'):
            self.music_player.stop()
            self.music_player.audio_init.terminate()
        event.accept()

    # ════════════════════════════════════════
    #  定时刷新进度条
    # ════════════════════════════════════════
    def update_fortime(self):
        # 更新时间文字
        pos = self.music_player.get_now_position()
        dur = self.music_player.get_total_duration_ms()
        self.music_time.setText(
            f"{pos // 60000}:{(pos // 1000) % 60:02d} / "
            f"{dur // 60000}:{(dur // 1000) % 60:02d}"
        )
        # 更新滑块位置
        if not self._user_dragging:
            self.progress.setValue(int(self.music_player.get_ratio() * 1000))


# ═══════════════════════════════════════════
#  程序入口 — 加载 QSS 样式表
# ═══════════════════════════════════════════
def main():
    if hasattr(Qt, 'AA_EnableHighDpiScaling'):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)

    app = QApplication(sys.argv)

    # 加载 QSS 样式表
    qss_path = os.path.join(os.path.dirname(__file__), "..", "resource", "style.qss")
    if os.path.exists(qss_path):
        with open(qss_path, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
