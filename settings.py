import os


# TODO: store these credentials in secure place if use non-locally
PG_HOST = os.environ.get('POSTGRES_HOST')
PG_DB = os.environ.get('POSTGRES_DB')
PG_USER = os.environ.get('POSTGRES_USER')
PG_PASSWORD = os.environ.get('POSTGRES_PASSWORD')

PINGER_TABLE = 'pinger_data'

REDIS_HOST = os.environ.get('REDIS_HOST')
REDIS_PORT = os.environ.get('REDIS_PORT')

TEST_HOSTS_URL = 'https://public-dns.info//nameservers-all.txt'
HOSTS_FILE = 'hosts'

PING_TIMEOUT = 2  # mtr default is 10 seconds
FETCHING_LIMIT = 1000  # limits number of pinged hosts

# regex patterns representing IPv4 address or IPv4:port format
IP_RE_PATTERN = '^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
IP_PORT_RE_PATTERN = '({})|({}:[0-9]+$)'.format(
    IP_RE_PATTERN,
    IP_RE_PATTERN[:-1],  # dropping $ so we could rewrite the ending
)

LOG_FORMATTER = '%(asctime)s.%(msecs)03d %(levelname)s %(module)s -> %(message)s'
LOG_DATE_TIME = '%Y-%m-%d %H:%M:%S'

# semaphore is needed to avoid BlockingIOError when running many requests
# simultaneously. The number is a result of trial and error process
# and it's specific for my machine (which is quite slow)
# One should play with it to understand the largest value which
# does not lead to corrupted results (may be up to 1000 or even more)
SEMAPHORE_LIMIT = 200
