from loguru import logger

clients = []

def push_text_to_client(txt):
    logger.debug(f"{txt}")
    broadcast_message(txt)

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




