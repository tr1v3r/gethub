#!/usr/bin/env python3
__author__ = "riverchu"

import subprocess
import os
import shutil
import hashlib
import logging
import requests
import crawler
import pattern
import json

logging.basicConfig(level=logging.DEBUG, format="[%(asctime)s][%(levelname)s][%(funcName)s:%(lineno)s] %(message)s")
logger = logging.getLogger(__name__)


class Respository:
    base_url = "https://github.com"
    name = None
    release_urls = []
    store_dir = "."

    is_cloned = False
    collected = []

    def __init__(self, name, storedir='.'):
        self.name = name
        self.store_dir = storedir

    def reset(self):
        self.base_url = "https://github.com"
        self.name = None
        self.release_urls = []
        self.store_dir = "."

        self.is_cloned = False
        self.collected.clear()

    def set_storedir(self, storedir):
        self.store_dir = storedir

    def init_by_info(self, info):
        d = None
        if isinstance(info, str):
            d = json.loads(info)
        elif isinstance(info, dict):
            d = info
        self.name = d['name']
        self.release_urls = d['release_urls']
        self.is_cloned = d['is_cloned']
        self.collected = d['collected']

    def update(self, respo):
        if isinstance(respo, Respository) and self.name == respo.name:
            self.release_urls = respo.release_urls
            self.is_cloned = respo.is_cloned
            self.collected = respo.collected

    def collect_releases(self):
        logger.info("Collect releases...")
        try:
            releases_url = "{}/{}/releases".format(self.base_url, self.name)

            for html in crawler.mining_page(releases_url, respo=self.name):
                patterns = pattern.for_release(self.name)
                release_urls = crawler.filterhtml(html, patterns)
                self.release_urls.extend(release_urls)

            self.release_urls = list(set(self.release_urls))
        except Exception as e:
            logger.error('Download failed...\n.{}'.format(e), exc_info=True)

        return len(self.release_urls)

    def get_clone(self, storedir=None):
        if self.is_cloned:
            return ""

        logger.info("Git clone...")

        storedir = self.store_dir if storedir is None else storedir
        store_path = ""

        try:
            git_url = "{}/{}.git".format(self.base_url, self.name)
            store_path = '{}/{}'.format(storedir, self.name.split('/')[-1])
            subprocess.run(["git", "clone", git_url, store_path])
        except Exception as e:
            logger.error('Clone {} failed...\n.{}'.format(self.name, e), exc_info=True)

        self.is_cloned = True
        return store_path

    def get_all_releases(self, storedir=None):
        storedir = self.store_dir if storedir is None else storedir

        return list(self.get_releases(storedir=storedir))

    def get_releases(self, storedir=None):
        storedir = self.store_dir if storedir is None else storedir

        for url in self.release_urls:
            yield self.get_release(url, storedir=storedir)

    def get_release(self, url, storedir=None):
        storedir = self.store_dir if storedir is None else storedir

        if not url.startswith('http://') and not url.startswith('https://'):
            url = self.base_url + url
        # url = url.split('/')
        # url[2] = 'codeload.' + url[2]
        # url[5] = 'tar.gz'
        # url[6] = url[6].replace('.tar.gz', '')
        # url = '/'.join(url)

        if url in self.collected:
            return ""

        logger.info("Downloading {}...".format(url))
        try:
            filename = url.split('/')[-1]
            store_path = "{}/{}".format(storedir, filename)
            subprocess.run(["wget", "-P", storedir, url])
            logger.info("Save file {}...".format(filename))
        except Exception as e:
            logger.error('Download failed...\n.{}'.format(e), exc_info=True)
            return ""

        self.add_collected(url)
        return store_path

    def get_raw(self):
        pass

    def add_collected(self, url):
        if url in [None, '']:
            return
        if isinstance(url, str) and url not in self.collected:
            self.collected.append(url)
            return True
        elif isinstance(url, list):
            self.collected.extend(url)
            self.collected = list(set(self.collected))
        return False

    def to_dict(self):
        d = dict()
        d['name'] = self.name
        d['release_urls'] = self.release_urls
        d['is_cloned'] = self.is_cloned
        d['collected'] = self.collected
        return d

    def to_json(self):
        return json.dumps(self.to_dict())


