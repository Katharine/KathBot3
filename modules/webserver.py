# encoding=utf-8
import BaseHTTPServer
import SocketServer
import threading
import inspect
import os.path
import urllib2
import urlparse
import traceback
import mimetypes
import platform
import socket
from cgi import parse_qs

web_handlers = {}

PORT_NUMBER = 8765

class FileNotFound(Exception): pass

class KBHTTPServer(BaseHTTPServer.HTTPServer, SocketServer.ThreadingMixIn):
    def shutdown(self):
        try:
            self.socket.shutdown()
        except:
            logger.warning("Couldn't shut down socket.")
        try:
            self.socket.close()
        except:
            pass

class KBHTTPHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    server_version = 'KathBot/3'
    protocol_version = 'HTTP/1.0'
    
    def send_output(self, output, discard_body=False, content_type='text/html; charset=utf-8', content_encoding=None, encoded=False):
        if content_type.startswith('text/') and not encoded:
            output = output.encode('utf-8')
        self.send_response(200)
        self.send_header("Content-Length", str(len(output)))
        self.send_header("Content-Type", content_type)
        if content_encoding is not None:
            self.send_header("Content-Encoding", content_encoding)
        self.end_headers()
        if not discard_body:
            self.wfile.write(output)
    
    def get_postdata(self):
        try:
            return self._postdata
        except AttributeError:
            pass
        length = int(self.headers['content-length'])
        self._postdata = urlparse.parse_qs(self.rfile.read(length), keep_blank_values=True)
        return self._postdata


    def do_something(self, method, discard_body=False):
        parts = urlparse.urlparse(self.path)
        self.path = parts[2]
        self.query = parse_qs(parts[4])
        if self.path == '/':
            self.send_output(generate_index_page(self), discard_body)
        elif self.path.startswith('/static/'):
            if method == 'POST':
                self.send_error(405)
            else:
                try:
                    path = 'data/web/' + self.path.replace('..', '')[8:]
                    f = open(path, 'rb')
                    content = f.read()
                    f.close()
                    content_type, content_encoding = mimetypes.guess_type(path, strict=False)
                    if content_type is None:
                        content_type = 'application/octet-stream'
                    self.send_output(content, content_type=content_type, content_encoding=content_encoding, encoded=True)
                except IOError:
                    self.send_error(404)
        else:
            requested_module = self.path.split('/')[1]
            if requested_module in web_handlers:
                if method in web_handlers[requested_module]:
                    try:
                        output = web_handlers[requested_module][method](self)
                        if output is not None:
                            self.send_output(output, discard_body)
                    except FileNotFound:
                        self.send_error(404)
                    except Exception, message:
                        logger.error(traceback.format_exc())
                        self.send_error(500, str(message))
                else:
                    self.send_error(405)
            else:
                self.send_error(404)
    
    def do_GET(self):
        self.do_something('GET')
    
    def do_HEAD(self):
        self.do_something('GET', discard_body=True)
    
    def do_POST(self):
        self.do_something('POST')

class WebServer(threading.Thread):
    server = None
    running = True
    
    def __init__(self):
        threading.Thread.__init__(self, name='httpd')
        self.setDaemon(True)
        
        self.server = KBHTTPServer(('', PORT_NUMBER), KBHTTPHandler)
        self.start()
    
    def run(self):
        while self.running:
            try:
                self.server.handle_request()
            except:
                pass
        self.server.shutdown()
    
    def shutdown(self):
        self.running = False

server = None

def init():
    global server
    server = WebServer()
    add_dyn_tag()
    add_hook('loaded', loaded)

def add_dyn_tag():
    try:
        m('dynamic').add_tag('localhttp', tag_localhttp)
    except ModuleNotLoaded:
        pass

def loaded(module):
    if module == 'dynamic':
        add_dyn_tag()

def tag_localhttp(node, context):
    return get_root_address()

def shutdown():
    server.shutdown()
    # This hack lets the server thread *actually* terminate.
    try:
        f = urllib2.urlopen('http://127.0.0.1:%s/' % PORT_NUMBER, None, 2)
        f.read(1)
        f.close()
    except:
        pass

def add_handler(method, handler):
    module = get_calling_module()
    if not module in web_handlers:
        web_handlers[module] = {}
    
    web_handlers[module][method.upper()] = handler
    logger.debug("Added %s method for %s." % (method, module))

def remove_handlers():
    module = get_calling_module()
    if module in web_handlers:
        del web_handlers[module]

def get_root_address(cached=[]):
    if not cached:
        cached.append('http://%s:%s/' % (socket.gethostbyaddr(socket.gethostname())[0], PORT_NUMBER))
    return cached[0]

def generate_index_page(request):
    return 'This is the index page.'

# Note: This function *must* be called by the function called by the other module.
def get_calling_module():
    record = inspect.stack()[2][1]
    filename = os.path.split(record)
    if filename[1].startswith('__init__.py'):
        filename = os.path.split(filename[0])
    
    module = filename[1].split('.')[0]
    
    return module