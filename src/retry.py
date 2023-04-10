"""
retry decorator in a wsk style
"""
from loguru import logger
from time import sleep
from functools import wraps

def retry(ExceptionToCheck=Exception, tries=5, delay=0.5, backoff=2, ExceptionToRaise=AssertionError):
    """Retry calling the decorated function using an exponential backoff.

    http://www.saltycrane.com/blog/2009/11/trying-out-retry-decorator-python/
    original from: http://wiki.python.org/moin/PythonDecoratorLibrary#Retry

    :param ExceptionToCheck: the exception to check. may be a tuple of
        exceptions to check
    :type ExceptionToCheck: Exception or tuple
    :param tries: number of times to try (not retry) before giving up
    :type tries: int
    :param delay: initial delay between retries in seconds
    :type delay: int
    :param backoff: backoff multiplier e.g. value of 2 will double the delay
        each retry
    :type backoff: int
    :param ExceptionToRaise: exceptions that should be raised instead of retried.
        
    """
    def deco_retry(f):

        @wraps(f)
        def f_retry(*args, **kwargs):
            mtries, mdelay = tries, delay
            while mtries > 1:
                try:
                    return f(*args, **kwargs)
                except ExceptionToRaise as e:
                    raise e
                except ExceptionToCheck as e:
                    if mtries == 1: # only show full stack trace on last try
                        logger.exception(f"Exception: {e}")
                    logger.warning(f"Exception: {e}")
                    logger.info(f"retrying in {mdelay} seconds")
                    sleep(mdelay)
                    mtries -= 1
                    mdelay *= backoff
            return f(*args, **kwargs)

        return f_retry  # true decorator

    return deco_retry