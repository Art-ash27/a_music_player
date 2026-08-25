"""
基于 miniaudio 的播放内核(替代 pyaudio + pydub)。

- miniaudio 自带 MP3 / FLAC / WAV / OGG 解码, 不再依赖 ffmpeg / PortAudio 等外部程序。
- 播放采用 PlaybackDevice + 生成器回调, 支持播放 / 暂停 / 跳转 / 停止。
- 对外接口与原 Music_player 保持一致:
    load_file / play / pause / seek / stop / close
    is_load / is_playing / is_pause / is_finished
    get_total_duration_ms / get_now_position / get_ratio
"""
import threading

import miniaudio
from miniaudio import SampleFormat


class Music_player:
    def __init__(self):
        self.device = None               # miniaudio.PlaybackDevice 实例
        self.current_audio = None        # 解码后的 miniaudio.DecodedSoundFile。
        self._view = None                # 解码后 PCM 的字节视图(零拷贝切片)
        self.is_load = False             # 是否已成功加载音频
        self.is_playing = False          # 正在播放标志
        self.is_pause = False            # 暂停标志
        self.is_finished = False         # 自然播放结束标志(供界面复位状态)
        self._seek_request = None        # 跳转请求(目标字节偏移, 由播放生成器消费)
        self._frame_size = 4             # 每帧字节数 = 声道数 * 采样宽度
        self._lock = threading.Lock()
        self._long = 0                   # PCM 总字节数
        self._now_position = 0           # 已播放字节数(设备线程中刷新)

    # ────────────────────────────────────────────
    #  加载
    # ────────────────────────────────────────────
    def load_file(self, filepath):
        if self.is_load:
            self.current_audio = None
            self.stop()

        try:
            info = miniaudio.get_file_info(filepath)
            decoded = miniaudio.decode_file(
                filepath,
                output_format=SampleFormat.SIGNED16,
                nchannels=info.nchannels,
                sample_rate=info.sample_rate,
            )
        except miniaudio.DecodeError as exc:
            raise ValueError(
                "无法解码该音频文件(仅支持 mp3 / wav / ogg / flac): %s" % exc
            ) from exc

        self.current_audio = decoded
        self._view = memoryview(decoded.samples).cast("B")
        self._frame_size = decoded.nchannels * decoded.sample_width
        self._long = len(self._view)
        self._now_position = 0
        self.is_finished = False
        self.is_load = True

    # ────────────────────────────────────────────
    #  查询
    # ────────────────────────────────────────────
    def get_total_duration_ms(self):  # 获取总长度 ms
        audio = self.current_audio
        if not audio or audio.sample_rate <= 0:
            return 0
        return int(audio.num_frames / audio.sample_rate * 1000)

    def get_ratio(self):  # 已播放与全长的比例 [0, 1]
        if not self.current_audio or self._long == 0:
            return 0.0
        return min(1.0, self._now_position / self._long)

    def get_now_position(self):  # 当前播放位置 ms
        if not self.current_audio or self._long == 0:
            return 0
        return int(self.get_ratio() * self.get_total_duration_ms())

    # ────────────────────────────────────────────
    #  播放内核: 设备线程中运行的生成器
    # ────────────────────────────────────────────
    def _playback_generator(self):
        """被 PlaybackDevice 回调驱动: 每次 send(framecount) 返回对应帧数的 PCM 数据。

        必须先 next() 预热再传给 device.start(); 生成器绝不主动抛异常,
        出错/暂停/播完时一律输出静音, 避免设备线程崩溃。
        """
        view = self._view
        frame_size = self._frame_size
        total = len(view)

        def silence(want_frames):
            return b"\x00" * (max(want_frames, 1) * frame_size)

        want = 0
        try:
            want = yield b""            # 预热
            while True:
                with self._lock:
                    if self._seek_request is not None:
                        self._now_position = self._seek_request
                        self._seek_request = None
                    offset = self._now_position
                    playing = self.is_playing
                    paused = self.is_pause

                if not playing:         # 收到 stop 请求
                    break
                if paused:              # 暂停: 设备保持运行, 输出静音
                    want = yield silence(want)
                    continue
                if offset >= total:     # 自然播完: 复位并输出静音
                    self.is_playing = False
                    self.is_finished = True
                    self._now_position = 0
                    want = yield silence(want)
                    continue

                end = min(offset + want * frame_size, total)
                chunk = view[offset:end]
                self._now_position = end
                want = yield chunk
        except GeneratorExit:
            raise
        except Exception:
            # 设备回调线程内不允许抛出异常, 出错时转为静音
            self.is_playing = False
            self.is_finished = True
            try:
                while True:
                    want = yield silence(want)
            except GeneratorExit:
                raise

    def _get_device(self, nchannels, sample_rate):
        """复用参数匹配的播放设备, 否则重建一个。"""
        d = self.device
        if d is not None and d.nchannels == nchannels and d.sample_rate == sample_rate:
            if d.running:
                d.stop()
            return d
        if d is not None:
            try:
                d.close()
            except Exception:
                pass
        self.device = miniaudio.PlaybackDevice(
            output_format=SampleFormat.SIGNED16,
            nchannels=nchannels,
            sample_rate=sample_rate,
            buffersize_msec=50,
        )
        return self.device

    # ────────────────────────────────────────────
    #  播放控制
    # ────────────────────────────────────────────
    def play(self):
        if not self.is_load or self.is_playing:
            return

        audio = self.current_audio
        self.is_playing = True
        self.is_pause = False
        self.is_finished = False
        self._now_position = 0

        device = self._get_device(audio.nchannels, audio.sample_rate)
        gen = self._playback_generator()
        next(gen)                       # 预热生成器
        try:
            device.start(gen)
        except Exception:
            self.is_playing = False
            raise

    def pause(self):
        self.is_pause = not self.is_pause

    def seek(self, ms):
        if not self.is_load or self._long == 0:
            return
        total_ms = self.get_total_duration_ms()
        if total_ms <= 0:
            return
        ratio = max(0.0, min(1.0, ms / total_ms))
        target_byte = int(ratio * self._long)
        target_byte = (target_byte // self._frame_size) * self._frame_size
        with self._lock:
            self._seek_request = target_byte

    def stop(self):
        self.is_playing = False
        self.is_pause = False
        self.is_finished = False
        with self._lock:
            self._seek_request = None
        self._now_position = 0
        d = self.device
        if d is not None and d.running:
            try:
                d.stop()
            except Exception:
                pass

    def close(self):
        """停止播放并关闭音频设备(替代旧的 audio_init.terminate())。"""
        self.stop()
        d, self.device = self.device, None
        if d is not None:
            try:
                d.close()
            except Exception:
                pass

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass
