import time
from functools import lru_cache, wraps

cache_registry = []

def cache(maxsize=128, ttl=None):
    def decorator(func):
        local_cache = lru_cache(maxsize=maxsize)(func)
        local_cache._cache = {}
        local_cache._timestamps = {}

        @wraps(func)
        def wrapped(*args, **kwargs):
            current_time = time.time()
            if args in local_cache._cache:
                if ttl is None or current_time - local_cache._timestamps[args] < ttl:
                    return local_cache._cache[args]
                else:
                    # Remove expired cache entry
                    del local_cache._cache[args]
                    del local_cache._timestamps[args]
            result = func(*args, **kwargs)
            if result:
                local_cache._cache[args] = result
                local_cache._timestamps[args] = current_time
            return result

        def cache_clear():
            local_cache._cache.clear()
            local_cache._timestamps.clear()

        def cache_evict(*args, **kwargs):
            key = args
            if key in local_cache._cache:
                del local_cache._cache[key]
                del local_cache._timestamps[key]


        def cache_stats():
            return {
                'size': len(local_cache._cache),
                'maxsize': maxsize,
                'ttl': ttl,
                'keys': list(local_cache._cache.keys())
            }

        wrapped.cache__clear = cache_clear
        wrapped.cache__evict = cache_evict
        wrapped.cache__stats = cache_stats

        cache_registry.append(wrapped)
        return wrapped
    return decorator

def get_all_cache_stats():
    stats = {func.__name__: func.cache__stats() for func in cache_registry}
    return stats


def clear_caches():
    cleared = {}
    for func in cache_registry:
        func.cache__clear()
        cleared[func.__name__] = 'cleared'
    return cleared

