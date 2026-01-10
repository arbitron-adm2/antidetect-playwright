"""Redis client wrapper."""

import asyncio
from typing import Any

import redis.asyncio as redis


class RedisClient:
    """Async Redis client with connection pooling."""

    def __init__(
        self,
        host: str,
        port: int,
        password: str | None,
        db: int,
        pool_size: int,
        key_prefix: str,
        default_ttl: int,
        connection_timeout: int,
    ) -> None:
        self._host = host
        self._port = port
        self._password = password
        self._db = db
        self._pool_size = pool_size
        self._key_prefix = key_prefix
        self._default_ttl = default_ttl
        self._connection_timeout = connection_timeout

        self._pool: redis.ConnectionPool | None = None
        self._client: redis.Redis | None = None

    async def connect(self) -> None:
        """Initialize connection pool."""
        self._pool = redis.ConnectionPool(
            host=self._host,
            port=self._port,
            password=self._password,
            db=self._db,
            max_connections=self._pool_size,
            socket_connect_timeout=self._connection_timeout,
            socket_timeout=self._connection_timeout,
            decode_responses=True,
        )
        self._client = redis.Redis(connection_pool=self._pool)

        await self._client.ping()

    async def disconnect(self) -> None:
        """Close connection pool."""
        if self._client:
            await self._client.close()
        if self._pool:
            await self._pool.disconnect()

    def _make_key(self, key: str) -> str:
        """Create prefixed key."""
        return f"{self._key_prefix}:{key}"

    async def get(self, key: str) -> str | None:
        """Get value by key."""
        if not self._client:
            raise RuntimeError("Redis client not connected")
        return await self._client.get(self._make_key(key))

    async def set(
        self,
        key: str,
        value: str,
        ttl: int | None = None,
    ) -> None:
        """Set value with optional TTL."""
        if not self._client:
            raise RuntimeError("Redis client not connected")
        await self._client.set(
            self._make_key(key),
            value,
            ex=ttl or self._default_ttl,
        )

    async def delete(self, key: str) -> bool:
        """Delete key."""
        if not self._client:
            raise RuntimeError("Redis client not connected")
        result = await self._client.delete(self._make_key(key))
        return result > 0

    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        if not self._client:
            raise RuntimeError("Redis client not connected")
        result = await self._client.exists(self._make_key(key))
        return result > 0

    async def hset(self, key: str, mapping: dict[str, str]) -> None:
        """Set hash fields."""
        if not self._client:
            raise RuntimeError("Redis client not connected")
        await self._client.hset(self._make_key(key), mapping=mapping)

    async def hget(self, key: str, field: str) -> str | None:
        """Get hash field."""
        if not self._client:
            raise RuntimeError("Redis client not connected")
        return await self._client.hget(self._make_key(key), field)

    async def hgetall(self, key: str) -> dict[str, str]:
        """Get all hash fields."""
        if not self._client:
            raise RuntimeError("Redis client not connected")
        return await self._client.hgetall(self._make_key(key))

    async def lpush(self, key: str, *values: str) -> int:
        """Push values to list head."""
        if not self._client:
            raise RuntimeError("Redis client not connected")
        return await self._client.lpush(self._make_key(key), *values)

    async def rpush(self, key: str, *values: str) -> int:
        """Push values to list tail."""
        if not self._client:
            raise RuntimeError("Redis client not connected")
        return await self._client.rpush(self._make_key(key), *values)

    async def lpop(self, key: str) -> str | None:
        """Pop value from list head."""
        if not self._client:
            raise RuntimeError("Redis client not connected")
        return await self._client.lpop(self._make_key(key))

    async def llen(self, key: str) -> int:
        """Get list length."""
        if not self._client:
            raise RuntimeError("Redis client not connected")
        return await self._client.llen(self._make_key(key))

    async def lrange(self, key: str, start: int, end: int) -> list[str]:
        """Get list range."""
        if not self._client:
            raise RuntimeError("Redis client not connected")
        return await self._client.lrange(self._make_key(key), start, end)

    async def pipeline(self) -> redis.client.Pipeline:
        """Get pipeline for batch operations."""
        if not self._client:
            raise RuntimeError("Redis client not connected")
        return self._client.pipeline()

    @property
    def client(self) -> redis.Redis:
        """Get raw client for advanced operations."""
        if not self._client:
            raise RuntimeError("Redis client not connected")
        return self._client
