# pages_qt/local_music_page.py
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton,
    QFileDialog, QMessageBox, QHBoxLayout
)
from PyQt5.QtCore import Qt
import os


class LocalMusicPage(QWidget):
    def __init__(self, on_file_selected):
        """
        :param on_file_selected: 回调函数，传入 (file_path, filename)
        """
        super().__init__()
        self.on_file_selected = on_file_selected

        layout = QVBoxLayout()
        layout.setContentsMargins(30, 40, 30, 40)

        title = QLabel("🎵 本地音乐")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)

        self.info_label = QLabel("请选择一个音频文件")
        self.info_label.setAlignment(Qt.AlignCenter)
        self.info_label.setStyleSheet("font-size: 14px; color: #666;")
        layout.addWidget(self.info_label)

        layout.addStretch(1)

        # 只有一个按钮
        self.select_btn = QPushButton("📂 选择音乐文件")
        self.select_btn.setFixedWidth(180)
        btn_layout = QHBoxLayout()
        btn_layout.addStretch(1)
        btn_layout.addWidget(self.select_btn)
        btn_layout.addStretch(1)
        layout.addLayout(btn_layout)

        layout.addStretch(2)
        self.setLayout(layout)

        self.select_btn.clicked.connect(self.select_file)

    def select_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择音频文件",
            "",
            "音频文件 (*.mp3 *.wav *.ogg *.flac *.m4a);;所有文件 (*)"
        )
        for i in range(10): print(file_path)   #测试能否正常切歌
        if file_path and os.path.isfile(file_path):
            filename = os.path.basename(file_path)
            self.info_label.setText(f"已加载：\n{filename}")
            self.on_file_selected(file_path,filename)  # 通知主窗口