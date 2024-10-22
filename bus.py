import queue

event_bus = queue.Queue(10)

def push_text_to_client(txt):
    event_bus.put_nowait(txt)
