#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
GTFS manager - (C) 2015 by geOps

A cache will be build in the GTFS directories, containing the valid period of GTFS feeds.

Usage:
  gtfsman.py [list | status | show] [--active | -a] [--notactive | -n] [--checkremotedate] [--base-folder=<path>]
  gtfsman.py show <feedname> [--checkremotedate]
  gtfsman.py update <feedname> [--dontbug] [--base-folder=<path>]
  gtfsman.py update-all [--base-folder=<path>] [--active | -a] [--notactive | -n] [--dontbug]
  gtfsman.py update-All [--base-folder=<path>] [--active | -a] [--notactive | -n] [--dontbug]
  gtfsman.py update-ALL [--base-folder=<path>] [--active | -a] [--notactive | -n] [--dontbug]
  gtfsman.py set-url <feedname> [<url>] [--base-folder=<path>]
  gtfsman.py set-pp <feedname> [<pp>] [--base-folder=<path>]
  gtfsman.py clear-cache | cc [--base-folder=<path>]
  gtfsman.py generate-cache [--base-folder=<path>]
  gtfsman.py init <feedname> [<url>] [--base-folder=<path>]
  gtfsman.py -h | --help
  gtfsman.py --version

Options:
  -h --help                     Show this screen.
  --version                     Show version.
  --checkremotedate             Check if the modification date of the remote file is newer than local files
  -l --list                     List all feeds.
  -a --active                   Only show feeds that are active
  -n --notactive                Only show feeds that are inactive
  --dontbug                     Don't break on warnings or ask for input, just do whats possible
  --base-folder=<path>          Change the base folder (default: cwd)
