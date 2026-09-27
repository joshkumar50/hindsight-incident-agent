"""
Redis Streams EventBus Client
Provides an asynchronous, robust connection to Redis for publishing and consuming SRE events.
"""

import asyncio
import json
import logging
import os
from typing import Any, Callable, Dict, Optional

try:
    import redis.asyncio as redis
    from redis.asyncio.client import Redis
    from redis.exceptions import ResponseError, TimeoutError, ConnectionError
except ImportError:
    redis = None
    Redis = Any
    ResponseError = Exception
    TimeoutError = Exception
    ConnectionError = Exception

logger = logging.getLogger("eventbus")


class EventBusClient:
    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
        self.client: Optional[Redis] = None

    async def connect(self):
        """Establish async connection to Redis."""
        if redis is None:
            raise ImportError("redis module is not installed.")
        # socket_timeout=None to avoid blocking read timeouts killing the connection
        self.client = redis.from_url(
            self.redis_url,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_keepalive=True,
            health_check_interval=30,
        )
        await self.client.ping()
        logger.info(f"Connected to EventBus at {self.redis_url}")

    async def _ensure_connected(self):
        """Reconnect if connection is lost, looping until successful."""
        while True:
            if self.client is None:
                try:
                    await self.connect()
                    return
                except Exception as e:
                    logger.warning(f"Failed to connect to Redis, retrying in 2s: {e}")
                    await asyncio.sleep(2)
                    continue
            
            try:
                await self.client.ping()
                return
            except Exception:
                logger.warning("Redis connection lost, reconnecting...")
                try:
                    await self.client.aclose()
                except Exception:
                    pass
                self.client = None
                await asyncio.sleep(2)

    async def disconnect(self):
        """Close connection."""
        if self.client:
            await self.client.aclose()

    async def publish(self, stream: str, event_type: str, payload: Dict[str, Any]):
        """Publish an event to a specific Redis Stream."""
        await self._ensure_connected()
        event_data = {"event_type": event_type, "payload": json.dumps(payload)}
        message_id = await self.client.xadd(stream, event_data, id="*")
        logger.debug(f"Published event {event_type} to {stream} with ID {message_id}")
        return message_id

    async def consume(self, stream: str, group: str, consumer: str, callback: Callable):
        """
        Consume events from a Redis Stream using Consumer Groups.
        Ensures at-least-once delivery with automatic reconnection on failures.
        """
        await self._ensure_connected()

        # Use id="$" — only consume NEW messages published after this consumer starts.
        # id="0" would replay ALL historical messages from the stream on every pod restart,
        # causing stale ChaosStarted events to re-trigger the pipeline.
        try:
            await self.client.xgroup_create(stream, group, id="$", mkstream=True)
            logger.info(f"Created consumer group {group} for stream {stream}")
        except ResponseError as e:
            if "BUSYGROUP" not in str(e):
                logger.error(f"Error creating consumer group: {e}")
                raise
        except Exception as e:
            logger.error(f"Unexpected error creating group: {e}")

        logger.info(f"Started consumer {consumer} in group {group} for stream {stream}")

        while True:
            try:
                await self._ensure_connected()

                # Block for 2 seconds max — short enough to avoid stale connection timeouts
                # but long enough to be efficient. On timeout, just loop again.
                messages = await self.client.xreadgroup(
                    group, consumer, {stream: ">"}, count=10, block=2000
                )

                if not messages:
                    # No new messages — normal, just loop
                    continue

                for _, stream_messages in messages:
                    for message_id, message_data in stream_messages:
                        try:
                            event_type = message_data.get("event_type", "unknown")
                            payload_str = message_data.get("payload", "{}")
                            payload = json.loads(payload_str)

                            logger.debug(f"Processing event {event_type} [{message_id}] from {stream}")

                            if asyncio.iscoroutinefunction(callback):
                                await callback(event_type, payload, message_id)
                            else:
                                callback(event_type, payload, message_id)

                            # ACK only after successful processing
                            await self.client.xack(stream, group, message_id)
                            logger.debug(f"ACKed message {message_id}")

                        except Exception as inner_e:
                            logger.error(f"Error processing message {message_id}: {inner_e}")
                            # Do not ACK — let it be reprocessed

            except asyncio.CancelledError:
                logger.info(f"Consumer {consumer} cancelled, shutting down.")
                break
            except (TimeoutError, ConnectionError) as e:
                # Redis read timeout is NORMAL when no messages arrive — just reconnect and continue
                logger.warning(f"Redis connection issue on {stream}, reconnecting: {type(e).__name__}")
                try:
                    await self.client.aclose()
                except Exception:
                    pass
                self.client = None
                await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Consumer loop error on {stream}: {e}")
                await asyncio.sleep(2)
