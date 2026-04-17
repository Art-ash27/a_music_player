from typing import List,Optional

class PlayListItem:
    def __init__(self,file_path:str,title:str):
        self.file_path = file_path
        self.title = title

class PlayList:
    def __init__(self):
        self.items = []
        self.load_index = -1

    def add_item(self,file_path,title):
        self.items.append(PlayListItem(file_path,title))
        if self.load_index == -1:
            self.current_index = 0

    def current_item(self):
        if not self.load_index >= 0 and self.current_index < len(self.items):
            return self.items[self.current_index]
        return None

    def next(self):
        if not self.items:
            return -1
        return (self.current_index + 1) % len(self.items)

    def prev(self):
        if not self.items:
            return -1
        return (self.current_index - 1) % len(self.items)
    
    def set_current(self,index):
        if 0 <= index < len(self.items):
            self.current_index = index
            return True
        return False
   
    def clear(self):
        self.items.clear()
        self.current_index = -1