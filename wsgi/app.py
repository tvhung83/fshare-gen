import os
from bottle import route, default_app, request, response, get, abort, redirect, view, TEMPLATE_PATH
from json import dumps
from fshare_client import FshareClient

# This must be added in order to do correct path lookups for the views
TEMPLATE_PATH.append(os.path.join(os.environ['OPENSHIFT_REPO_DIR'], 'wsgi/views/'))

application = default_app()
application.config.load_config(os.path.join(os.environ['OPENSHIFT_REPO_DIR'], 'wsgi/conf/app.conf'))
client = FshareClient()

@get('/')
@view('index.html')
def index():
    return 

@route('/', method=['OPTIONS', 'POST'])
def process():
    response.content_type = 'application/json'
    if request.method == 'OPTIONS':
        return {}
    else:
        results = []    # premium link list to return
        if client.login(application.config.get('account.email'), application.config.get('account.password')):
            for file in request.json:
                results.append(client.process(file))
        else:
            results.append('Login failed!')
        return dumps(results)

@get('/file/<file_id:re:[a-zA-Z0-9]+/?>')
def single_file(file_id):
    if client.login(application.config.get('account.email'), application.config.get('account.password')):
        result = client.process('https://www.fshare.vn/file/' + file_id)
        if result.startswith('http'):
            redirect(result, 302)
        else:
            abort(500, result)
    else:
        abort(401, 'Login failed!')

@get('/health')
def health():
    return "ok"

@application.hook('after_request')
def enable_cors():
    """
    You need to add some headers to each request.
    Don't use the wildcard '*' for Access-Control-Allow-Origin in production.
    """
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'PUT, GET, POST, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Origin, Accept, Content-Type, X-Requested-With, X-CSRF-Token'
