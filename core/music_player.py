import threading
import pyaudio
from pydub import AudioSegment
import time
from core.music_info import MusicInfoManager

class Music_player:
    def __init__(self):
        self.audio_init = pyaudio.PyAudio()
        self.stream = None
        self.current_audio = None  #放置解码后的AudioSegment对象
        self.is_playing = False #正在播放标志
        self.is_pause = False #停止播放标志
        self.play_thread = None #播放线程引用
        self._seek_request = None
        self.frame_size=4
        self._seek_lock = threading.Lock()
        self._long = 0 #读取文件后获得总字节数
        self._now_position = 0 #定期刷新播放字节
        self.is_load = False


    def load_file(self,filepath):
        if self.is_load:
            self.current_audio = None
            self.stop()
        for i in range(10) : print(filepath)
        self.current_audio = AudioSegment.from_file(filepath)
        self._long = len(self.current_audio.raw_data)  #返回字节总数
        for i in range(10): print(self._long)  #测试 能否正常切歌
        self.is_load = True
    

    def get_total_duration_ms(self):  #获取总长度ms
        return len(self.current_audio) if self.current_audio else 0

    def get_ratio(self): #返回已播放与全长比例:
        if not self.current_audio or self._long == 0:
            return 0.0
        return self._now_position / self._long

    def get_now_position(self):  #返回目前播放ms
        if not self.current_audio or self._long == 0:
            return 0
        return int(self.get_ratio() * self.get_total_duration_ms())
        
        

    def _play_audio_data(self,audio_data,channels,sample_rate,sample_width):
        self.frame_size = channels * sample_width
        chunk_frames = 1024
        self.stream = self.audio_init.open(
            format=self.audio_init.get_format_from_width(sample_width),
            channels = channels,
            rate = sample_rate,
            output = True,
            frames_per_buffer = 1024)

        chunk_size = chunk_frames * self.frame_size
        offset = 0

        while self.is_playing and offset < len(audio_data):
            with self._seek_lock:
                if self._seek_request != None:
                    offset = self._seek_request
                    self._now_position = offset
                    self._seek_request = None
            if self.is_pause:
                time.sleep(0.1)
                continue

            end = min(offset+chunk_size,len(audio_data))
            self.stream.write(audio_data[offset:end])
            offset = end
        
            self._now_position = offset  #运行时刷新已读取字节
        
        self.is_playing = False
        self._now_position = 0
    
    def play(self):
        if self.is_playing:
            return


        raw_data = self.current_audio.raw_data
        self._now_position = 0
        
        sample_rate = int(self.current_audio.frame_rate)
        channels = int(self.current_audio.channels)
        sample_width = self.current_audio.sample_width

        self.is_playing=True
        self.is_pause=False

        self.play_thread = threading.Thread(
            target=self._play_audio_data,
            args = (raw_data,channels,sample_rate,sample_width),
            daemon = False
        )

        self.play_thread.start()

    def seek(self, ms):
        if not self.current_audio:
            return

        total_ms = len(self.current_audio)
        total_bytes = len(self.current_audio.raw_data)

        if total_ms <= 0:
            return

        ratio = max(0.0, min(1.0, ms / total_ms))
        target_byte = int(ratio * total_bytes)

        target_byte = (target_byte // self.frame_size) * self.frame_size

        with self._seek_lock:
            self._seek_request = target_byte  # 设置跳转目标

        
    
    def pause(self):
        self.is_pause = not self.is_pause

    def stop(self):
        self.is_playing=False
        self.is_pause=False
        if self.play_thread:
            self.play_thread.join(timeout=0.5)

    def __del__(self):
        self.stop()
        if hasattr(self, 'audio_init'):
            self.audio_init.terminate()