"""

import csv, os, sys
import zipfile
import urllib2
import httplib
from dateutil import parser
from datetime import datetime
from urlparse import urlparse
from os.path import relpath
import shutil

# do not require calendar.txt
GTFS_REQ_FILES = ['agency.txt', 'routes.txt', 'trips.txt', 'stops.txt', 'stop_times.txt']
GTFS_VALID_FILES = ['transfers.txt', 'frequencies.txt', 'agency.txt', 'routes.txt', 'trips.txt', 'stops.txt', 'stop_times.txt', 'feed_info.txt', 'calendar.txt', 'calendar_dates.txt', 'shapes.txt']

class GTFSManager(object):

    def __init__(self, options):
        self.options = options

        if not self.options['--base-folder']: self.options['--base-folder'] = os.getcwd()

        if self.options['list']:
            self.list()
        elif self.options['update']:
            self.update(self.options['<feedname>'])
        elif self.options['update-all']:
            self.update_all()
        elif self.options['update-All']:
            self.update_all(1)
        elif self.options['update-ALL']:
            self.update_all(2)
        elif self.options['set-url']:
            self._update_feed_url(self.options['<feedname>'], self.options['<url>'])
        elif self.options['set-pp']:
            self._store_postprocess_cmd(self.options['<feedname>'], self.options['<pp>'])
        elif self.options['show']:
            self._show_feed(self.options['<feedname>'])
        elif self.options['clear-cache'] or self.options['cc']:
            self._clear_caches()
        elif self.options['generate-cache']:
            self._generate_caches()
        elif self.options['init']:
            initpath = os.path.join(self.options['--base-folder'], self.options['<feedname>'])
            self.init(initpath)
        else:
            # if nothing is provided, answer with list
            self.list()

    def init(self, path):
        # make directory
        if not os.path.exists(path):
            os.makedirs(path)

        will_be_name = relpath(os.path.abspath(path), self.options['--base-folder'])

        url = self.options['<url>']

        if not url:
            # ask for zip URL
            url = raw_input('Enter feed URL for new feed "%s": ' % will_be_name)
        if self._download_feed(path, url):
            self._store_feed_url(url, path)
            self._clear_cache(path)
            self._get_feed_by_name(will_be_name)
            print '\033[92mInitialized new feed in %s \033[0m' % path
        else:
            print '\033[91mInitialization of %s failed.\033[0m' % path

    def list(self):
        for f in self._loadfeeds():
            self._print_feed(f)

    def update(self, feedname):
        feed = self._get_feed_by_name(feedname)
        if not feed:
            sys.stderr.write('No feed named "%s" found...\n' % feedname)
            return
        self.update_feed(feed)

    def update_feed(self, feed):
        print 'Trying to update "%s"...' % feed['name']
        if not feed['url']:
            print 'No feed URL stored for "%s" in feed_url.txt' % feed['name']
            if self.options['--dontbug']:
                return
            feed['url'] = raw_input('Enter feed URL: ')
            self._store_feed_url(feed['url'], feed['fullpath'])

        if self._download_feed(feed['fullpath'], feed['url']):
            # rewrite cache by calling feed load
            self._clear_cache(feed['fullpath'])
            self._get_feed_by_name(feed['name'])
            print '\033[92mUpdated %s\033[0m' % feed['name']

    def _download_feed(self, path, url):
        url = urlparse(url)
        try:
            self._get_zip(url, path)
            self._extract_zip(path)
        except Exception as e:
            sys.stderr.write('\033[91mCould not fetch %s, skipping.\n' % url.geturl().strip())
            sys.stderr.write('\033[91mProblem: %s\033[0m\n' % str(e))
            return False

         # call postprocess
        if not self._postprocess(path):
            sys.stderr.write('\033[91mError while executing postprocess cmd for %s\033[0m\n' % url.geturl().strip())
            exit(1)
        return True

    def update_all(self, forcelevel = 0):
        for f in self._loadfeeds():
            daydiff = (datetime.now() - f['data_to']).days
            if daydiff > 0 or (daydiff > -7 and forcelevel == 1) or forcelevel == 2:
                self.update_feed(f)

    def _update_feed_url(self, feedname, url):
        feed = self._get_feed_by_name(feedname)
        if not url:
            url = raw_input('Enter feed URL: ')
        if not feed:
            sys.stderr.write('No feed named "%s" found...\n' % str(feedname))
            return
        self._store_feed_url(url, feed['fullpath'])

    def _get_zip(self, url, path):
        store_file = os.path.join(path, 'gtfs.zip')
        u = urllib2.urlopen(url.geturl())
        f = open(store_file, 'wb')
        meta = u.info()
        file_size = None
        if meta.getheaders('Content-Length'):
            file_size = int(meta.getheaders('Content-Length')[0])
            print 'Downloading %s to %s (%s kB)' % (url.geturl().strip(), store_file, file_size / 1024)
        else:
            print 'Downloading %s to %s' % (url.geturl().strip(), store_file)

        file_size_dl = 0
        block_sz = 8192
        while True:
            buffer = u.read(block_sz)
            if not buffer:
                break

            file_size_dl += len(buffer)
            f.write(buffer)
            if file_size:
                status = r"%8d kB  [%3.2f%%]" % (file_size_dl / 1024, file_size_dl * 100. / file_size)
            else:
                status = r"%8d kB" % (file_size_dl / 1024)
            status = status + chr(8) * (len(status)+1)
            print status,

        f.close()

    def _extract_zip(self, path):
        zfile = os.path.join(path, 'gtfs.zip')
        print "Extracting zip file " + zfile
        with zipfile.ZipFile(zfile) as gtfs_zip:
             for member in gtfs_zip.namelist():
                filename = os.path.basename(member)
                if filename in GTFS_VALID_FILES:
                    source = gtfs_zip.open(member)
                    target = file(os.path.join(path, filename), "wb")
                    with source, target:
                        shutil.copyfileobj(source, target)

        os.remove(zfile)

    def _get_feed_by_name(self, name):
        feeds = self._loadfeeds(name)
        for f in feeds:
            if f['name'] == name:
                return f
        return None

    def _show_feed(self, feedname):
        if not feedname:
            return self.list()

        f = self._loadfeed(feedname)
        if not f:
            sys.stderr.write('No feed named "%s" found...\n' % str(feedname))
            return

        colort = '\033[92m'
        colorf = '\033[92m'

        daydiff = (datetime.now() - f['data_to']).days
        if daydiff > -7:
            colort = '\033[93m'
        if daydiff > 0:
            colort = '\033[91m'

        daydifffrom = (datetime.now() - f['data_from']).days
        if daydifffrom < 0:
            # feed only starts in the future...
            colorf = '\033[94m'

        print feedname
        print ('data from: '.ljust(17) + '%s%s' + '\033[0m') % (colorf, datetime.strftime(f['data_from'], "%d/%m/%Y"))
        print ('data until: '.ljust(17) + '%s%s' + '\033[0m') % (colort, datetime.strftime(f['data_to'], "%d/%m/%Y"))
        print 'url: '.ljust(17) + str(f['url'])
        if 'remote_date' in f and 'local_date' in f:
            print 'newer at url: '.ljust(17) + ('Yes' if f.get('has_newer_zip', False) else 'No') + ' (remote: ' +  datetime.strftime(f['remote_date'], "%d/%m/%Y") + ', local: ' + datetime.strftime(f['local_date'], "%d/%m/%Y") + ')'
        print 'has shapes: '.ljust(17) + ('Yes' if f['has_shapes'] else 'No')
        if f['postprocess']:
            print 'Postprocess cmd: '.ljust(17) + f['postprocess']

    def _print_feed(self, f):
        color = '\033[92m'
        daydiff = (datetime.now() - f['data_to']).days
        if daydiff > -7:
            color = '\033[93m'
        if daydiff > 0:
            if self.options['--active']:
                return
            color = '\033[91m'
        elif self.options['--notactive']:
            return

        daydifffrom = (datetime.now() - f['data_from']).days
        if daydifffrom < 0:
            # feed only starts in the future...
            color = '\033[94m'

        print color + f['name'].ljust(30) + '\t' + datetime.strftime(f['data_from'], "%d/%m/%Y").ljust(10) + '\t' + datetime.strftime(f['data_to'], "%d/%m/%Y").ljust(15) + '\t' + ('s' if f['has_shapes'] else ' ') + '\t' + ('u' if f['url'] else ' ') + '\t' + ('r' if f.get('has_newer_zip', False) else ' ') + '\033[0m'

    def _loadfeeds(self, name = None):
        ret = []
        for path in self._getfeeds(self.options['--base-folder'], 2):
            if not name or name == os.path.basename(os.path.abspath(path)):
                yield self._loadfeed(path)

    def _loadfeed(self, path):
        try:
            if not self._is_gtfs(path):
                raise Exception('Feed not found.')

            # read date validity
            feed = {}
            feed['name'] = relpath(os.path.abspath(path), self.options['--base-folder'])
            feed['data_from'] = datetime.strptime(self._parse_calendars(path)['from_date'], "%Y%m%d")
            feed['data_to'] = datetime.strptime(self._parse_calendars(path)['to_date'], "%Y%m%d")
            feed['url'] = self._parse_feed_url(path)
            feed['fullpath'] = path
            feed['has_shapes'] = os.path.isfile(os.path.join(path, 'shapes.txt'))
            feed['postprocess'] = self._parse_postprocess_cmd(path)

            if self.options['--checkremotedate']:
                feed['has_newer_zip'], feed['remote_date'], feed['local_date'] = self._check_for_newer_zip(path, feed['url'])

            self._write_span_cache(feed)
            return feed
        except Exception, err:
            print 'Error while parsing ' + str(path)
            print err

    def _check_for_newer_zip(self, path, url):
        if not url: return None, None, None
        u = urlparse(url)
        conn = httplib.HTTPConnection(u.netloc)
        conn.request("HEAD", u.path)
        res = conn.getresponse()
        if res.status == 200:
            mod = dict(res.getheaders()).get('last-modified', None)
            if not mod: return None, None, None
            servertime = parser.parse(mod, ignoretz=True) # ignoretz to get non-offsetted timestamp
            # use age of trips.txt as indicator for global feed age
            localtime = datetime.fromtimestamp(os.path.getmtime(os.path.join(path, 'trips.txt')))
            return localtime < servertime, servertime, localtime

    def _parse_feed_url(self, path):
        if os.path.isfile(os.path.join(path, 'feed_url.txt')):
            with open(os.path.join(path, 'feed_url.txt'), 'r') as feed_url_f:
                return feed_url_f.readline()

        return None

    def _parse_postprocess_cmd(self, path):
        if os.path.isfile(os.path.join(path, 'postprocess.txt')):
            with open(os.path.join(path, 'postprocess.txt'), 'r') as postprocess_f:
                return postprocess_f.readline()

        return None

    def _store_feed_url(self, url, path):
        print 'Setting feed url for ' + path + ' to ' + url
        with open(os.path.join(path, 'feed_url.txt'), 'w') as feed_url_f:
            feed_url_f.write(url)

    def _store_postprocess_cmd(self, feedname, cmd):
        feed = self._get_feed_by_name(feedname)
        if not feed:
            sys.stderr.write('No feed named "%s" found...\n' % str(feedname))
            return
        if not cmd:
            cmd = raw_input('Enter cmd: ')
        print 'Storing postprocessing cmd for %s' % feedname
        with open(os.path.join(feedname, 'postprocess.txt'), 'w') as postprocess_f:
            postprocess_f.write(cmd)

    def _postprocess(self, path):
        cmd = self._parse_postprocess_cmd(path)
        if cmd:
            cmd = cmd.replace('{feed_path}', path)
            print '==========================='
            print 'Running postprocess command'
            print '==========================='
            print cmd
            if not os.system(cmd):
                return True
            else:
                return False
        else:
            return True

    def _parse_calendars(self, path):
        # first, check if we have cache information
        cache = self._read_span_cache(path)
        if cache:
            return cache

        from_date = sys.maxint
        to_date = 0

        # use csv.reader, not DictReader and store field indexes from header
        # because it is _much_ faster
        if os.path.isfile(os.path.join(path, 'calendar.txt')):
            with open(os.path.join(path, 'calendar.txt'), 'r') as calendar:
                reader = iter(csv.reader(calendar))
                header = next(reader)
                monf = header.index('monday')
                tuef = header.index('tuesday')
                wedf = header.index('wednesday')
                thuf = header.index('thursday')
                frif = header.index('friday')
                satf = header.index('saturday')
                sunf = header.index('sunday')
                startf = header.index('start_date')
                endf = header.index('end_date')
                # store length of header
                headerl = len(header)

                for row in reader:
                    # only count services that are active at at least 1 day
                    if (len(row) != headerl):
                        continue
                    if int(monf) or int(tuef) or int(wedf) or int(thuf) or int(frif) or int(satf) or int(sunf):
                        if int(row[startf]) < int(from_date):
                            from_date = row[startf]

                        if int(row[endf]) > int(to_date):
                            to_date = row[endf]

        if os.path.isfile(os.path.join(path, 'calendar_dates.txt')):
            with open(os.path.join(path, 'calendar_dates.txt'), 'r') as calendar:
                reader = iter(csv.reader(calendar))
                header = next(reader)
                excf = header.index('exception_type')
                datef = header.index('date')
                # store length of header
                headerl = len(header)
                for row in reader:
                    if (len(row) != headerl):
                        continue
                    if int(row[excf]) == 1:
                        if int(row[datef]) < int(from_date):
                            from_date = row[datef]

                        if int(row[datef]) > int(to_date):
                            to_date = row[datef]

        return {'from_date' : str(from_date).strip(), 'to_date' : str(to_date).strip()}


    def _getfeeds(self, root, maxlevel=0, ret = []):
        """ Returns all folders below root (not deeper than maxlevel)
            that contain GTFS files
        """
        isgtfs = 0
        for item in os.listdir(root):
            if os.path.isfile(os.path.join(root, item)):
                if item in GTFS_REQ_FILES:
                    isgtfs += 1
                if isgtfs == len(GTFS_REQ_FILES):
                    ret.append(root)
                    isgtfs = 0

            elif maxlevel > 0 and os.path.isdir(os.path.join(root, item)):
                self._getfeeds(os.path.join(root, item), maxlevel - 1, ret)

        return ret

    def _is_gtfs(self, path):
        path = os.path.abspath(path)
        isgtfs = 0
        if not os.path.exists(path): return False
        for item in os.listdir(path):
                if item in GTFS_REQ_FILES:
                    isgtfs += 1
                if isgtfs == len(GTFS_REQ_FILES):
                    return True

        return False

    def _write_span_cache(self, feed):
        path = feed['fullpath']
        from_d = datetime.strftime(feed['data_from'], "%Y%m%d")
        to_d = datetime.strftime(feed['data_to'], "%Y%m%d")
        with open(os.path.join(path, '.gtfs_span_cache'), 'w') as cache:
            cache.write(str(from_d) + ',' + str(to_d))

    def _read_span_cache(self, path):
        if os.path.isfile(os.path.join(path, '.gtfs_span_cache')):
            with open(os.path.join(path, '.gtfs_span_cache'), 'r') as cache:
                line = cache.readline()
                parts = line.split(',')
                if len(parts) == 2:
                    return {'from_date' : str(parts[0]), 'to_date' : str(parts[1])}
        return None

    def _generate_caches(self):
        self._clear_caches()
        for f in self._loadfeeds():
            print 'Generated cache for ' + f['name']

    def _clear_caches(self):
        print 'Clearing caches...'
        for path in self._getfeeds(self.options['--base-folder'], 2):
            self._clear_cache(path)

    def _clear_cache(self, path):
        cachepath = os.path.abspath(os.path.join(path, '.gtfs_span_cache'))
        if os.path.isfile(cachepath):
            os.remove(cachepath)

def main(options=None):
    theman = GTFSManager(options)

if __name__ == '__main__':
    from docopt import docopt

    arguments = docopt(__doc__, version='geOps GTFS Manager 0.2')
    try:
        main(options=arguments)
    except KeyboardInterrupt:
        print "\nCancelled by user."
    exit(0)