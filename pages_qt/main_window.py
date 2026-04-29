import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QGridLayout,
    QShortcut, QVBoxLayout, QPushButton,
    QLabel, QFrame, QHBoxLayout,QMessageBox,QSlider
)
from PyQt5.QtCore import Qt,QTimer
from PyQt5.QtGui import QKeySequence
from core.music_player import Music_player
from pages_qt.local_page import LocalMusicPage



class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Seeker播放器")
        self.resize(900, 600)
        self.setMinimumSize(700, 500)
        #创建一个100ms的定时器
        self.process_qt = QTimer(self)
        self.process_qt.timeout.connect(self.update_fortime)
        self.process_qt.start(100)
            
        # 创建全局播放器实例（所有页面共享）
        self.music_player = Music_player()
        

        # 主布局...
        self.main_layout = QGridLayout()
        self.main_layout.setSpacing(0)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.main_layout)

        # 左侧导航（不变）
        self.nav_widget = QWidget()
        self.nav_widget.setFixedWidth(180)
        nav_layout = QVBoxLayout()
        nav_layout.setSpacing(5)
        nav_layout.setContentsMargins(10, 20, 10, 10)

        self.btn_home = QPushButton("首页")
        self.btn_local = QPushButton("本地音乐") 
        self.btn_list = QPushButton("我的歌单")
        self.btn_settings = QPushButton("设置")

        for btn in [self.btn_home, self.btn_local, self.btn_list, self.btn_settings]:
            btn.setFixedHeight(40)
            nav_layout.addWidget(btn)
        nav_layout.addStretch(1)
        self.nav_widget.setLayout(nav_layout)

        # 👇 初始化默认页面（首页）
        self.content_widget = QLabel("欢迎使用 Seeker 播放器\n点击左侧导航开始")
        self.content_widget.setAlignment(Qt.AlignCenter)

        # 底部播放栏（不变）
        self.pause = False
        self.player_bar = QFrame()
        self.player_bar.setFixedHeight(80)
        self.player_bar.setStyleSheet("background-color: #2c3e50; color: white;")
        player_layout = QHBoxLayout()
        player_layout.setContentsMargins(15, 0, 15, 0)
        self.song_label = QLabel("未播放任何歌曲")

        #利用滑块制作进度条
        self.progress_widget = QWidget()
        self.progress_bar = QVBoxLayout(self.progress_widget)
        self.progress_bar.setContentsMargins(0,32,0,2)


        self.progress = QSlider()
        self.music_time =QLabel("00:00/00:00")
        self.progress.setMinimum(0)
        self.progress.setMaximum(1000)
        self.progress.setOrientation(Qt.Horizontal)
        self.progress.wheelEvent = lambda e: None  # 屏蔽鼠标滚轮
        self.progress_bar.addWidget(self.progress)
        self.progress_bar.addWidget(self.music_time)

        self.play_btn = QPushButton("▶")
        self.play_btn.setEnabled(False)
        player_layout.addWidget(self.song_label)
        player_layout.addWidget(self.progress_widget)
        player_layout.addWidget(self.play_btn)
        self.player_bar.setLayout(player_layout)

        # 添加到网格
        self.main_layout.addWidget(self.nav_widget, 0, 0)
        self.main_layout.addWidget(self.content_widget, 0, 1)
        self.main_layout.addWidget(self.player_bar, 1, 0, 1, 2)
        self.main_layout.setColumnStretch(1, 1)

        # 全屏快捷键（不变）
        self.fullscreen_shortcut = QShortcut(QKeySequence("F11"), self)
        self.fullscreen_shortcut.activated.connect(self.toggle_fullscreen)
        self.is_fullscreen = False

        # 👇 连接导航按钮
        self.btn_local.clicked.connect(self.show_local_music)

        # 👇 连接底部播放按钮
        self.play_btn.clicked.connect(self.toggle_global_play)

        # 播放状态
        self.global_play_state = "stopped"

        # 用户拖动进度条标志（防止定时器覆盖用户拖动位置）
        self._user_dragging = False
        self.progress.sliderPressed.connect(self.on_slider_pressed)
        self.progress.sliderReleased.connect(self.on_slider_released)

        # 点击轨道 → 仅移动滑块，seek 统一在 sliderReleased 中执行
        self._orig_progress_mousePress = self.progress.mousePressEvent
        def click_jump(event):
            if self.global_play_state == "stopped":
                return
            if event.button() == Qt.LeftButton and self.music_player.is_load:
                ratio = max(0.0, min(1.0, event.x() / self.progress.width()))
                self.progress.setValue(int(ratio * 1000))
            self._orig_progress_mousePress(event)
        self.progress.mousePressEvent = click_jump

    def on_slider_pressed(self):
        """用户开始拖动进度条，暂停定时器刷新"""
        self._user_dragging = True

    def on_slider_released(self):
        """用户释放进度条，统一执行 seek"""
        if not self.music_player.is_load:
            self._user_dragging = False
            return
        ratio = self.progress.value() / 1000.0
        total_ms = self.music_player.get_total_duration_ms()
        target_ms = int(ratio * total_ms)
        self.music_player.seek(target_ms)
        self._user_dragging = False

    def show_local_music(self):
        """切换到本地音乐页面"""
        # 删除旧内容
        if hasattr(self, 'content_widget') and self.content_widget:
            self.main_layout.removeWidget(self.content_widget)
            self.content_widget.deleteLater()

        # 创建新页面
        self.content_widget = LocalMusicPage(
            on_file_selected=self.load_music  # 回调
        )
        self.main_layout.addWidget(self.content_widget, 0, 1)

    def load_music(self,file_path,filename):
        try:
            self.music_player.load_file(file_path)
            self.song_label.setText(f"🎵{filename}")
            self.play_btn.setEnabled(True)
            self.global_play_state = "stopped"
            self.play_btn.setText("▶️")

        except Exception as e:
            QMessageBox.critical(self,"错误",f"无法加载音频文件:\n{str(e)}")
            self.play_btn.setEnabled(False)


    def toggle_global_play(self):
        """底部播放/暂停按钮"""
        if not self.music_player.load_file:
            return

        if self.global_play_state == "stopped":
            self.music_player.play()
            self.pause = False
            self.global_play_state = "playing"
            self.play_btn.setText("⏸ ")
        elif self.global_play_state=="playing":
            self.music_player.pause()
            self.pause = True
            self.global_play_state = "pause"
            self.play_btn.setText("▶")
        elif self.global_play_state=="pause":
            self.music_player.pause()
            self.pause = True
            self.global_play_state = "playing"
            self.play_btn.setText("⏸")

    def toggle_fullscreen(self):
        if self.is_fullscreen:
            self.showNormal()
            self.is_fullscreen = False
        else:
            self.showFullScreen()
            self.is_fullscreen = True

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape and self.is_fullscreen:
            self.toggle_fullscreen()
        else:
            super().keyPressEvent(event)
    
    def closeEvent(self,event):
        if hasattr(self,'music_player'):
            self.music_player.stop()
            self.music_player.audio_init.terminate()
        event.accept()

    #按时刷新进度条
    def update_fortime(self):
        self.music_time.setText(f"{self.music_player.get_now_position()//60000}:{self.music_player.get_now_position()//1000%60:02d}/{self.music_player.get_total_duration_ms()//60000}:{self.music_player.get_total_duration_ms()//1000%60:02d}")
        if not self._user_dragging:
            self.progress.setValue(int(self.music_player.get_ratio()*1000))


def main():
    if hasattr(Qt, 'AA_EnableHighDpiScaling'):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
