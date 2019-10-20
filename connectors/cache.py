import asyncio
import logging

import aioredis

import settings

logger = logging.getLogger('pinger')


class AsyncRedisConnector:
    ''' Manages redis connections and executes queries.

        Usage example:
            connector = AsyncRedisConnector()
            batch = {
                '1.1.1.1': True,
                '2.2.2.2': False,
            }
            results = await connector.write_batch(batch)
    '''
    def __init__(self, host=settings.REDIS_HOST, port=settings.REDIS_PORT):
        self.host = host
        self.port = port

    def _redis_manager(function):
        ''' The decorator connects to the cache and closes the connection
        pool when 'function' has finished.
        '''
        async def body(self, *args, **kwargs):
            # Redis client bound to pool of connections
            # and has auto-reconnecting feature
            self.pool = await aioredis.create_pool((self.host, self.port))

            result = await function(self, *args, **kwargs)

            self.pool.close()
            await self.pool.wait_closed()
            return result

        return body

    @_redis_manager
    async def write_batch(self, batch: dict):
        ''' Writes key:value pairs from batch to cache.
        Exceptions are not propagated but stored in results lists.
        Returns a list of results.
        '''
        # pool is created by _redis_manager
        async with self.pool.get() as connection:
            results = await asyncio.gather(
                *[
                    connection.execute('set', ip, str(result))
                    for ip, result in batch.items()
                ],
                return_exceptions=True,
            )

        # since asyncio.gather's return_exceptions is True, so we can safely
        # iterate the results
        for result in results:
            if isinstance(result, Exception):
                logger.exception(
                    f'Unexpected exception while writing a batch '
                    f'of results to the cache: {result}'
                )
            elif result != b'OK':
                logger.error(
                    f'Unexpected response from redis while writing a batch '
                    f'of results to the cache: {result}'
                )

        return results

    @_redis_manager
    async def get(self, key):
        ''' Reads a value for the given key '''
        async with self.pool.get() as connection:
            return await connection.execute('get', key)
