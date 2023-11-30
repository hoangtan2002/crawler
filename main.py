from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
import queue
import threading
import logging
import flet as ft

url = ""

logging.basicConfig(
    format='%(asctime)s %(levelname)s:%(message)s',
    level=logging.INFO)

class urlStruct:
    def __init__(self,url:str,level:int):
        self.url = url;
        self.level = level
        
class fileStruct:
    def __init__(self,fileName:str,url:str):
        self.fileName = fileName
        self.url = url

class Crawler:
    def __init__(self) -> None:
        self.urlQueue = queue.Queue()
        self.fileType = ""
        self.visitedUrl = []
        self.fileCrawled = []
        self.maxDepth = 0
        pass
    
    def addSite(self, url:urlStruct) -> None:
        self.urlQueue.push(urlStruct(url=url, level = 0))
        self.queueLock = threading.Lock()
        pass
    
    def setFileType(self, fileType:str):
        self.fileType = fileType
        
    def setMaxDepth(self, depth:int):
        self.maxDepth = depth
        
    def addFile(self, file:fileStruct):
        self.fileCrawled.append(file)
    
    def worker(self) -> None:
        while True:
            while self.queueLock.locked():
                pass
            self.queueLock.acquire()
            if self.urlQueue.empty():
                self.queueLock.release()
                break
            else:
                urlStruct = self.urlQueue.get()
                #TODO: Get web page, find all elements with the filetype. If find a link, add back with increase level
            self.queueLock.release()
                        
class UserInterface:
    def __init__(self):
        self.urlField = ft.TextField(label="Enter URL here", autofocus=True,width=300)
        self.fileTypeDropdown = ft.Dropdown(label = "Filetype",
                                            width=200,
                                            options=[
                                                ft.dropdown.Option("mp3"),
                                                ft.dropdown.Option("pdf")
                                            ])
        self.parallelThread = ft.Dropdown(label = "Threads",
                                          width=150,
                                          options = [ft.dropdown.Option(1),
                                                     ft.dropdown.Option(5),
                                                     ft.dropdown.Option(10)])
        self.maxDepth = ft.Dropdown(label = "Max depth", 
                                    width=150,
                                    options = [ft.dropdown.Option(1),
                                               ft.dropdown.Option(2),
                                               ft.dropdown.Option(3),
                                               ft.dropdown.Option(4),
                                               ft.dropdown.Option(5)])
        self.startBtn = ft.ElevatedButton(text="Start",
                                          on_click=self.startCrawl,
                                          height=50)
        
        self.crawler = Crawler()
        pass
    
    def startCrawl(self):
        print(f"Start Crawler with URL:{self.urlField.value}, filetype:{self.fileTypeDropdown.value}, with {self.parallelThread.value} Threads and max depth of {self.maxDepth.value}" )
        pass
    
    def main(self,page:ft.Page):
        page.add(ft.Row([self.urlField,
                         self.fileTypeDropdown,
                         self.parallelThread,
                         self.maxDepth,
                         self.startBtn]))
        
ui=UserInterface()
ft.app(target=ui.main)
    