import json
from typing import Any, Optional, Union

import redis.asyncio as redis

from app.core.config import get_settings
from app.core.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)


class RedisClient:
    def __init__(self):
        self._client: Optional[redis.Redis] = None
        self._pool: Optional[redis.ConnectionPool] = None

    async def connect(self):
        try:
            self._pool = redis.ConnectionPool.from_url(
                settings.redis_url,
                max_connections=settings.redis_pool_size,
                decode_responses=True
            )
            self._client = redis.Redis(connection_pool=self._pool)
            await self._client.ping()
            logger.info("redis_connected")
        except Exception as e:
            logger.error("redis_connection_failed", error=str(e))
            raise

    async def disconnect(self):
        if self._pool:
            await self._pool.disconnect()
            logger.info("redis_disconnected")

    @property
    def client(self) -> redis.Redis:
        if not self._client:
            raise RuntimeError("Redis client not initialized. Call connect() first.")
        return self._client

    async def get(self, key: str) -> Optional[str]:
        return await self.client.get(key)

    async def set(
        self,
        key: str,
        value: Union[str, int, float],
        expire: Optional[int] = None
    ) -> bool:
        return await self.client.set(key, value, ex=expire)

    async def delete(self, key: str) -> int:
        return await self.client.delete(key)

    async def exists(self, key: str) -> bool:
        return await self.client.exists(key) > 0

    async def expire(self, key: str, seconds: int) -> bool:
        return await self.client.expire(key, seconds)

    async def ttl(self, key: str) -> int:
        return await self.client.ttl(key)

    async def set_json(self, key: str, value: Any, expire: Optional[int] = None) -> bool:
        return await self.set(key, json.dumps(value), expire)

    async def get_json(self, key: str) -> Optional[Any]:
        data = await self.get(key)
        if data:
            return json.loads(data)
        return None

    async def add_to_set(self, key: str, *values: str) -> int:
        return await self.client.sadd(key, *values)

    async def remove_from_set(self, key: str, *values: str) -> int:
        return await self.client.srem(key, *values)

    async def is_member(self, key: str, value: str) -> bool:
        return await self.client.sismember(key, value)

    async def push_list(self, key: str, *values: str) -> int:
        return await self.client.lpush(key, *values)

    async def pop_list(self, key: str, blocking: bool = False, timeout: int = 0) -> Optional[str]:
        if blocking:
            result = await self.client.brpop(key, timeout=timeout)
            return result[1] if result else None
        return await self.client.rpop(key)

    async def publish(self, channel: str, message: str) -> int:
        return await self.client.publish(channel, message)


redis_client = RedisClient()


class OTPStorage:
    KEY_PREFIX = "otp:"

    @staticmethod
    def _key(phone: str) -> str:
        return f"{OTPStorage.KEY_PREFIX}{phone}"

    async def store(self, phone: str, otp: str, expiry_minutes: int = None) -> bool:
        expiry = (expiry_minutes or settings.otp_expiry_minutes) * 60
        return await redis_client.set(
            self._key(phone),
            otp,
            expire=expiry
        )

    async def verify(self, phone: str, otp: str) -> bool:
        key = self._key(phone)
        stored = await redis_client.get(key)
        if stored and stored == otp:
            await redis_client.delete(key)
            return True
        return False

    async def get_remaining_attempts(self, phone: str) -> int:
        key = f"{self._key(phone)}:attempts"
        attempts = await redis_client.get(key)
        return int(attempts) if attempts else 3

    async def increment_attempts(self, phone: str) -> int:
        key = f"{self._key(phone)}:attempts"
        new_val = await redis_client.client.incr(key)
        if new_val == 1:
            await redis_client.expire(key, 3600)
        return new_val


class JWTBlacklist:
    KEY_PREFIX = "jwt_blacklist:"

    def _key(self, token_jti: str) -> str:
        return f"{self.KEY_PREFIX}{token_jti}"

    async def blacklist(self, token_jti: str, expire_seconds: int) -> bool:
        return await redis_client.set(
            self._key(token_jti),
            "1",
            expire=expire_seconds
        )

    async def is_blacklisted(self, token_jti: str) -> bool:
        return await redis_client.exists(self._key(token_jti))


class SOSStateCache:
    KEY_PREFIX = "sos:"

    def _key(self, alert_id: str) -> str:
        return f"{self.KEY_PREFIX}{alert_id}"

    async def cache_alert(self, alert_id: str, data: dict, expire_seconds: int = 3600) -> bool:
        return await redis_client.set_json(
            self._key(alert_id),
            data,
            expire=expire_seconds
        )

    async def get_alert(self, alert_id: str) -> Optional[dict]:
        return await redis_client.get_json(self._key(alert_id))

    async def update_location(self, alert_id: str, lat: float, lng: float, timestamp: str) -> bool:
        key = f"{self._key(alert_id)}:locations"
        location_data = json.dumps({"lat": lat, "lng": lng, "ts": timestamp})
        return await redis_client.push_list(key, location_data)

    async def get_recent_locations(self, alert_id: str, count: int = 10) -> list:
        key = f"{self._key(alert_id)}:locations"
        locations = await redis_client.client.lrange(key, 0, count - 1)
        return [json.loads(loc) for loc in locations]


class SessionCache:
    KEY_PREFIX = "session:"

    def _key(self, session_id: str) -> str:
        return f"{self.KEY_PREFIX}{session_id}"

    async def store(self, session_id: str, data: dict, expire_hours: int = 24) -> bool:
        return await redis_client.set_json(
            self._key(session_id),
            data,
            expire=expire_hours * 3600
        )

    async def get(self, session_id: str) -> Optional[dict]:
        return await redis_client.get_json(self._key(session_id))

    async def delete(self, session_id: str) -> int:
        return await redis_client.delete(self._key(session_id))


# Initialize storage classes
otp_storage = OTPStorage()
jwt_blacklist = JWTBlacklist()
sos_cache = SOSStateCache()
session_cache = SessionCache()
