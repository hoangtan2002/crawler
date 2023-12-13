from urllib.parse import urljoin, urlparse
from pathlib import Path
from collections import OrderedDict
from bs4 import BeautifulSoup
import requests
import queue
import threading
import logging
import tld
import flet as ft

url = ""

logging.basicConfig(
    format='%(asctime)s %(levelname)s:%(message)s',
    level=logging.INFO)

def is_html_content(response):
    content_type = response.headers.get('Content-Type', '').lower()
    return 'text/html' in content_type

class IdGenerator:
    def __init__(self, maxId=10):
        self.maxId = 10
        self.Id = 0
        
    def resetIdGenerator(self):
        self.Id = 0
        
    def yieldId(self):
        while True:
            yield self.Id
            self.Id = self.Id+1
            if(self.Id == self.maxId):
                self.Id = 0;

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
        self.queueLock = threading.Lock()
        self.fileType = ""
        self.visitedUrl = []
        self.fileCrawled = []
        self.maxDepth = 0
        pass
    
    def addSite(self, url:urlStruct, level) -> None:
        self.urlQueue.put(urlStruct(url=url, level=level))
        pass
    
    def setFileType(self, fileType:str):
        self.fileType = fileType
        
    def setMaxDepth(self, depth:int):
        self.maxDepth = depth
        
    def addFile(self, file:fileStruct):
        self.fileCrawled.append(file)
        
    def writeLogMsg(self, msg:str):
        print(msg)

    def worker(self, fileType:str, maxDepth:int, firstLevelUrl:str ,threadId: int) -> None:
        self.writeLogMsg(f"Worker {threadId} started")
        while True:
            while self.queueLock.locked():
                pass
            self.queueLock.acquire()
            if self.urlQueue.empty():
                self.queueLock.release()
                self.writeLogMsg(f"Worker {threadId}: has completed")
                break
            else:
                urlStruct = self.urlQueue.get()
                #TODO: Get web page, find all elements with the filetype. If find a link, add back with increase level

                if urlStruct.url in self.visitedUrl:
                    self.writeLogMsg(f"Worker {threadId}: Link visited")
                    self.queueLock.release()
                    continue
                
                if fileType in urlStruct.url:
                    self.queueLock.release()
                    self.writeLogMsg(f"Worker {threadId}: File URL")
                    continue
                
                if urlStruct.level > maxDepth:
                    self.queueLock.release()
                    self.writeLogMsg(f"Worker {threadId}: Hit max depth")
                    continue

                self.visitedUrl.append(urlStruct.url)
                self.writeLogMsg(f"Worker {threadId}: Visit URL {urlStruct.url}")
                try:
                    response = requests.get(urlStruct.url)
                    if response.status_code == 200 and is_html_content(response):
                        soup = BeautifulSoup(response.text, 'html.parser')
                        # Extract links
                        numOfLinks = 0
                        numOfFiles = 0
                        for a in soup.find_all('a', href=True):
                            if a['href'].endswith(fileType):
                                numOfFiles += 1
                                self.addFile(fileStruct(Path(urljoin(urlStruct.url, a['href'])).name,
                                                        urljoin(urlStruct.url, a['href'])))
                                pass
                            elif firstLevelUrl in a['href']:
                                numOfLinks+=1
                                if a['href'] not in self.visitedUrl:
                                    self.addSite(urljoin(urlStruct.url, a['href']), urlStruct.level+1)
                            else:
                                self.writeLogMsg(f"Worker {threadId}: URL outside of first level domain, ignore!")
                                
                        self.queueLock.release()
                        
                        if fileType in ['.png', '.jpg']:
                            for element in soup.find_all('img',src=True):
                                src = element['src']
                                if src.endswith(fileType):
                                    numOfFiles+=1
                                    self.addFile(fileStruct(Path(src).name,src))
                                    
                        elif fileType == '.mp3':
                            for element in soup.find_all('audio',src=True):
                                src = element['src']
                                if src.endswith(fileType):
                                    numOfFiles+=1
                                    self.addFile(fileStruct(Path(src).name,src))
                                    
                        elif fileType == '.mp4':
                            for element in soup.find_all('video',src=True):
                                src = element['src']
                                if src.endswith(fileType):
                                    numOfFiles+=1
                                    self.addFile(fileStruct(Path(src).name,src))
                        
                        self.writeLogMsg(f"Worker {threadId}: Depth {urlStruct.level}: {urlStruct.url} - Found {numOfLinks} links and {numOfFiles} files")

                        # Enqueue links for further processing
                        
                    else:
                        self.queueLock.release()
                        self.writeLogMsg(f"Worker {threadId}: Error:Might not be an actual page or some exit code")

                except Exception as e:
                    self.queueLock.release()
                    self.writeLogMsg(f"Worker {threadId}: Error processing {urlStruct.url}: {e}")
                    
    def download(self,url,dest):
        print(f"Download file {url}")
        response = requests.get(url)
        if response.status_code == 200:
            # Extracting the file name from the URL
            file_name = url.split("/")[-1]
            
            # Creating the destination path
            destination_path = Path(dest) / file_name
            
            # Writing the content to the file
            with open(destination_path, 'wb') as file:
                file.write(response.content)
                
            print(f"File downloaded successfully: {destination_path}")
        else:
            print(f"Failed to download file. Status code: {response.status_code}")
            pass
                
    def getAllFile(self,dest):
        #TODO: Download all files to Downloads folder 
        self.fileCrawled = list(OrderedDict.fromkeys(self.fileCrawled))
        for file in self.fileCrawled:
            self.download(file.url,dest)
        pass
                        
