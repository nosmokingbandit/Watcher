import json

import core
from core import sqldb
from core.helpers import Conversions
from dominate.tags import *


class MovieStatusPopup():

    def __init__(self):
        self.sql = sqldb.SQL()

    def html(self, imdbid):

        data = self.sql.get_movie_details('imdbid', imdbid)
        if data:
            poster_path = core.URL_BASE + '/static/images/posters/{}.jpg'.format(data['imdbid'])
            title = data['title']
            year = str(data['year'])

            url = data['url']

        container = div(id='container')
        with container:
            script(src=core.URL_BASE + '/static/js/status/movie_status_popup.js?v=01.26')
            if not data:
                span(u'Unable to get movie information from database. Check logs for more information.')
                return doc.render()

            with div(id='title'):
                with p():
                    with span(title, id='title', imdbid=imdbid):
                        span(year, id='title_year')
                    i(cls='fa fa-times', id='close')
                    i(cls='fa fa-trash', id='remove')
                    i(cls='fa fa-search', id='search_now', imdbid=data['imdbid'], title=data['title'])
            with div(id='media'):
                img(id='poster', src=poster_path)
                with div(id='search_results'):

                    self.result_list(imdbid)
                    div(id='results_thinker')

            with div(id='plot'):
                p(data['plot'])
            with div(id='additional_info'):
                if data['predb'] == 'found':
                    i(id='predb', cls='fa fa-check-circle', title='Verified releases found on predb.me')
                else:
                    i(id='predb', cls='fa fa-circle-o', title='No releases found on predb.me')
                span(u'Theatrical Release Date: {}'.format(data['release_date']))
                with a(href=url, target='_blank'):
                    span(u'Score: {}'.format(data['score']))
                span('Rated: {}'.format(data['rated']))

                with span('Quality profile: ', id='quality'):
                    with select(id='quality_profile', value=data['quality']):
                        options = core.CONFIG['Quality'].keys()
                        for opt in options:
                            item = option(opt, value=opt)
                            if opt == data['quality']:
                                item['selected'] = 'selected'

                    i(cls='fa fa-save', id='change_quality')

        return unicode(container)

    def result_list(self, imdbid):
        results = self.sql.get_search_results(imdbid)

        result_list = ul(id='result_list')
        with result_list:

            if not results:
                li(u'Nothing found yet.', cls='title bold')
                li(u'Next automatic search scheduled for {}'.format(Conversions.human_datetime(core.NEXT_SEARCH)), cls='title')
            else:
                for idx, res in enumerate(results):
                    kind = res['type']
                    info_link = res['info_link']
                    title = res['title']
                    guid = res['guid']
                    status = res['status']
                    size = Conversions.human_file_size(res['size'])
                    pubdate = res['pubdate']

                    # applied bottom border to all but last element
                    if idx == len(results) - 1:
                        bbord = u''
                    else:
                        bbord = u'bbord'
                    with li(cls='title bold'):
                        span(title, cls='name', title=title)
                        with span(cls='buttons'):
                            with a(href=info_link, target='_blank'):
                                i(cls='fa fa-info-circle')
                            i(cls='fa fa-download', id='manual_download', kind=kind, guid=guid)
                            i(cls='fa fa-ban', id='mark_bad', guid=guid)
                    with li(cls='data ' + bbord):
                        span(u'Type: ')
                        span(kind, cls='bold')
                        span(u' Status: ')
                        if status == 'Snatched':
                            span(status, cls='bold snatched')
                        elif status == 'Bad':
                            span(status, cls='bold bad')
                        elif status == 'Finished':
                            span(status, cls='bold finished')
                        else:
                            span(status, cls='bold')
                        span(u' Size: ')
                        span(size, cls='bold')
                        span(u' Score: ')
                        span(res['score'], cls='bold')
                        span(u' Source: ')
                        span(res['indexer'] or '', cls='bold')
                        if pubdate:
                            span(u' Published: ')
                            span(pubdate, cls='bold')

        return unicode(result_list)

# pylama:ignore=W0401
