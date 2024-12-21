from globals import load_url_map, save_url_map

def on_starting(server):
    load_url_map()

def on_exit(server):
    save_url_map()