class UserInterface:
    def __init__(self):
        self.urlField = ft.TextField(label="Enter URL here", autofocus=True,width=520)
        self.threadIdPool = IdGenerator()
        self.fileTypeDropdown = ft.Dropdown(label = "Filetype",
                                            width=200,
                                            options=[
                                                ft.dropdown.Option(".mp3"),
                                                ft.dropdown.Option(".mp4"),
                                                ft.dropdown.Option(".pdf"),
                                                ft.dropdown.Option(".jpg"),
                                                ft.dropdown.Option(".png"),
                                            ])
        self.parallelThread = ft.Dropdown(label = "Num of workers",
                                          width=200,
                                          options = [ft.dropdown.Option(1),
                                                     ft.dropdown.Option(5),
                                                     ft.dropdown.Option(10)])
        self.maxDepth = ft.Dropdown(label = "Depth", 
                                    width=100,
                                    options = [ft.dropdown.Option(0),
                                               ft.dropdown.Option(1),
                                               ft.dropdown.Option(2),
                                               ft.dropdown.Option(3),
                                               ft.dropdown.Option(4),
                                               ft.dropdown.Option(5)])
        self.startBtn = ft.ElevatedButton(text="Start",
                                          on_click=self.startCrawl,
                                          height=50)
        self.logContent = ft.ListView(auto_scroll=True)
        self.status = ft.Text("Status: Ready",
                              text_align=ft.TextAlign.LEFT,
                              size=24)      
        self.downloadBtn = ft.ElevatedButton(icon='download',
                                             text="Download all",
                                             height=50,
                                             disabled=True,
                                             on_click=self.startDownload)
        self.crawler = Crawler()
        self.userRequest = 0;
        self.workerThread = []
        pass
    
    def startCrawl(self,e):
        #TODO:Start crawling thread
        self.crawler.addSite(self.urlField.value,0)
        self.status.value = "Status: Crawling"
        self.startBtn.disabled = True
        self.page.update()
        threadId = range(int(self.parallelThread.value))
        for i in range(int(self.parallelThread.value)):
            self.workerThread.append(threading.Thread(target=lambda:self.crawler.worker(
                self.fileTypeDropdown.value,
                int(self.maxDepth.value),
                tld.get_fld(self.urlField.value),
                threadId[i],
            )))
            self.workerThread[i].start()
        for i in range(int(self.parallelThread.value)):
            self.workerThread[i].join()
        print("All thread complete")
        self.startBtn.disabled = False 
        self.downloadBtn.disabled = False
        self.status.value = "Status: Done Crawling"
        self.page.update()
        pass
    
    def startDownload(self,e):
        pick_files_dialog = ft.FilePicker(on_result=self.downloadFiles)
        self.page.overlay.append(pick_files_dialog)
        self.page.update()
        pick_files_dialog.get_directory_path(dialog_title="Pick a location to save files")
        pass
    
    def downloadFiles(self,e:ft.FilePicker.result):
        self.status.value = "Status: Downloading files"
        self.page.update()
        self.crawler.getAllFile(e.path)
        self.status.value = "Status: Done downloading "
        self.page.update()
    
    def main(self,page:ft.Page):
        self.page = page
        self.page.window_min_height = 600
        self.page.window_min_width = 610
        self.Row1 = ft.Row([self.urlField])
        self.Row2 = ft.Row([self.fileTypeDropdown,
                            self.parallelThread,
                            self.maxDepth])
        self.Row3 = ft.Row([self.startBtn,
                            self.downloadBtn,
                            self.status])
        page.add(self.Row1,
                 self.Row2,
                 self.Row3)
        
ui=UserInterface()
app = ft.app(target=ui.main)
