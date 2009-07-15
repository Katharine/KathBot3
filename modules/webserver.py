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

web_handlers = {}

class KBHTTPServer(BaseHTTPServer.HTTPServer, SocketServer.ThreadingMixIn):
    def shutdown(self):
        try:
            self.socket.close()
        except:
            pass

class KBHTTPHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    server_version = 'KathBot/3'
    protocol_version = 'HTTP/1.0'
    
    def send_output(self, output, discard_body=False, content_type='text/html; charset=utf-8', content_encoding=None):
        if content_type.startswith('text/'):
            output = output.encode('utf-8')
        self.send_response(200)
        self.send_header("Content-Length", str(len(output)))
        self.send_header("Content-Type", content_type)
        if content_encoding is not None:
            self.send_header("Content-Encoding", content_encoding)
        self.end_headers()
        if not discard_body:
            self.wfile.write(output)
    
    def do_something(self, method, discard_body=False):
        parts = urlparse.urlparse(self.path)
        self.path = parts[2]
        self.query = parts[4]
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
                    self.send_output(content, content_type=content_type, content_encoding=content_encoding)
                except IOError:
                    self.send_error(404)
        else:
            requested_module = self.path.split('/')[1]
            if requested_module in web_handlers:
                if method in web_handlers[requested_module]:
                    try:
                        output = web_handlers[requested_module][method](self)
                        if output is None:
                            self.send_error(404)
                        else:
                            self.send_output(output, discard_body)
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
        
        self.server = KBHTTPServer(('', 8765), KBHTTPHandler)
        self.start()
    
    def run(self):
        while self.running:
            try:
                self.server.handle_request()
            except:
                pass
    
    def shutdown(self):
        self.running = False
        self.server.shutdown()

server = None

def init():
    global server
    server = WebServer()

def shutdown():
    server.shutdown()
    try:
        f = urllib2.urlopen('http://127.0.0.1:8765/')
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