#!/usr/bin/env python3
__author__ = "riverchu"

import requests
import re
import subprocess
import os
import shutil
import hashlib
import sys
import logging
import time
from requests.cookies import RequestsCookieJar

logging.basicConfig(level=logging.DEBUG, format="[%(asctime)s][%(levelname)s][%(funcName)s:%(lineno)s] %(message)s")
logger = logging.getLogger(__name__)


class Urls:
    base_url = ""
    exact_url = ""
    search_urls = []
    detail_urls = []
    download_urls = []
    downloaded_urls = []

    def __init__(self, base_url=None, exact_url=None):
        self.base_url = base_url
        self.exact_url = exact_url

    def add_search(self, url):
        if url is None or url == "":
            return
        elif isinstance(url, list):
            self.search_urls.extend(url)
        elif isinstance(url, str):
            self.search_urls.append(url)

    def empty_search(self):
        self.search_urls = []

    def add_detail(self, url):
        if url is None or url == "":
            return
        elif isinstance(url, list):
            self.detail_urls.extend(url)
        elif isinstance(url, str):
            self.detail_urls.append(url)

    def empty_detail(self):
        self.detail_urls = []

    def add_download(self, url):
        if url is None or url == "":
            return
        elif isinstance(url, list):
            self.download_urls.extend(url)
        elif isinstance(url, str):
            self.download_urls.append(url)

    def empty_download(self):
        self.download_urls = []

    def add_downloaded(self, url):
        if url is None or url == "":
            return
        elif isinstance(url, list):
            self.downloaded_urls.extend(url)
        elif isinstance(url, str):
            self.downloaded_urls.append(url)

    def empty_downloaded(self):
        self.downloaded_urls = []

    def empty_all(self):
        self.empty_search()
        self.empty_detail()
        self.empty_download()
        self.empty_downloaded()

    def reset(self):
        self.base_url = ""
        self.exact_url = ""
        self.empty_all()


class OperateFile:
    dstpath = ""
    storepath = ""
    collect_filetype = []
    record_file = "record.txt"
    recorded_file = "recorded.txt"

    def __init__(self, storepath, dstpath):
        self.dstpath = dstpath
        self.storepath = storepath

    def add_filetype(self, filetype):
        if filetype is None:
            return
        elif isinstance(filetype, list):
            self.collect_filetype.extend(filetype)
        elif isinstance(filetype, str):
            self.collect_filetype.append(filetype)

    def reset(self):
        self.dstpath = ""
        self.storepath = ""
        self.collect_filetype = []

    def unzip(self, filename, specifydir=True, storepath=None):
        logger.info("Unzip {}...".format(filename))
        try:
            if filename is None:
                return None

            if specifydir is True:
                storepath = self.storepath if storepath is None else storepath
            else:
                storepath = '.'

            if filename.endswith('.tar.gz'):
                directory = '{}/{}'.format(storepath, filename.replace('.tar.gz', ''))
                os.makedirs(directory, exist_ok=True)
                subprocess.run(["tar", "xzf", filename, '-C', directory])
            elif filename.endswith('.zip'):
                directory = '{}/{}'.format(storepath, filename.replace('.zip', ''))
                os.makedirs(directory, exist_ok=True)
                subprocess.run(["unzip", "-o", filename, '-d', directory])
            else:
                logger.error('Wrong type. Now supports .tar.gz .zip')
                return None

            return directory
        except Exception as e:
            logger.error(e)

    def collectfile(self, directory):
        logger.info("Collecting {}...".format(directory))
        if directory is None:
            return None
        for fpath, dirs, fs in os.walk(directory):
            for filename in fs:
                if os.path.splitext(filename)[1] in self.collect_filetype:
                    self.movefile(fpath + '/' + filename)

    def movefile(self, srcname, dstpath=None):
        try:
            if not os.path.exists(srcname):
                logger.error("Src file {} is not exists.".format(srcname))
                return None

            dstpath = self.dstpath if dstpath is None else dstpath

            md5er = hashlib.md5()
            with open(srcname, 'rb') as f:
                md5er.update(f.read())
            md5sum = md5er.hexdigest()

            fpath, fname = os.path.split(srcname)
            type_ = os.path.splitext(fname)[1]
            dstname = '{}/{}/{}{}'.format(dstpath, type_[1:], md5sum, type_)
            if os.path.exists(dstname):
                logger.debug('{} exists...'.format(dstname))
                return
            logger.debug('Move {} ----> {}'.format(srcname, dstname))
            shutil.copyfile(srcname, dstname)
        except Exception as e:
            logger.error(e, exc_info=True)

    def removetar(self, filename, storepath=None):
        logger.info("Remove package {}...".format(filename))
        if filename is None or filename == "":
            return
        storepath = self.storepath if storepath is None else storepath

        if os.path.exists(filename):
            subprocess.run(['rm', '-rf', filename])
            subprocess.run(['rm', '-rf', '{}/{}'.format(storepath, filename.replace('.tar.gz', ''))])
            subprocess.run(['rm', '-rf', '{}/{}'.format(storepath, filename.replace('.zip', ''))])

    def save(self, mode, type, record=None, recorded=None):
        '''

        :param mode: collect, downloaded
        :param type: url, respository
        :param record:
        :param recorded:
        :return:
        '''
        if mode == "collect":
            with open(self.record_file, 'a') as f:
                for item in record:
                    f.write("{},{}\n".format(type, item))
        elif mode == 'downloaded':
            recorded = []
            if os.path.exists(self.recorded_file):
                with open(self.recorded_file, 'r') as f:
                    recorded = list(f.readlines())
                    recorded = map(lambda item: item.strip('\r\n'), recorded)
            record = "{},{}".format(type, record)
            if record not in recorded:
                with open(self.recorded_file, 'a') as f:
                    f.write("{}\n".format(record))

    def read(self, respository, download_record):
        if os.path.exists(self.record_file):
            with open(self.record_file, 'r') as f:
                for line in f.readlines():
                    type, record = line.strip('\r\n').split(',')
                    if type == "url":
                        download_record.append(record)
                    elif type == "respository":
                        respository.append(record)

        if os.path.exists(self.recorded_file):
            with open(self.recorded_file, 'r') as f:
                for line in f.readlines():
                    type, record = line.strip('\r\n').split(',')
                    if type == "url" and record in download_record:
                        download_record.remove(record)
                    elif type == "respository" and record in respository:
                        respository.remove(record)

    def set_recordfile(self, record_file=None, recorded_file=None):
        if record_file is not None:
            self.record_file = record_file
        if recorded_file is not None:
            self.recorded_file = recorded_file


