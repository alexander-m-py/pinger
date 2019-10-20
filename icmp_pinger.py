import asyncio
import logging
import re
import time
from abc import ABCMeta, abstractmethod

import mtrpacket
import requests

import settings
from connectors.cache import AsyncRedisConnector
from connectors.db import AsyncDBConnector

logging.basicConfig(
    level=logging.DEBUG,
    format=settings.LOG_FORMATTER,
    datefmt=settings.LOG_DATE_TIME,
)
logger = logging.getLogger('pinger')


class Pinger(metaclass=ABCMeta):
    ''' The base class for all pingers. Contains mandatory "probe" method
    which sends requests and returns responses asynchronously
    and "run" method which invokes the probe for provided list of addresses.
    _log method can be used for simple and efficient logging.
    '''
    @abstractmethod
    async def probe(self, host, port):
        raise NotImplementedError()

    @abstractmethod
    async def run(self, hosts):
        raise NotImplementedError()

    def _log(self, message, log_type='debug'):
        ''' Logs the message and invoker's name '''
        logging_methods = {
            'debug': logging.debug,
            'warning': logging.warning,
            'exception': logging.exception,
            'error': logging.error,
        }

        invoker = logging_methods.get(log_type)

        if not invoker:
            raise KeyError(
                f'Incompatible log_type: {log_type}; '
                f'one can use: {logging_methods.keys()}'
            )

        invoker(f'{str(self)}: {message}')


