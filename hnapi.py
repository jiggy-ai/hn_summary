#
# functions to access the HN api
#
# https://github.com/HackerNews/API

import requests
from requests.packages.urllib3 import Retry
from requests.adapters import HTTPAdapter


class PrefixSession(requests.Session):
    """
    A requests.Session with good retry behavior by default 
    and a persistent url prefix to be used on every request operation.
    For example:
    s = PrefixSession("https://api.foo.com/v0")
    s.get("/version")
    results in GET https://api.foo.com/v0/version
    """    
    def __init__(self, prefix_url, *args, **kwargs):
        super(PrefixSession, self).__init__(*args, **kwargs)
        self.prefix_url = prefix_url
        super(PrefixSession, self).mount('https://',
                                         HTTPAdapter(max_retries=Retry(connect=5,
                                                                       read=5,
                                                                       status=5,
                                                                       redirect=2,
                                                                       backoff_factor=.001,
                                                                       status_forcelist=(500, 502, 503, 504))))
    def request(self, method, url, *args, **kwargs):
        url = self.prefix_url + url
        return super(PrefixSession, self).request(method, url, *args, **kwargs)
        


session = PrefixSession("https://hacker-news.firebaseio.com/v0")

def get_topstories():
    """
    return list of the integer ids of the current top stories
    """
    return session.get("/topstories.json").json()


def get_item(item_id):
    """
    return the contents of the specified item as a dict
    """
    return session.get(f"/item/{item_id}.json").json()