class GetCode:
    respository = []
    start_page = 1
    end_page = 1
    url = None
    file = None

    def __init__(self, dstpath="", storepath="", baseurl=None, exacturl=None, start_page=1, end_page=1):
        logger.debug('Initial...')
        self.url = Urls(base_url=baseurl, exact_url=exacturl)
        self.file = OperateFile(storepath=storepath, dstpath=dstpath)
        self.file.add_filetype([".php", ".jsp"])

        self.start_page = start_page
        self.end_page = end_page

    def reset(self):
        self.respository = []
        self.start_page = 1
        self.end_page = 1
        self.url.empty_all()
        self.file.reset()

    def gen_urls(self, mode='search'):
        logger.info("Generate {} urls...".format(mode))
        if mode == "search":
            if self.start_page == 1:
                self.url.add_search("{}{}".format(self.url.base_url, self.url.exact_url))
            for page in range(self.start_page + 1, self.end_page + 1):
                self.url.add_search("{}{}&p={}".format(self.url.base_url, self.url.exact_url, page))
        elif mode == 'detail':
            self.url.add_detail(["{}/{}/releases".format(self.url.base_url, respo) for respo in
                                 self.respository])
        elif mode == 'download':
            urls = map(lambda url: url if url.startswith('http://') or url.startswith('https://') else "{}{}".format(
                self.url.base_url, url), self.url.download_urls)
            urls = list(urls)
            self.url.add_download(urls)

    @staticmethod
    def gen_patterns(mode='search', filetype='tar', respo=None):
        logger.info("Generate {} patterns...".format(mode))
        patterns = list()
        if mode == 'search':
            pattern = [r'<a class="v-align-middle" data-hydro-click.*?href="/(.*?)">',
                       r'<a class="text-bold" href="/(.*?)">']
            patterns.extend(pattern)
        elif mode == 'download':
            if filetype == 'tar':
                pattern = [r"/{}/archive/.*?.tar.gz".format(respo)]
                patterns.extend(pattern)
            elif filetype == 'zip':
                pattern = [r"/{}/archive/.*?.zip".format(respo)]
                patterns.extend(pattern)
        elif mode == 'mining':
            pattern = [r'<a rel="nofollow" href="(https://github.com/[\w/\-]+?/releases\?after=[\d\.\w\-]+?)">Next']
            patterns.extend(pattern)
        return patterns

    @staticmethod
    def gethtml(url):
        logger.info("Getting {}...".format(url))
        html = requests.get(url).text
        logger.debug("Html length {}...".format(len(html)))
        if html.find('You have triggered an abuse detection mechanism.') != -1:
            logger.info("Wait 10s...")
            time.sleep(10)
            return GetCode.gethtml(url)
        else:
            return html

    @staticmethod
    def filterhtml(html, patterns):
        logger.info("Getting urls from html...")
        reslist = []
        for pattern in patterns:
            res = re.findall(pattern, html)
            res = list(set(res))
            reslist.extend(res)
        logger.debug("Getting {} items...".format(len(reslist)))
        return reslist

    @staticmethod
    def download(url, base_url=None, storepath="."):
        if not url.startswith('http://') and not url.startswith('https://'):
            url = base_url + url
        # url = url.split('/')
        # url[2] = 'codeload.' + url[2]
        # url[5] = 'tar.gz'
        # url[6] = url[6].replace('.tar.gz', '')
        # url = '/'.join(url)

        logger.info("Downloading {}...".format(url))
        try:
            res = requests.get(url, timeout=180)
        except Exception as e:
            logger.error('Download failed...\n.{}'.format(e), exc_info=True)
            return None

        filename = url.split('/')[-1]
        full_path = "{}/{}".format(storepath, filename)
        with open(full_path, 'wb') as f:
            f.write(res.content)

        logger.info("Download file {}...".format(filename))
        return full_path

    @staticmethod
    def gitclone(respo, base_url=None, storepath='.'):
        base_url = "https://github.com/" if base_url is None else base_url

        download_url = "{}{}.git".format(base_url, respo)
        full_path = '{}/{}'.format(storepath, respo.split('/')[-1])
        subprocess.run(["git", "clone", download_url, full_path])

        return full_path

    def mining_page(self, url):
        while True:
            logger.debug("Mining page {}...".format(url))
            html = self.gethtml(url)
            yield html

            patterns = self.gen_patterns(mode='mining')
            next_page = self.filterhtml(html, patterns)
            if len(next_page) > 0:
                url = next_page[0]
            else:
                break

    def getready(self):
        logger.debug("Get ready...")
        self.gen_urls(mode="search")
        for url in self.url.search_urls:
            html = self.gethtml(url)
            patterns = self.gen_patterns(mode='search')
            self.respository.extend(self.filterhtml(html, patterns))
        self.respository = list(set(self.respository))
        self.gen_urls(mode="detail")

    def getdetail(self):
        logger.info("Get detail...")
        for detail_url in self.url.detail_urls:
            for html in self.mining_page(detail_url):
                patterns = self.gen_patterns(mode='download',
                                             respo='/'.join(detail_url.split('/')[3:5]))
                download_urls = self.filterhtml(html, patterns)
                self.url.download_urls.extend(download_urls)
        self.url.download_urls = list(set(self.url.download_urls))
        self.gen_urls(mode="download")

    def getfile(self):
        logger.info("Start download...")
        try:
            for url in self.url.download_urls:
                filename = self.download(url, base_url=self.url.base_url, storepath=self.file.storepath)
                directory = self.file.unzip(filename, )
                self.file.collectfile(directory)
                self.file.removetar(filename)
                self.file.save(mode='downloaded', type='url', record=url)
                logger.info("{} done...".format(filename))
            logger.info("All done...")
        except Exception as e:
            logger.error(e, exc_info=True)

    def getsource(self):
        logger.info("Start git clone...")
        try:
            for respo in self.respository:
                if respo in [None, ""]:
                    continue
                directory = self.gitclone(respo=respo, storepath=self.file.storepath)
                self.file.collectfile(directory)
                self.file.removetar(directory)
                self.file.save(mode='downloaded', type='respository', record=respo)
                logger.info("{} done...".format(respo))
        except Exception as e:
            logger.error(e, exc_info=True)

    def geton(self, mode):
        if mode == 'web':
            self.getready()
            self.getdetail()
            self.file.save(mode="collect", type='url', record=self.url.download_urls)
            self.file.save(mode="collect", type='respository', record=self.respository)
        elif mode == 'file':
            self.file.read(self.respository, self.url.download_urls)
        self.getsource()
        self.getfile()


if __name__ == "__main__":
    get = GetCode(dstpath='white', storepath='github', baseurl="https://github.com",
                  exacturl='/search?l=Java+Server+Pages&q=import%3D"java.util.%2A&type=Code', start_page=1,
                  end_page=10)
    get.geton(mode='web')