class Cluster:
    respos = []
    operator = None
    store_dir = None
    dst_dir = None

    def __init__(self):
        pass

    def set_dir(self, storedir, dstdir):
        self.store_dir = storedir
        self.dst_dir = dstdir

    def set_operator(self, operator):
        self.operator = operator

    def format(self):
        self.operator.set_path(storedir=self.store_dir, dstdir=self.dst_dir)
        for respo in self.respos:
            respo.set_storedir(self.store_dir)

    def respo_collect(self):
        logger.info("Collect respoitory...")
        for respo in self.respos:
            if not isinstance(respo, Respository):
                continue

            try:
                path = respo.get_clone()
                self.operator.collectfile(path)
                self.operator.remove(path)
                self.save()

                respo.collect_releases()
                self.save()
                for path in respo.get_releases():
                    directory = self.operator.unzip(path)
                    self.operator.collectfile(directory)
                    self.operator.remove(directory)
                    self.operator.remove(path)
                    self.save()
            except Exception as e:
                logger.error(e, exc_info=True)

            self.save()

    def add_respo(self, respo):
        if isinstance(respo, Respository):
            if respo.name not in self.respos_name():
                logger.debug("Add respoitory {}...".format(respo.name))
                self.respos.append(respo)
            else:
                logger.info("Update respoitory {}...".format(respo.name))
                respo_ = self.get_respobyname(respo.name)
                respo_.update(respo)
        elif isinstance(respo, str):
            logger.debug("Add respoitory {}...".format(respo))
            if respo not in self.respos_name():
                respo = Respository(respo, self.store_dir)
                self.respos.append(respo)
            else:
                logger.info("Had respoitory {}...".format(respo))
        elif isinstance(respo, list):
            for respo_ in respo:
                self.add_respo(respo_)
        else:
            logger.info("Wrong type when add respo: {}...".format(respo))

    def remove_respo(self, respo):
        if isinstance(respo, Respository):
            logger.debug("Remove respoitory {}...".format(respo.name))
            if respo.name in self.respos_name():
                self.respos.remove(respo)
            else:
                logger.info("No respoitory {}...".format(respo.name))
        elif isinstance(respo, str):
            logger.debug("Remove respoitory {}...".format(respo))
            if respo in self.respos_name():
                respo = self.get_respobyname(respo)
                self.respos.remove(respo)
            else:
                logger.info("No respoitory {}...".format(respo))
        elif isinstance(respo, list):
            for respo_ in respo:
                self.remove_respo(respo_)

    def respos_name(self):
        name = list()
        for respo in self.respos:
            name.append(respo.name)
        name = list(set(name))
        return name

    def get_respobyname(self, respo_name):
        for respo in self.respos:
            if respo.name == respo_name:
                return respo
        return None

    def format_respo(self):
        for respo in self.respos:
            if respo.store_dir is None:
                respo.store_dir = self.store_dir

    def clear(self):
        self.respos.clear()

    def save(self):
        logger.info("Save cluster info into {}...".format(self.operator.record_file))
        self.operator.save(self.to_json())

    def read(self):
        logger.info("Read cluster info from {}...".format(self.operator.record_file))
        try:
            cluster_info = self.operator.read()
            if cluster_info in [None, ""]:
                logger.info("Read None info from {}...".format(self.operator.record_file))
                return
            cluster_info = json.loads(cluster_info)
            for name in cluster_info:
                respo = Respository(name)
                respo.init_by_info(cluster_info[name])
                self.add_respo(respo)
            logger.info("Collect {}'s respo info...".format(len(self.respos)))
        except Exception as e:
            logger.error(e, exc_info=True)

    def to_dict(self):
        respo_dict = dict()
        for respo in self.respos:
            if respo.name in respo_dict.keys():
                continue
            respo_dict[respo.name] = respo.to_dict()
        return respo_dict

    def to_json(self):
        return json.dumps(self.to_dict())


