import dominate
import core
from core import config
from cherrypy import expose
from dominate.tags import *
from header import Header


class AddMovie():
    @expose
    def index(self):
        theme=str(core.CONFIG['Server']['csstheme'])
        doc = dominate.document(title='Watcher')

        with doc.head:
            base(href="/static/")

            link(rel='stylesheet', href='css/'+theme+'/style.css')
            link(rel='stylesheet', href='css/'+theme+'/add_movie.css')
            link(rel='stylesheet', href='css/'+theme+'/movie_info_popup.css')
            link(rel='stylesheet', href='//fonts.googleapis.com/css?family=Raleway')
            link(rel='stylesheet', href='font-awesome/css/font-awesome.css')
            link(rel='stylesheet', href='js/sweetalert-master/dist/'+theme+'/sweetalert.css')

            script(type='text/javascript', src='https://ajax.googleapis.com/ajax/libs/jquery/3.1.0/jquery.min.js')
            script(src="https://ajax.googleapis.com/ajax/libs/jqueryui/1.12.0/jquery-ui.min.js")
            script(type='text/javascript', src='js/sweetalert-master/dist/sweetalert-dev.js')
            script(type='text/javascript', src='js/add_movie/main.js')

        with doc:
            Header.insert_header(current="add_movie")
            with div(id='search_box'):
                input(id='search_input', type="text", placeholder="Search...", name="search_term")
                with button(id="search_button"):
                    i(cls='fa fa-search')

            div(id='thinker')

            with div(id="database_results"):
                ul(id='movie_list')

            div(id='overlay')

            div(id='info_pop_up')

        return doc.render()
