import logging

import asyncpg

import settings

logger = logging.getLogger('pinger')


class AsyncDBConnector:
    ''' Manages db connections and exectutes sql queries.

        Usage example:
            connector = AsyncDBConnector()
            request_map = {
                'host': '1.1.1.1',
                'ping_timestamp': 'NOW()',
                'result': 'True',
            }
            asyncio.run(connector.insert('pinger_data', request_map))
    '''
    def __init__(self, host=settings.PG_HOST, db=settings.PG_DB,
                 user=settings.PG_USER, password=settings.PG_PASSWORD):
        self.host = host
        self.db = db
        self.user = user
        self.password = password

    def _pg_manager(function):
        ''' The decorator connects to the database and closes the connection
        when 'function' has finished.
        '''
        async def body(self, *args, **kwargs):
            self.connection = await asyncpg.connect(
                user=self.user, password=self.password,
                database=self.db, host=self.host,
            )

            result = await function(self, *args, **kwargs)

            await self.connection.close()
            return result

        return body

    @_pg_manager
    async def execute_sql(self, sql: str):
        ''' Executes given raw sql string.
        Returns a list of asyncpg.Record objects.
        '''
        return await self.connection.fetch(sql)

    @_pg_manager
    async def insert(self, table, data):
        ''' Inserts data to the given table. Data can be a dictionary
        with {column: value} structure or a list/tuple with dictionaries
        '''
        if isinstance(data, dict):
            query = "INSERT INTO {} ({}) VALUES ({})".format(
                table,
                ', '.join(data.keys()),
                ', '.join(data.values()),
            )
        # if input is a list or a tuple we should insert multiple rows
        # the formatting below is kinda ugly but the idea is to get
        # a request looking as follows:
        # INSERT INTO films (code, title, did, date_prod, kind) VALUES
        #     ('B6717', 'Tampopo', 110, '1985-02-10', 'Comedy'),
        #     ('HG120', 'The Dinner Game', 140, DEFAULT, 'Comedy')
        elif isinstance(data, list) or isinstance(data, tuple):
            query = "INSERT INTO {} ({}) VALUES {}".format(
                table,
                ', '.join(data[0].keys()),
                ', '.join([
                    '({})'.format(
                        ', '.join(batch.values())
                    ) for batch in data
                ])
            )

        return await self.connection.execute(query)
