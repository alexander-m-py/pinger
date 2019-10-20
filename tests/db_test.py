import asyncio
import unittest

import settings
from connectors.db import AsyncDBConnector


class DBTester(unittest.TestCase):
    ''' Tests whether db is ready and works correctly or not '''
    def __init__(self, *args, **kwargs):
        # simple __init__ overriding raises an exception
        super(DBTester, self).__init__(*args, **kwargs)
        self.connector = AsyncDBConnector()

    def test_io(self):
        async def async_tester():
            row = {
                'host': "'1.1.1.1'",
                'ping_timestamp': 'NOW()',
                'result': 'True'
            }

            await self.connector.insert(settings.PINGER_TABLE, row)
            return await self.connector.execute_sql(
                "SELECT * FROM pinger_data WHERE host='1.1.1.1' "
                "AND ping_timestamp>=NOW() - INTERVAL '1 seconds'"
            )

        # async_tester returns a list of asyncpg.Record objects
        records = asyncio.run(async_tester())

        self.assertEqual(len(records), 1)
        self.assertTrue(records[0]['result'])
        self.assertEqual(records[0]['host'], '1.1.1.1')
