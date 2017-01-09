import datetime
import logging

import cherrypy
import core
from core.notification import Notification

from core import searcher, version
from core.rss import imdb
from core.plugins import taskscheduler

logging = logging.getLogger(__name__)


class Scheduler(object):

    def __init__(self):
        # create scheduler plugin
        self.plugin = taskscheduler.SchedulerPlugin(cherrypy.engine)


# create classes for each scheduled task
class AutoSearch(object):
    @staticmethod
    def create():
        search = searcher.Searcher()
        interval = int(core.CONFIG['Search']['searchfrequency']) * 3600

        hr = int(core.CONFIG['Search']['searchtimehr'])
        min = int(core.CONFIG['Search']['searchtimemin'])

        task_search = taskscheduler.ScheduledTask(hr, min, interval,
                                                  search.auto_search_and_grab,
                                                  auto_start=True)

        # update core.NEXT_SEARCH
        delay = task_search.task.delay
        now = datetime.datetime.today().replace(second=0, microsecond=0)
        core.NEXT_SEARCH = now + datetime.timedelta(0, delay)


class AutoUpdateCheck(object):

    @staticmethod
    def create():

        interval = int(core.CONFIG['Server']['checkupdatefrequency']) * 3600

        now = datetime.datetime.today()
        hr = now.hour
        min = now.minute
        if now.second > 30:
            min += 1

        if core.CONFIG['Server']['checkupdates'] == u'true':
            auto_start = True
        else:
            auto_start = False

        taskscheduler.ScheduledTask(hr, min, interval, AutoUpdateCheck.update_check,
                                    auto_start=auto_start)
        return

    @staticmethod
    def update_check():
        ''' Checks for any available updates

        Returns dict from core.version.Version.manager.update_check():
            {'status': 'error', 'error': <error> }
            {'status': 'behind', 'behind_count': #, 'local_hash': 'abcdefg', 'new_hash': 'bcdefgh'}
            {'status': 'current'}
        '''

        ver = version.Version()

        data = ver.manager.update_check()
        # if data['status'] == u'current', nothing to do.

        if data['status'] == u'error':
            notif = {'type': 'error',
                     'title': 'Error Checking for Updates',
                     'body': data['error'],
                     'params': '{closeButton: true, timeOut: 0, extendedTimeOut: 0}'
                     }
            Notification.add(notif)

        elif data['status'] == u'behind':
            if data['behind_count'] == 1:
                title = u'1 Update Available'
            else:
                title = u'{} Updates Available'.format(data['behind_count'])

            compare = u'{}/compare/{}...{}'.format(core.GIT_URL, data['new_hash'], data['local_hash'])

            notif = {'type': 'update',
                     'title': title,
                     'body': 'Click <a href="update_now"><u>here</u></a> to update now.'
                             '<br/> Click <a href="'+compare+'"><u>here</u></a> to view changes.',
                     'params': {'closeButton': 'true',
                                'timeOut': 0,
                                'extendedTimeOut': 0,
                                'tapToDismiss': 0}
                     }

            Notification.add(notif)

        return data


class AutoUpdateInstall(object):

    @staticmethod
    def create():
        interval = 24 * 3600

        hr = int(core.CONFIG['Server']['installupdatehr'])
        min = int(core.CONFIG['Server']['installupdatemin'])

        if core.CONFIG['Server']['installupdates'] == u'true':
            auto_start = True
        else:
            auto_start = False

        taskscheduler.ScheduledTask(hr, min, interval, AutoUpdateInstall.install,
                                    auto_start=auto_start)
        return

    @staticmethod
    def install():
        ver = version.Version()

        if not core.UPDATE_STATUS or core.UPDATE_STATUS['status'] != u'behind':
            return

        logging.info(u'Running automatic updater.')

        logging.info(u'Currently {} commits behind. Updating to {}.'.format(
                     core.UPDATE_STATUS['behind_count'], core.UPDATE_STATUS['new_hash']))

        core.UPDATING = True

        logging.info(u'Executing update.')
        update = ver.manager.execute_update()
        core.UPDATING = False

        if not update:
            logging.error(u'Update failed.')

        logging.info(u'Update successful, restarting.')
        cherrypy.engine.restart()
        return


class ImdbRssSync(object):

    @staticmethod
    def create():
        interval = 6 * 3600
        now = datetime.datetime.now()

        hr = now.hour
        min = now.minute + 5

        if core.CONFIG['Search']['imdbsync'] == u'true':
            auto_start = True
        else:
            auto_start = False

        taskscheduler.ScheduledTask(hr, min, interval, ImdbRssSync.sync_rss,
                                    auto_start=auto_start)
        return

    @staticmethod
    def sync_rss():
        logging.info(u'Running automatic IMDB rss sync.')
        rss_url = core.CONFIG['Search']['imdbrss']

        imdb_rss = imdb.ImdbRss()

        imdb_rss.get_rss(rss_url)
        return
