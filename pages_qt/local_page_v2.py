# pages_qt/local_page_v2.py
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
        layout.setContentsMargins(40, 48, 40, 40)
        layout.setSpacing(20)

        # 标题
        title = QLabel("本地音乐")
        title.setObjectName("page_title")
        layout.addWidget(title)

        # 信息展示卡片
        self.info_label = QLabel("点击下方按钮选择音频文件")
        self.info_label.setObjectName("info_label")
        self.info_label.setAlignment(Qt.AlignCenter)
        self.info_label.setMinimumHeight(80)
        layout.addWidget(self.info_label)

        layout.addStretch(1)

        # 选择按钮（居中）
        self.select_btn = QPushButton("选择音乐文件")
        self.select_btn.setObjectName("select_btn")
        self.select_btn.setFixedWidth(180)
        self.select_btn.setCursor(Qt.PointingHandCursor)

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
        if file_path and os.path.isfile(file_path):
            filename = os.path.basename(file_path)
            self.info_label.setText(f"{filename}")
            self.on_file_selected(file_path, filename)
