import time
from functools import lru_cache, wraps

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

        def clear_cache():
            local_cache._cache.clear()
            local_cache._timestamps.clear()

        def evict_cache_key(*args, **kwargs):
            key = args
            if key in local_cache._cache:
                del local_cache._cache[key]
                del local_cache._timestamps[key]


        wrapped.clear_cache = clear_cache
        wrapped.evict_cache_key = evict_cache_key
        return wrapped
    return decorator