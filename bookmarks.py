import json
import os

from cache import cache
from globals import get_static_directory


@cache(maxsize=128, ttl=3600)
def list_bookmarks():
    bookmarks = []
    bookmarks_file = os.path.join(get_static_directory(), 'bookmarks.json')
    if os.path.exists(bookmarks_file):
        with open(bookmarks_file, 'r', encoding='utf-8') as f:
            bookmarks = json.load(f)
    return sorted(bookmarks, key=lambda x: x['title'].lower())


def write_bookmarks(bookmarks):
    bookmarks_file = os.path.join(get_static_directory(), 'bookmarks.json')
    with open(bookmarks_file, 'w', encoding='utf-8') as f:
        json.dump(bookmarks, f, indent=2, ensure_ascii=False)
    list_bookmarks.cache__clear()


def save_bookmark(title, url):#
    if not title or not url:
        return ServerResponse(False, "Title or URL missing")

    bookmarks = list_bookmarks()
    bookmark = next((b for b in bookmarks if b['url'] == url), None)

    if bookmark:
        bookmark['title'] = title
    else:
        bookmarks.append({"title": title, "url": url})

    write_bookmarks(bookmarks)
    return ServerResponse(True, "Bookmark added")


def delete_bookmark(url):
    if not url:
        return ServerResponse(False, "URL missing")

    bookmarks_before = list_bookmarks()
    bookmarks = [b for b in bookmarks_before if b['url'] != url]
    if len(bookmarks) == len(bookmarks_before):
        return ServerResponse(False, "Bookmark not found")
    else:
        write_bookmarks(bookmarks)

    return ServerResponse(True, "Bookmark deleted")
