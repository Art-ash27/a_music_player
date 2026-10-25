"""本地音乐页 · v3

相比 local_page / local_page_v2 的变化（均为新增文件，未改动旧版本）：
- 支持一次选择多个文件，形成播放列表
- 支持把音频文件直接拖进窗口
- 双击列表中的歌曲播放，右键可播放 / 移除
- 列表与当前播放状态有高亮联动
"""
import os

from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QFileDialog, QListWidget, QListWidgetItem, QMenu, QStackedWidget,
    QAbstractItemView, QSizePolicy,
)

AUDIO_EXTS = (".mp3", ".wav", ".ogg", ".flac", ".m4a", ".aac", ".wma")


class LocalMusicPage(QWidget):
    """本地音乐页面。

    对外信号：
        playRequested(int)   请求播放某个下标
        tracksChanged()      列表内容发生变化
        trackRemoved(int)    某个下标被移除
    """

    playRequested = pyqtSignal(int)
    tracksChanged = pyqtSignal()
    trackRemoved = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.tracks = []          # [{"path": str, "name": str}, ...]
        self._current = -1

        self.setAcceptDrops(True)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)

        # ── 工具栏 ──
        bar = QHBoxLayout()
        bar.setSpacing(10)

        self.tip_label = QLabel("双击列表中的歌曲即可播放，也可以把文件拖进窗口")
        self.tip_label.setObjectName("page_sub")
        bar.addWidget(self.tip_label)
        bar.addStretch(1)

        self.clear_btn = QPushButton("清空列表")
        self.clear_btn.setObjectName("ghost_btn")
        self.clear_btn.setFixedHeight(36)
        self.clear_btn.setCursor(Qt.PointingHandCursor)
        self.clear_btn.clicked.connect(self.clear_tracks)
        bar.addWidget(self.clear_btn)

        self.add_btn = QPushButton("＋  添加音乐")
        self.add_btn.setObjectName("primary_btn")
        self.add_btn.setFixedHeight(36)
        self.add_btn.setCursor(Qt.PointingHandCursor)
        self.add_btn.clicked.connect(self.select_files)
        bar.addWidget(self.add_btn)

        root.addLayout(bar)

        # ── 空状态 / 列表 ──
        self.stack = QStackedWidget()
        self.stack.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.hint_label = QFrame()
        self.hint_label.setObjectName("list_hint")
        hint_box = QVBoxLayout(self.hint_label)
        hint_box.setContentsMargins(24, 24, 24, 24)
        hint_box.setSpacing(6)
        hint_box.addStretch(1)

        hint_icon = QLabel("🎧")
        hint_icon.setObjectName("hint_icon")
        hint_icon.setAlignment(Qt.AlignCenter)
        hint_box.addWidget(hint_icon)

        hint_title = QLabel("播放列表还是空的")
        hint_title.setObjectName("hint_title")
        hint_title.setAlignment(Qt.AlignCenter)
        hint_box.addWidget(hint_title)
        hint_box.addSpacing(2)

        hint_desc = QLabel("把音频文件拖到这里，或点击右上角「添加音乐」")
        hint_desc.setObjectName("card_desc")
        hint_desc.setAlignment(Qt.AlignCenter)
        hint_desc.setWordWrap(True)
        hint_box.addWidget(hint_desc)

        hint_formats = QLabel("支持 MP3 / WAV / OGG / FLAC / M4A")
        hint_formats.setObjectName("hint_formats")
        hint_formats.setAlignment(Qt.AlignCenter)
        hint_box.addWidget(hint_formats)

        hint_box.addStretch(1)

        self.list_widget = QListWidget()
        self.list_widget.setObjectName("track_list")
        self.list_widget.setFrameShape(QListWidget.NoFrame)
        self.list_widget.setSpacing(2)
        self.list_widget.setSelectionMode(QAbstractItemView.SingleSelection)
        self.list_widget.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.list_widget.setAcceptDrops(False)
        self.list_widget.setDragDropMode(QAbstractItemView.NoDragDrop)
        self.list_widget.itemDoubleClicked.connect(self._on_double_click)
        self.list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self._show_menu)

        self.stack.addWidget(self.hint_label)
        self.stack.addWidget(self.list_widget)
        root.addWidget(self.stack, 1)

        self._refresh()

    # ════════════════════════════════════════════════
    #  列表操作
    # ════════════════════════════════════════════════
    def add_files(self, paths):
        """加入一批文件（自动跳过重复与不支持的格式）。"""
        added = 0
        exist = {t["path"] for t in self.tracks}
        for path in paths:
            path = os.path.abspath(path)
            if not os.path.isfile(path) or path in exist:
                continue
            if not path.lower().endswith(AUDIO_EXTS):
                continue
            self.tracks.append({"path": path, "name": os.path.basename(path)})
            exist.add(path)
            added += 1
        if added:
            self._refresh()
            self.tracksChanged.emit()
            if len(self.tracks) == added:          # 第一次添加自动选中首曲
                self.list_widget.setCurrentRow(0)
        return added

    def select_files(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "选择音频文件",
            "",
            "音频文件 (*.mp3 *.wav *.ogg *.flac *.m4a *.aac *.wma);;所有文件 (*)",
        )
        if paths:
            self.add_files(paths)

    def clear_tracks(self):
        if not self.tracks:
            return
        self.tracks.clear()
        self._current = -1
        self._refresh()
        self.tracksChanged.emit()

    def remove_at(self, index):
        if not 0 <= index < len(self.tracks):
            return
        self.tracks.pop(index)
        self._refresh()
        self.trackRemoved.emit(index)
        self.tracksChanged.emit()

    def track_at(self, index):
        if 0 <= index < len(self.tracks):
            return self.tracks[index]
        return None

    def set_current(self, index):
        """高亮当前播放的歌曲。"""
        self._current = index
        self._render_rows()

    # ════════════════════════════════════════════════
    #  渲染
    # ════════════════════════════════════════════════
    def _refresh(self):
        self.stack.setCurrentWidget(self.list_widget if self.tracks else self.hint_label)
        self.clear_btn.setEnabled(bool(self.tracks))
        self._render_rows()

    def _render_rows(self):
        self.list_widget.clear()
        for i, track in enumerate(self.tracks):
            if i == self._current:
                text = f"▶    {track['name']}"
            else:
                text = f"{i + 1:02d}    {track['name']}"
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, i)
            item.setSizeHint(QSize(0, 44))
            item.setToolTip(track["path"])
            if i == self._current:
                item.setForeground(QColor("#c4b5fd"))
            self.list_widget.addItem(item)

        # 重新渲染后恢复当前曲目的选中态（例如播放中又添加了歌曲）
        if 0 <= self._current < self.list_widget.count():
            self.list_widget.setCurrentRow(self._current)

    # ════════════════════════════════════════════════
    #  交互
    # ════════════════════════════════════════════════
    def _on_double_click(self, item):
        index = item.data(Qt.UserRole)
        if index is not None:
            self.playRequested.emit(int(index))

    def _show_menu(self, pos):
        item = self.list_widget.itemAt(pos)
        if item is None:
            return
        index = int(item.data(Qt.UserRole))
        menu = QMenu(self)
        act_play = menu.addAction("播放")
        menu.addSeparator()
        act_remove = menu.addAction("从列表移除")
        chosen = menu.exec_(self.list_widget.mapToGlobal(pos))
        if chosen is act_play:
            self.playRequested.emit(index)
        elif chosen is act_remove:
            self.remove_at(index)

    # ── 拖拽添加 ──
    def _audio_paths(self, urls):
        paths = []
        for url in urls:
            if url.isLocalFile():
                path = url.toLocalFile()
                if path.lower().endswith(AUDIO_EXTS):
                    paths.append(path)
        return paths

    def dragEnterEvent(self, event):
        if self._audio_paths(event.mimeData().urls()):
            event.acceptProposedAction()
            self.hint_label.setProperty("dropActive", True)
            self._repolish_hint()
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self.hint_label.setProperty("dropActive", False)
        self._repolish_hint()
        super().dragLeaveEvent(event)

    def dropEvent(self, event):
        paths = self._audio_paths(event.mimeData().urls())
        self.hint_label.setProperty("dropActive", False)
        self._repolish_hint()
        if paths:
            self.add_files(paths)
            event.acceptProposedAction()
        else:
            event.ignore()

    def _repolish_hint(self):
        self.hint_label.style().unpolish(self.hint_label)
        self.hint_label.style().polish(self.hint_label)
