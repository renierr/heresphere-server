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
    logger.debug(f"{txt}")
    broadcast_message(txt)


clients = []

def broadcast_message(message):
    for client_queue, stop_event in clients:
        client_queue.put(message)

def client_add(client_queue, stop_event):
    clients.append((client_queue, stop_event))

def client_remove(client_queue, stop_event):
    clients.remove((client_queue, stop_event))

def event_stream(client_queue, stop_event):
    while not stop_event.is_set():
        try:
            message = client_queue.get(timeout=1)
            yield f'data: {message}\n\n'
        except:
            continue




