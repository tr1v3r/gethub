#!/usr/bin/env python3
__author__ = "riverchu"

import requests
import logging
import re
import time
import pattern

logger = logging.getLogger(__name__)


def filterhtml(html, patterns):
    logger.info("Getting urls from html...")
    reslist = []
    for pattern in patterns:
        res = re.findall(pattern, html)
        res = list(set(res))
        reslist.extend(res)
    logger.debug("Getting {} items...".format(len(reslist)))
    return reslist


def gethtml(url):
    logger.info("Getting {}...".format(url))
    proxies = {
        # 'http': 'http://localhost:1087',
        # 'https': 'http://localhost:1087',
    }
    cookie = ''
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.102 Safari/537.36',
        'cookie': cookie
    }
    html = requests.get(url, headers=headers, proxies=proxies).text
    logger.debug("Html length {}...".format(len(html)))
    if html.find('You have triggered an abuse detection mechanism.') != -1:
        logger.info("Wait 10s...")
        time.sleep(10)
        return gethtml(url)
    else:
        return html


def mining_page(url, respo):
    while True:
        logger.debug("Mining page {}...".format(url))
        html = gethtml(url)
        yield html

        patterns = pattern.for_mining_release(respo=respo)
        next_page = filterhtml(html, patterns)
        if len(next_page) > 0:
            url = next_page[0]
        else:
            break
