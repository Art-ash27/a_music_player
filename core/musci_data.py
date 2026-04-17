import re
from pathlib import Path
import json
import os
from .music_info import parse_song_info
class Music_DataBase:
    def __init__(self,db_path):
        self.db_path = Path(db_path)
        self.songs = []
        self.load()
    
    def load(self):
        if self.db_path.exists():
            try:
                with open(self.db_path,'r',encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data,dict):
                        self.songs = [data]
                    else:
                        self.songs = data
            except Exception as e:
                print(f"[WARN] 加载 {self.db_path} 失败")
                self.songs = []
        else:
            self.sons = []