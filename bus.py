from queue import Queue, Empty
import threading
from loguru import logger
import time

clients = []

def get_clients():
    return clients

def clean_client_task():
    def cleanup():
        while True:
            time.sleep(10)  # Run cleanup every 10 seconds
            for client_queue, stop_event in clients[:]:
                client_queue.put("Heartbeat to clean stale clients.")
                if stop_event.is_set() and (client_queue, stop_event) in clients:
                    clients.remove((client_queue, stop_event))

    cleanup_thread = threading.Thread(target=cleanup, daemon=True)
    cleanup_thread.start()

def push_text_to_client(txt):
    logger.debug(f"{txt}")
    broadcast_message(txt)

def broadcast_message(message):
    for client_queue, stop_event in clients:
        client_queue.put(message)

def client_add(client_queue, stop_event):
    clients.append((client_queue, stop_event))

def client_remove(client_queue: Queue, stop_event: threading.Event):
    if (client_queue, stop_event) in clients:  # Replace `some_list` with the actual list you are using
        clients.remove((client_queue, stop_event))
    stop_event.set()

def event_stream(client_queue: Queue, stop_event: threading.Event):
    try:
        while not stop_event.is_set():
            try:
                message = client_queue.get(timeout=1)
                yield f'data: {message}\n\n'
            except Empty:
                continue
    except GeneratorExit:
        logger.debug(f"Client {client_queue} disconnected, stopping the generator.")
    finally:
        client_remove(client_queue, stop_event)




