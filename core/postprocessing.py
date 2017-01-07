import datetime
import json
import logging
import os
import re
import shutil
import urllib2

import cherrypy
import core
import PTN
from core import snatcher, sqldb, updatestatus

logging = logging.getLogger(__name__)


class Postprocessing(object):
    exposed = True

    def __init__(self):
        self.sql = sqldb.SQL()
        self.snatcher = snatcher.Snatcher()
        self.update = updatestatus.Status()

    def null(*args, **kwargs): return

    @cherrypy.expose
    def GET(self, **data):
        ''' Handles post-processing requests.
        :kwparam **params: keyword params send through GET request URL

        required kw params:
            apikey: str Watcher api key
            mode: str post-processing mode (complete, failed)
            guid: str download link of file. Can be url or magnet link.
            path: str path to downloaded files. Can be single file or dir

        optional kw params:
            imdbid: str imdb identification number (tt123456)
            downloadid: str id number from downloader

        Returns str json.dumps(dict) to post-process reqesting application.
        '''

        logging.info('#################################')
        logging.info('Post-processing request received.')
        logging.info('#################################')

        # check for required keys
        required_keys = ['apikey', 'mode', 'guid', 'path']

        for key in required_keys:
            if key not in data:
                logging.info('Missing key {}'.format(key))
                return json.dumps({'response': 'false',
                                  'error': 'missing key: {}'.format(key)})

        # check if api key is correct
        if data['apikey'] != core.CONFIG['Server']['apikey']:
            logging.info('Incorrect API key.'.format(key))
            return json.dumps({'response': 'false',
                              'error': 'incorrect api key'})

        # check if mode is valid
        if data['mode'] not in ['failed', 'complete']:
            logging.info('Invalid mode value: {}.'.format(data['mode']))
            return json.dumps({'response': 'false',
                              'error': 'invalid mode value'})

        # get the actual movie file name
        data['filename'] = self.get_filename(data['path'])

        logging.info('Parsing release name for information.')
        data.update(self.parse_filename(data['filename']))

        # Get possible local data or get OMDB data to merge with self.params.
        logging.info('Gathering release information.')
        data.update(self.get_movie_info(data))

        # remove any invalid characters
        for (k, v) in data.iteritems():
            # but we have to keep the path unmodified
            if k != 'path' and type(v) == str:
                data[k] = re.sub(r'[:"*?<>|]+', '', v)

        # At this point we have all of the information we're going to get.
        if data['mode'] == 'failed':
            logging.info('Post-processing as Failed.')
            # returns to url:
            response = json.dumps(self.failed(data), indent=2, sort_keys=True)
            logging.info(response)
        elif data['mode'] == 'complete':
            logging.info('Post-processing as Complete.')
            # returns to url:
            response = json.dumps(self.complete(data), indent=2, sort_keys=True)
            logging.info(response)
        else:
            logging.info('Invalid mode value: {}.'.format(data['mode']))
            return json.dumps({'response': 'false',
                               'error': 'invalid mode value'})

        logging.info('#################################')
        logging.info('Post-processing complete.')
        logging.info(response)
        logging.info('#################################')

        return response

    def get_filename(self, path):
        ''' Looks for the filename of the movie being processed
        :param path: str url-passed path to download dir

        If path is a file, just returns path.
        If path is a directory, finds the largest file in that dir.

        Returns str absolute path /home/user/filename.ext
        '''

        logging.info('Finding movie file name.')
        if os.path.isfile(path):
            return path
        else:
            # Find the biggest file in the dir. Assume that this is the movie.
            try:
                files = os.listdir(path)
            except Exception, e: # noqa
                logging.error('Path not found in filesystem.',
                              exc_info=True)
                return ''

            files = []
            for root, dirs, filenames in os.walk(path):
                for file in filenames:
                    files.append(os.path.join(root, file))

            if files == []:
                return ''

            biggestfile = None
            s = 0
            for file in files:
                size = os.path.getsize(file)
                if size > s:
                    biggestfile = file
                    s = size

            logging.info('Post-processing file {}.'.format(biggestfile))

            return biggestfile

    def parse_filename(self, filepath):
        ''' Parses filename for release information
        :param filename: str name of movie file

        PTN only returns information it finds, so we start with a blank dict
            of keys that we NEED to have, then update it with PTN's data. This
            way when we rename the file it will insert a blank string instead of
            throwing a missing key exception.

        Might eventually replace this with Hachoir-metadata

        Returns dict of parsed data
        '''

        # This is our base dict. Contains all neccesary keys, though they can all be empty if not found.
        data = {
            'title': '',
            'year': '',
            'resolution': '',
            'releasegroup': '',
            'audiocodec': '',
            'videocodec': '',
            'source': '',
            'imdbid': ''
            }

        titledata = PTN.parse(os.path.basename(filepath))
        # this key is useless
        if 'excess' in titledata:
            titledata.pop('excess')

        if len(titledata) <= 2:
            logging.info('Parsing filename doesn\'t look accurate. Parsing parent folder name')
            path_list = filepath.split(os.sep)
            if len(path_list) >=2:
                titledata = PTN.parse(path_list[-2])
            else:
                logging.info('Unable to parse file name or folder.')
                return data

        # this key is useless
        if 'excess' in titledata:
            titledata.pop('excess')

        # Make sure this matches our key names
        if 'codec' in titledata:
            titledata['videocodec'] = titledata.pop('codec')
        if 'audio' in titledata:
            titledata['audiocodec'] = titledata.pop('audio')
        if 'quality' in titledata:
            titledata['source'] = titledata.pop('quality')
        if 'group' in titledata:
            titledata['releasegroup'] = titledata.pop('group')
        data.update(titledata)

        return data

    def get_movie_info(self, data):
        ''' Gets score, imdbid, and other information to help process
        :param data: dict url-passed params with any additional info

        Uses guid to look up local details.
        If that fails, uses downloadid.
        If that fails, uses title and year from  to search omdb for imdbid

        If everything fails returns empty dict {}

        Returns dict of any gathered information
        '''

        # try to get searchresult using guid first then downloadid
        logging.info('Searching local database for guid.')
        result = self.sql.get_single_search_result('guid', data['guid'])
        if not result:
            # try to get result from downloadid
            logging.info('Searching local database for downloadid.')
            result = self.sql.get_single_search_result('downloadid', data['downloadid'])
            if result:
                logging.info('Searchresult found by downloadid.')
                if result['guid'] != data['guid']:
                    logging.info('Guid for downloadid does not match local data. '
                                 'Adding guid2 to processing data.')
                    data['guid2'] = result['guid']
        else:
            logging.info('Searchresult found by guid.')

        # if we found it, get local movie info
        if result:
            logging.info('Searching local database by imdbid.')
            data = self.sql.get_movie_details('imdbid', result['imdbid'])
            if data:
                logging.info('Movie data found locally by imdbid.')
                data['finishedscore'] = result['score']
            else:
                logging.info('Unable to find movie in local db.')

        else:
            # Still no luck? Try to get the imdbid from OMDB
            logging.info('Unable to find local data for release. Searching OMDB.')

            title = data['title']
            year = data['year']

            logging.info(u'Searching omdb for {} {}'.format(title, year))
            search_string = u'http://www.omdbapi.com/?t={}&y={}&plot=short&r=json'.format(title, year).replace(' ', '+')

            request = urllib2.Request(search_string, headers={'User-Agent': 'Mozilla/5.0'})

            try:
                omdbdata = json.loads(urllib2.urlopen(request).read())
            except Exception, e: # noqa
                logging.error('Post-processing omdb request.', exc_info=True)
                return {}

            if omdbdata['Response'] == 'False':
                logging.info('Nothing found in OMDB.')
                return {}
            else:
                logging.info('Data found on OMDB.')

                # make the keys all lower case
                omdbdata_lower = dict((k.lower(), v) for (k, v) in omdbdata.iteritems())
                return omdbdata_lower

        if data:
            # remove unnecessary info
            del data['quality']
            del data['plot']

            repl = core.CONFIG['Postprocessing']['replace_illegal']

            for (k, v) in data.iteritems():
                # but we have to keep the path unmodified
                if type(v) == str:
                    data[k] = re.sub(r'[:"*?<>|]+', repl, v)

            return data
        else:
            return {}

    def failed(self, data):
        ''' Post-process failed downloads.
        :param data: dict of gathered data from downloader and localdb/omdb

        In SEARCHRESULTS marks guid as Bad
        In MARKEDRESULTS:
            Creates or updates entry for guid and optional guid2 with status=Bad
        Updates MOVIES status

        If Clean Up is enabled will delete path and contents.
        If Auto Grab is enabled will grab next best release.

        Returns dict of post-processing results
        '''

        # dict we will json.dump and send back to downloader
        result = {}
        result['status'] = 'finished'
        result['data'] = data
        result['tasks'] = {}

        # mark guid in both results tables
        logging.info('Marking guid as Bad.')
        guid_result = {'url': data['guid']}
        if self.update.searchresults(data['guid'], 'Bad'):
            guid_result['update_SEARCHRESULTS'] = 'true'
        else:
            guid_result['update_SEARCHRESULTS'] = 'false'

        if self.update.markedresults(data['guid'], data['imdbid'], 'Bad'):
            guid_result['update_MARKEDRESULTS'] = 'true'
        else:
            guid_result['update_MARKEDRESULTS'] = 'false'

        # create result entry for guid
        result['tasks']['guid'] = guid_result

        # if we have a guid2, do it all again
        if 'guid2' in data.keys():
            logging.info('Marking guid2 as Bad.')
            guid2_result = {'url': data['guid2']}
            if self.update.searchresults(data['guid2'], 'Bad'):
                guid2_result['update SEARCHRESULTS'] = 'true'
            else:
                guid2_result['update SEARCHRESULTS'] = 'false'

            if self.update.markedresults(data['guid2'], data['imdbid'], 'Bad'):
                guid2_result['update_MARKEDRESULTS'] = 'true'
            else:
                guid2_result['update_MARKEDRESULTS'] = 'false'
            # create result entry for guid2
            result['tasks']['guid2'] = guid2_result

        # set movie status
        if data['imdbid']:
            logging.info('Setting MOVIE status.')
            r = str(self.update.movie_status(data['imdbid'])).lower()
        else:
            logging.info('Imdbid not supplied or found, unable to update Movie status.')
            r = 'false'
        result['tasks']['update_movie_status'] = r

        # delete failed files
        if core.CONFIG['Postprocessing']['cleanupfailed'] == 'true':
            result['tasks']['cleanup'] = {'enabled': 'true', 'path': data['path']}

            logging.info('Deleting leftover files from failed download.')
            if self.cleanup(data['path']) is True:
                result['tasks']['cleanup']['response'] = 'true'
            else:
                result['tasks']['cleanup']['response'] = 'false'
        else:
            result['tasks']['cleanup'] = {'enabled': 'false'}

        # grab the next best release
        if core.CONFIG['Search']['autograb'] == 'true':
            result['tasks']['autograb'] = {'enabled': 'true'}
            if data['imdbid']:
                if self.snatcher.auto_grab(data['imdbid']):
                    r = 'true'
                else:
                    r = 'false'
            else:
                r = 'false'
            result['tasks']['autograb']['response'] = r
        else:
            result['tasks']['autograb'] = {'enabled': 'false'}

        # all done!
        result['status'] = 'finished'
        return result

    def complete(self, data):
        '''
        :param data: str guid of downloads
        :param downloadid: str watcher-generated downloadid
        :param path: str path to downloaded files.

        All params can be blank strings ie ""

        In SEARCHRESULTS marks guid as Finished
        In MARKEDRESULTS:
            Creates or updates entry for guid and optional guid with status=bad
        In MOVIES updates finishedscore and finisheddate
        Updates MOVIES status

        Checks to see if we found a movie file. If not, ends here.

        If Renamer is enabled, renames movie file according to core.CONFIG
        If Mover is enabled, moves file to location in core.CONFIG
        If Clean Up enabled, deletes path after Mover finishes.

        Returns dict of post-processing results
        '''

        # dict we will json.dump and send back to downloader
        result = {}
        result['status'] = 'incomplete'
        result['data'] = data
        result['data']['finisheddate'] = str(datetime.date.today())
        result['tasks'] = {}

        # mark guid in both results tables
        logging.info('Marking guid as Finished.')
        guid_result = {}
        if self.update.searchresults(data['guid'], 'Finished'):
            guid_result['update_SEARCHRESULTS'] = 'true'
        else:
            guid_result['update_SEARCHRESULTS'] = 'false'

        if self.update.markedresults(data['guid'], data['imdbid'], 'Finished'):
            guid_result['update_MARKEDRESULTS'] = 'true'
        else:
            guid_result['update_MARKEDRESULTS'] = 'false'

        # create result entry for guid
        result['tasks'][data['guid']] = guid_result

        # if we have a guid2, do it all again
        if 'guid2' in data.keys():
            logging.info('Marking guid2 as Finished.')
            guid2_result = {}
            if self.update.searchresults(data['guid2'], 'Finished'):
                guid2_result['update_SEARCHRESULTS'] = 'true'
            else:
                guid2_result['update_SEARCHRESULTS'] = 'false'

            if self.update.markedresults(data['guid2'], data['imdbid'],
                                         'Finished'):
                guid2_result['update_MARKEDRESULTS'] = 'true'
            else:
                guid2_result['update_MARKEDRESULTS'] = 'false'

            # create result entry for guid2
            result['tasks'][data['guid2']] = guid2_result

        # set movie status and add finished date
        if data['imdbid']:
            logging.info('Setting MOVIE status.')
            r = str(self.update.movie_status(data['imdbid'])).lower()
            self.sql.update('MOVIES', 'finisheddate', result['data']['finisheddate'],
                            imdbid=data['imdbid'])
        else:
            logging.info('Imdbid not supplied or found, unable to update Movie status.')
            r = 'false'
        result['tasks']['update_movie_status'] = r

        # renamer
        if core.CONFIG['Postprocessing']['renamerenabled'] == 'true':
            result['tasks']['renamer'] = {'enabled': 'true'}
            result['data']['orig_filename'] = result['data']['filename']
            response = self.renamer(data)
            if response is None:
                result['tasks']['renamer']['response'] = 'false'
            else:
                path = os.path.split(data['filename'])[0]
                data['filename'] = os.path.join(path, response)
                result['tasks']['renamer']['response'] = 'true'
        else:
            logging.info('Renamer disabled.')
            result['tasks']['mover'] = {'enabled': 'false'}

        # mover
        if core.CONFIG['Postprocessing']['moverenabled'] == 'true':
            result['tasks']['mover'] = {'enabled': 'true'}
            response = self.mover(data)
            if response is False:
                result['tasks']['mover']['response'] = 'false'
            else:
                data['new_file_location'] = response
                result['tasks']['mover']['response'] = 'true'
        else:
            logging.info('Mover disabled.')
            result['tasks']['mover'] = {'enabled': 'false'}

        # delete leftover dir, only if mover was enabled successful
        if core.CONFIG['Postprocessing']['cleanupenabled'] == 'true':
            result['tasks']['cleanup'] = {'enabled': 'true'}
            # fail if mover disabled or failed
            if core.CONFIG['Postprocessing']['moverenabled'] == 'false' or \
                    result['tasks']['mover']['response'] == 'false':
                result['tasks']['cleanup']['response'] = 'false'
            else:
                if self.cleanup(data['path']):
                    r = 'true'
                else:
                    r = 'false'
                result['tasks']['cleanup']['response'] = r
        else:
            result['tasks']['cleanup'] = {'enabled': 'false'}

        # all done!
        result['status'] = 'finished'
        return result

    def renamer(self, data):
        ''' Renames movie file based on renamerstring.
        :param data: dict of movie information.

        Renames movie file based on params in core.CONFIG

        Returns str new file name or None on failure
        '''

        renamer_string = core.CONFIG['Postprocessing']['renamerstring']

        # check to see if we have a valid renamerstring
        if re.match(r'{(.*?)}', renamer_string) is None:
            logging.info('Invalid renamer string {}'.format(renamer_string))
            return None

        # existing absolute path
        abs_path_old = data['filename']
        file_path = os.path.split(data['filename'])[0]

        # get the extension
        ext = os.path.splitext(abs_path_old)[1]

        # get the new file name
        new_name = renamer_string.format(**data)

        while '  ' in new_name:
            new_name = new_name.replace('  ', ' ')

        if not new_name or new_name == ' ':
            logging.info('New file name would be blank. Cancelling renamer.')
            return None

        while new_name[-1] == ' ':
            new_name = new_name[:-1]
        new_name = new_name + ext

        # remove invalid chars
        new_name = re.sub(r'[:"*?<>|]+', '', new_name)

        # new absolute path
        abs_path_new = os.path.join(file_path, new_name)

        logging.info(u'Renaming {} to {}'.format(os.path.basename(data['filename']), new_name))
        try:
            os.rename(abs_path_old, abs_path_new)
        except (SystemExit, KeyboardInterrupt):
            raise
        except Exception, e: # noqa
            logging.error('Renamer failed: Could not rename file.', exc_info=True)
            return None

        # return the new name so the mover knows what our file is
        return new_name

    def mover(self, data):
        '''Moves movie file to path constructed by moverstring
        :param data: dict of movie information.

        Moves file to location specified in core.CONFIG

        Returns str new file location or False on failure
        '''

        abs_path_old = data['filename']
        mover_path = core.CONFIG['Postprocessing']['moverpath']

        target_folder = mover_path.format(**data)

        # remove invalid chars and normalize
        target_folder = re.sub(r'["*?<>|]+', '', target_folder)
        target_folder = os.path.normpath(target_folder)

        logging.info(u'Moving {} to {}'.format(abs_path_old, target_folder))

        # if the new folder doesn't exist, make it
        try:
            if not os.path.exists(target_folder):
                os.mkdir(target_folder)
        except Exception, e:
            logging.error('Mover failed: Could not create folder.', exc_info=True)
            return False

        # move the file
        try:
            shutil.copystat = self.null
            shutil.move(abs_path_old, target_folder)
        except Exception, e: # noqa
            logging.error('Mover failed: Could not move file.', exc_info=True)
            return False

        return os.path.join(target_folder, os.path.basename(data['filename']))

    def cleanup(self, path):
        ''' Deletes specified path
        :param path: str of path to remover

        path can be file or dir

        Returns Bool on success/failure
        '''

        # if its a dir
        if os.path.isdir(path):
            try:
                shutil.rmtree(path)
                return True
            except Exception, e:
                logging.error('Could not delete path.', exc_info=True)
                return False
        elif os.path.isfile(path):
            # if its a file
            try:
                os.remove(path)
                return True
            except Exception, e: # noqa
                logging.error('Could not delete path.', exc_info=True)
                return False
        else:
            # if it is somehow neither
            return False
