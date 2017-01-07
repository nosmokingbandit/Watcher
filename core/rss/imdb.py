import core
from core import ajax, config, sqldb
from core.movieinfo import Omdb
from datetime import datetime
import json
import logging
import os
import urllib2
import xml.etree.cElementTree as ET

logging = logging.getLogger(__name__)


class ImdbRss(object):
    def __init__(self):
        self.config = config.Config()
        self.omdb = Omdb()
        self.sql = sqldb.SQL()
        self.ajax = ajax.Ajax()
        return

    def get_rss(self, rss_url):
        ''' Gets rss feed from imdb
        :param rss_url: str url to rss feed

        Gets raw rss, sends to self.parse_xml to turn into dict

        Returns True or None on success or failure (due to exception or empty movie list)
        '''

        logging.info('Syncing IMDB watchlist {}'.format(rss_url))

        request = urllib2.Request(rss_url, headers={'User-Agent': 'Mozilla/5.0'})

        try:
            results_xml = urllib2.urlopen(request).read()
            movies = self.parse_xml(results_xml)
            self.lastbuilddate = self.parse_build_date(results_xml)
        except (SystemExit, KeyboardInterrupt):
            raise
        except Exception, e: # noqa
            logging.error('IMDB rss request.', exc_info=True)
            return None

        if movies:
            logging.info('Found {} movies in watchlist.'.format(len(movies)))
            self.sync_new_movies(movies)
            logging.info('IMDB rss sync complete.')
            return True
        else:
            return None

    def parse_xml(self, feed):
        ''' Turns rss into python dict
        :param feed: str rss feed

        Returns list of dicts of movies in rss
        '''

        root = ET.fromstring(feed)

        # This so ugly, but some newznab sites don't output json.
        items = []
        for item in root.iter('item'):
            d = {}
            for i_c in item:
                d[i_c.tag] = i_c.text
            items.append(d)
        return items

    def parse_build_date(self, feed):
        ''' Gets lastBuildDate from imdb rss
        :param feed: str xml feed

        Last build date is used as a stopping point when iterating over the rss.
            There is no need to check movies twice since they will be removed anyway
            when checking if it already exists in the library.

        Returns str last build date from rss
        '''

        root = ET.fromstring(feed)

        for i in root.iter('lastBuildDate'):
            return i.text

    def sync_new_movies(self, movies):
        ''' Adds new movies from rss feed
        :params movies: list of dicts of movies

        Checks last sync time and pulls new imdbids from feed.

        Checks if movies are already in library and ignores.

        Executes ajax.add_wanted_movie() for each new imdbid

        Does not return
        '''
        data_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'imdb')

        date_format = '%a, %d %b %Y %H:%M:%S %Z'
        new_rss_movies = []

        if os.path.isfile(data_file):
            with open(data_file, 'r') as f:
                last_sync = f.read()
        else:
            last_sync = 'Sat, 01 Jan 2000 00:00:00 GMT'

        logging.info('Last synced this watchlist on {}+0800'.format(last_sync))

        last_sync = datetime.strptime(last_sync, date_format)

        for i in movies:
            pub_date = datetime.strptime(i['pubDate'], date_format)

            if last_sync >= pub_date:
                break

            title = i['title']
            link = i['link']
            imdbid = link.split('/')[-2]

            logging.info('Found new watchlist movie: {} {}'.format(title, imdbid))

            new_rss_movies.append(imdbid)

        # check if movies already exists

        existing_movies = [i['imdbid'] for i in self.sql.get_user_movies()]

        movies_to_add = [i for i in new_rss_movies if i not in existing_movies]

        # do quick-add procedure
        quality = {}
        quality['Quality'] = core.CONFIG['Quality']
        quality['Filters'] = core.CONFIG['Filters']
        for imdbid in movies_to_add:
            movie_info = self.omdb.movie_info(imdbid)
            if not movie_info:
                logging.info('{} not found on omdb. Cannot add.'.format(imdbid))
                continue
            # logging.info('Adding {}'.format(imdbid))
            movie_info['quality'] = json.dumps(quality)
            self.ajax.add_wanted_movie(json.dumps(movie_info))

        logging.info('Storing last synced date')
        with open(data_file, 'w') as f:
            f.write(self.lastbuilddate)
