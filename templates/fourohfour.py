import dominate
import core
from cherrypy import expose
from dominate.tags import *
from head import Head
from footer import Footer

class FourOhFour():

    @staticmethod
    @expose
    def index():

        doc = dominate.document(title='Watcher')

        with doc.head:
            Head.insert()
            link(rel='stylesheet', href=core.URL_BASE + '/static/css/fourohfour.css')
            style

        with doc:
            with div(id='content'):
                with span(cls='msg'):
                    span('404')
                    br()
                    span('Page Not Found')
            Footer.insert_footer()
        return doc.render()