class ICMPPinger(Pinger):
    def __str__(self):
        return 'ICMPPinger'

    def __init__(self, hosts=None):
        ''' We can initialize a list of hosts manually or let pinger
        fetch it from the darkest corners of the Internet.

        Attributes
        ----------
        hosts : a list of dictionaries
            The probe requires ports to be defined explicitly
            in the following format:
            [{host: 178.255.201.20, port: 444}, {...}, {...},]
        '''
        if hosts:
            self.hosts = hosts
            return

        hosts = self._fetch_random_hosts()
        self.hosts = self._create_host_port_list(hosts)

    def _fetch_random_hosts(self):
        ''' Returns raw list of hosts fetched from the Internet
        or from the local file
        '''
        def fetch_hosts_from_internet():
            url = settings.TEST_HOSTS_URL
            self._log(f'...Fetching hosts from {url}')

            try:
                hosts = requests.get(url)
            except ConnectionError:
                self._log(
                    f'Cannot fetch hosts from {url}', log_type='exception',
                )
                return

            if not hosts.ok:
                self._log(
                    f'Cannot fetch a list of hosts from {url}; '
                    f'the status code is {hosts.status_code}',
                    log_type='error',
                )
                return

            hosts = str(hosts.content).split('\\n')
            # we should drop all possible redundant symbols (there are
            # lots of them if the data is fetched from the web)
            # and it seems that the simplest solution is to search
            # for the regex pattern in every string
            pattern = re.compile(settings.IP_PORT_RE_PATTERN)
            return [h for h in hosts if pattern.search(h)]

        def fetch_hosts_from_file():
            self._log(f'...Fetching hosts from {settings.HOSTS_FILE} file')

            with open(settings.HOSTS_FILE, 'r') as reader:
                hosts = reader.read()

            # we should drop redundant symbols from the response and convert it
            # to a list of hosts
            hosts = hosts.split('\n')
            pattern = re.compile(settings.IP_PORT_RE_PATTERN)
            return [h for h in hosts if pattern.search(h)]

        hosts = fetch_hosts_from_file()

        # if data cannot be fetched from web
        # we should use local copy of the data
        if not hosts:
            hosts = fetch_hosts_from_internet()

            if not hosts:
                raise OSError('Hosts cannot be fetched')

        if settings.FETCHING_LIMIT:
            hosts = hosts[:settings.FETCHING_LIMIT]

        self._log(f'{len(hosts)} hosts has been fetched')
        return hosts

    def _create_host_port_list(self, hosts):
        ''' The probe requires ports to be defined explicitly
        This method converts provided list of hosts with
        '178.255.201.20:444'-like values (or just ip addresses)
        to a list of dictionaries with the following format:
        {host: 178.255.201.20, port: 444}
        '''
        return [
            {'host': h.split(':')[0], 'port': h.split(':')[1]} if ':' in h
            else {'host': h.split(':')[0], 'port': None}
            for h in hosts
        ]

    async def probe(self, host, port=None):
        ''' We send the probe in a coroutine since mtrpacket operates
        asynchronously. In a more complex program, it will allow
        other asynchronous operations to be processed concurrently
        with the probe.
        '''
        async with mtrpacket.MtrPacket() as mtr:
            # port must be provied explicitly and when provided
            # explicitly it cannot be None
            if port:
                result = await mtr.probe(
                    host, port=port, timeout=settings.PING_TIMEOUT,
                )
            else:
                result = await mtr.probe(host, timeout=settings.PING_TIMEOUT)

            #  If the ping got a reply, report the IP address and time
            if result.success:
                self._log('...got a reply from {} in {} ms'.format(
                    result.responder, result.time_ms,
                ))
            else:
                message = f'...no reply from {host}'

                if port:
                    message += f':{port}'

                self._log(message)

            return {
                'host': host, 'port': port, 'success': result.success,
                'timems': result.time_ms,
            }

    async def probe_with_semaphore(self, semaphore, host, port):
        ''' Sempaphore is necessary since when 500+ icmp requests
        are run simultaneously, the following exception is generated
        for some of them:

            Exception ignored when trying to write to the signal wakeup fd:
            BlockingIOError: [Errno 11] Resource temporarily unavailable

        There may be more robust solution but I decided to use semaphore
        since it justworks

        This article provided insight on how to solve the problem:
        https://pawelmhm.github.io/asyncio/python/aiohttp/2016/04/22/asyncio-aiohttp.html

        '''
        async with semaphore:
            return await self.probe(host, port)

    async def run(self):
        ''' Invokes the probe. Returns a list of ProbeResult objects
        which look as follows:
        ProbeResult(success=True, result='reply', time_ms=48.274,
        responder='178.255.201.52', mpls=[]).

        https://github.com/matt-kimball/mtr-packet-python

        ProbeResult.success: A boolean which is True only if the probe arrived
        at the target host.

        ProbeResult.time_ms: A floating point value indicating the number
        of milliseconds the probe was in-transit, prior to receiving a result.
        This value will be None in cases other than 'reply' or 'ttl-expired'

        ProbeResult.result: Common values are 'reply' for a probe which arrives
        at the target host, 'ttl-expired' for a probe which has
        its "time to live" counter reach zero before arriving
        at the target host, and 'no-reply' for a probe which is unanswered
        before its timeout value.

        ProbeResults are, basically, dictionaries.
        '''
        self._log(f'pinging {len(self.hosts)} hosts...')
        # semaphore is needed to avoid BlockingIOError
        # when running many requests
        semaphore = asyncio.Semaphore(settings.SEMAPHORE_LIMIT)

        start = time.time()

        tasks = [
            asyncio.create_task(
                self.probe_with_semaphore(
                    semaphore,
                    data['host'],
                    data['port'],
                )
            )
            for data in self.hosts
        ]
        try:
            results = await asyncio.gather(*tasks, return_exceptions=False)
        except Exception:
            self._log('Main async loop failed', log_type='exception')
            raise

        self._log(
            'It took {} seconds to process {} hosts '
            'which is {} seconds per 100 hosts'.format(
                time.time() - start,
                len(self.hosts),
                (time.time() - start) * 100 / len(self.hosts[:700])
            )
        )
        self._log(
            'There were {} broken hosts'.format(
                len([r for r in results if not r['success']])
            )
        )

        # everythin should be converted to string before making a db call
        db_requests = [
            {
                'host': "'{}'".format(batch['host']),
                'ping_timestamp': 'NOW()',
                'result': str(batch['success'])
            } for batch in results
        ]
        cache_batch = {
            batch['host']: batch['success'] for batch in results
        }

        db_connector = AsyncDBConnector()
        cache_connector = AsyncRedisConnector()

        self._log('Saving the results to the database...')
        await db_connector.insert(settings.PINGER_TABLE, db_requests)

        self._log('Adding the results to the cache...')
        await cache_connector.write_batch(cache_batch)


if __name__ == "__main__":
    pinger = ICMPPinger()
    asyncio.run(pinger.run())
