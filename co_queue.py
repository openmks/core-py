#!/usr/bin/python
import threading
import queue
import _thread
import traceback

from core import co_logger

class Manager():
    def __init__(self, handler):
        self.ClassName		    = "Queue"
        self.WorkerStart        = False
        self.Locker			    = threading.Lock()
        self.LocalQueue		    = queue.Queue()
        self.HandlerCallback    = handler

    def Start(self):
        self.WorkerStart = True
        _thread.start_new_thread(self.Worker, ())
    
    def Stop(self):
        self.WorkerStart = False
        self.QueueItem(None)
    
    def QueueItem(self, item):
        if self.WorkerStart is True:
            self.Locker.acquire()
            try:
                self.LocalQueue.put(item)
            except Exception as e:
                co_logger.LOGGER.Log("Queue [QueueItem]\n{}\n(Exception): {} \n=======\nTrace: {}=======".format(item, str(e), traceback.format_exc()), 1)
            self.Locker.release()

    def Worker(self):
        while self.WorkerStart is True:
            try:
                item = self.LocalQueue.get(block=True,timeout=None)
                if self.HandlerCallback is not None and item is not None:
                    self.HandlerCallback(item)
            except Exception as e:
                co_logger.LOGGER.Log("Queue [Worker]\n{}\n(Exception): {} \n=======\nTrace: {}=======".format(item, str(e), traceback.format_exc()), 1)