from loguru import logger
import queue

class AutoRemovingQueue(queue.Queue):
    def __init__(self, maxsize=100):
        super().__init__(maxsize)

    def put(self, item, block=True, timeout=None):
        while self.full():
            try:
                self.get_nowait()
            except queue.Empty:
                break
        super().put(item, block, timeout)

event_bus = AutoRemovingQueue(maxsize=100)

def push_text_to_client(txt):
    event_bus.put(txt)
    logger.debug(f"Added message to event bus: {txt}")
