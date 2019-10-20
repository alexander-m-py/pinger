import asyncio
import unittest

from connectors.cache import AsyncRedisConnector


class CacheTester(unittest.TestCase):
    ''' Tests whether cache is ready and works correctly or not '''
    def __init__(self, *args, **kwargs):
        # simple __init__ overriding leads to an exception
        super(CacheTester, self).__init__(*args, **kwargs)
        self.connector = AsyncRedisConnector()

    def test_io(self):
        async def get_test_batch():
            return (
                await self.connector.get('1.1.1.1'),
                await self.connector.get('2.2.2.2'),
            )

        async def write_test_batch():
            test_batch = {
                '1.1.1.1': True,
                '2.2.2.2': False,
            }
            return await self.connector.write_batch(test_batch)

        async def async_tester():
            write_results = await write_test_batch()
            first_value, second_value = await get_test_batch()
            return write_results, first_value, second_value

        write_results, first_value, second_value = asyncio.run(
            async_tester()
        )

        self.assertEqual(
            write_results, [b'OK', b'OK'], 'Redis test batch writing failed',
        )
        self.assertEqual(
            first_value, b'True', '1.1.1.1 value is not True',
        )
        self.assertEqual(
            second_value, b'False', '2.2.2.2 value is not False',
        )
