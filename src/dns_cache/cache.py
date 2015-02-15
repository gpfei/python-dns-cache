import asyncio
import asyncio_redis


class Singleton(type):
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class Cache(metaclass=Singleton):

    def __init__(self, name):
        self._cache = asyncio_redis.Connection.create(host='localhost', port=6379, db=0)

    def set(self, k, v, ttl):
        self._cache.set(k, v, ttl)

    def get(self, k):
        self._cache.get(k)
