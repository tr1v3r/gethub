#!/usr/bin/env python3
__author__ = "riverchu"

import logging

logger = logging.getLogger(__name__)


def for_search():
    logger.info("Generate search patterns...")
    pattern = list()

    pattern.append(r'<a class="v-align-middle" data-hydro-click.*?href="/(.*?)">')
    pattern.append(r'<a class="text-bold" href="/(.*?)">')

    return pattern


def for_release(respo, filetype='tar'):
    logger.info("Generate release patterns...")
    pattern = list()

    if filetype == 'tar':
        pattern.append(r"/{}/archive/.*?.tar.gz".format(respo))
    elif filetype == 'zip':
        pattern.append(r"/{}/archive/.*?.zip".format(respo))

    return pattern


def for_mining_release(respo):
    logger.info("Generate mining patterns...")
    pattern = [r'<a rel="nofollow" href="(https://github.com/{}/releases\?after=[\d\.\w\-]+?)">Next'.format(respo)]
    return pattern