class FileOperator:
    dstdir = ""
    storedir = ""
    collect_filetype = []
    record_file = "record-new.txt"

    def __init__(self, storedir="", dstdir=""):
        self.dstdir = dstdir
        self.storedir = storedir

    def set_path(self, storedir=None, dstdir=None):
        self.storedir = self.storedir if storedir is None else storedir
        self.dstdir = self.dstdir if dstdir is None else dstdir

    def add_filetype(self, filetype):
        if filetype is None:
            return
        elif isinstance(filetype, list):
            self.collect_filetype.extend(filetype)
        elif isinstance(filetype, str):
            self.collect_filetype.append(filetype)

    def reset(self):
        self.dstdir = ""
        self.storedir = ""
        self.collect_filetype = []
        self.record_file = "record.txt"

    def unzip(self, filename, specifydir=False, storedir=None):
        logger.info("Unzip {}...".format(filename))
        try:
            if filename is None:
                return None

            unzip_dir = os.path.split(filename)[-1].split('.')[0]

            if specifydir is True:
                storedir = self.storedir if storedir is None else storedir
                directory = "{}/{}".format(storedir, unzip_dir)
            else:
                directory = "{}/{}".format(os.path.dirname(filename), unzip_dir)

            os.makedirs(directory, exist_ok=True)

            if filename.endswith('.tar.gz'):
                subprocess.run(["tar", "xzf", filename, '-C', directory])
            elif filename.endswith('.zip'):
                subprocess.run(["unzip", "-o", filename, '-d', directory])
            else:
                logger.error('Wrong type. Now supports .tar.gz .zip')
                return None

            return directory
        except Exception as e:
            logger.error(e, exc_info=True)
            return None

    def collectfile(self, directory):
        logger.info("Collecting {}...".format(directory))
        if directory in [None, ""]:
            return None
        try:
            for fpath, dirs, fs in os.walk(directory):
                for filename in fs:
                    if os.path.splitext(filename)[1] in self.collect_filetype:
                        self.movefile(fpath + '/' + filename)
        except Exception as e:
            logger.error(e, exc_info=True)

    def movefile(self, srcname, dstdir=None):
        try:
            if not os.path.exists(srcname):
                logger.error("Src file {} is not exists.".format(srcname))
                return None

            dstdir = self.dstdir if dstdir is None else dstdir

            md5er = hashlib.md5()
            with open(srcname, 'rb') as f:
                md5er.update(f.read())
            md5sum = md5er.hexdigest()

            fpath, fname = os.path.split(srcname)
            type_ = os.path.splitext(fname)[1]
            dstname = '{}/{}/{}{}'.format(dstdir, type_[1:], md5sum, type_)
            if os.path.exists(dstname):
                logger.debug('{} exists...'.format(dstname))
                return
            logger.debug('Move {} ----> {}'.format(srcname, dstname))
            shutil.copyfile(srcname, dstname)
        except Exception as e:
            logger.error(e, exc_info=True)

    def remove(self, filename):
        logger.info("Remove {}...".format(filename))
        if filename is None or filename == "":
            return

        if os.path.exists(filename):
            subprocess.run(['rm', '-rf', filename])

    def save(self, object_, storedir=None):
        storedir = self.storedir if storedir is None else storedir
        if isinstance(object_, str):
            with open("{}/{}".format(storedir, self.record_file), 'w') as f:
                f.write("{}\n".format(object_))
        else:
            logger.error('Save wrong type.')

    def read(self, storedir=None):
        storedir = self.storedir if storedir is None else storedir
        try:
            record_file_path = "{}/{}".format(storedir, self.record_file)
            if os.path.exists(record_file_path):
                with open(record_file_path, 'r') as f:
                    line = f.readlines()[0]
                    return line.strip('\r\n')
        except Exception as e:
            logger.error('Read failed...\n.{}'.format(e), exc_info=True)

    def clearfile(self):
        with open(self.record_file, 'w') as f:
            f.write("")

    def set_recordfile(self, record_file=None):
        if record_file is not None:
            self.record_file = record_file


class WebCollect:
    '''
    收集搜索结果html和对应urls
    '''
    base_url = ""
    exact_url = ""
    search_urls = []

    def __init__(self, base_url, exact_url):
        self.base_url = base_url
        self.exact_url = exact_url

    def add_search(self, url):
        if url is None or url == "":
            return
        elif isinstance(url, list):
            self.search_urls.extend(url)
        elif isinstance(url, str):
            self.search_urls.append(url)

    def remove_search(self, url=None):
        if url is None:
            self.search_urls.pop()
        elif url in self.search_urls:
            self.search_urls.remove(url)
        else:
            logger.info("No url {} in search urls...".format(url))

    def empty(self):
        self.search_urls.clear()


class GetCode:
    cluster = None
    start_page = 1
    end_page = 1
    collect = None
    file = None

    def __init__(self, dstdir="", storedir="", baseurl=None, exacturl=None, start_page=1, end_page=1):
        logger.debug('Initial...')

        self.collect = WebCollect(base_url=baseurl, exact_url=exacturl)

        self.cluster = Cluster()
        self.cluster.set_dir(storedir=storedir, dstdir=dstdir)
        fileopeartor = FileOperator()
        fileopeartor.add_filetype([".php", ".jsp"])
        self.cluster.set_operator(fileopeartor)
        self.cluster.format()

        self.start_page = start_page
        self.end_page = end_page

    def reset(self):
        self.cluster = Cluster()
        self.start_page = 1
        self.end_page = 1
        self.collect.empty()
        self.file.reset()

    def gen_collect_urls(self):
        logger.info("Generate search urls...")
        if self.start_page == 1:
            self.collect.add_search("{}{}".format(self.collect.base_url, self.collect.exact_url))
        for page in range(self.start_page + 1, self.end_page + 1):
            self.collect.add_search("{}{}&p={}".format(self.collect.base_url, self.collect.exact_url, page))

    def collect_respo(self):
        logger.debug("Collect respo...")
        for url in self.collect.search_urls:
            html = crawler.gethtml(url)
            patterns = pattern.for_search()
            self.cluster.add_respo(crawler.filterhtml(html, patterns))

    def geton(self, mode):
        try:
            if mode == 'web':
                self.gen_collect_urls()
                self.collect_respo()
            self.cluster.read()
            self.cluster.save()

            self.cluster.format()

            self.cluster.respo_collect()
        except Exception as e:
            logger.error(e, exc_info=True)


if __name__ == "__main__":
    get = GetCode(dstdir='存储目标文件绝对路径',
                  storedir='临时存储工程绝对路径',
                  baseurl="https://github.com",
                  exacturl='/search?l=Java+Server+Pages&q=cms&type=Code', start_page=1,
                  end_page=1)
    get.geton(mode='web')
