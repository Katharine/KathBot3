from __future__ import with_statement
import socket
import logging
import threading
import modules

class ConnectionNotReady(Exception): pass

class IRC(threading.Thread):
    network = None
    socket = None
    connected = False
    writelock = None
    nick = ''

    def __init__(self, network):
        if not isinstance(network, Network):
            raise TypeError
        self.network = network
        self.writelock = threading.Lock()
        threading.Thread.__init__(self, name=network.name)
        
    def run(self):
        logging.info("Connecting to %s:%s..." % (self.network.server, self.network.port))
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.socket.connect((self.network.server, self.network.port))
        except socket.error, message:
            logging.error("Couldn't connect: %s" % message)
            return
        logging.info("Connected.")
        self.raw("USER %s 8 *: %s" % (self.network.ident, self.network.realname))
        self.nick = self.network.nicks[0]
        self.raw("NICK %s" % self.nick)
        self.connected = True
        self.mainloop()
        
    def raw(self, message):
        if not self.socket:
            raise ConnectionNotReady
        logging.debug("->%s\t%s" % (self.network, message))
        with self.writelock:
            self.socket.send(("%s\n" % message).encode('utf-8'))
        
    def disconnected(self):
        modules.call_hook('disconnected')
        logging.warn("Disconnected from %s." % self.network)
        
    def disconnect(self, forced=False, reason=""):
        if not forced:
            self.raw("QUIT :%s" % reason)
        
        try:
            self.socket.shutdown(socket.SHUT_RDWR)
            self.socket.close()
        except socket.error:
            pass
        
        self.connected = False
        
    def handle(self, line):
        origin = None
        if line[0] == ':':
            hostmask, line = line[1:].split(' ', 1)
            parts = hostmask.split('!', 1)
            origin = User(nick=parts[0])
            if len(parts) > 1:
                origin.ident, origin.hostname = parts[1].split('@', 1)
        
        parts = line.split(' :', 1)
        args = parts[0].split(' ')
        if len(parts) > 1:
            args.append(parts[1])
        
        command = args.pop(0).lower()
        modules.call_hook(command, self, origin, args)
    
    def mainloop(self):
        buff = ""
        while True:
            data = 0
            try:
                data = self.socket.recv(512)
            except socket.error:
                pass
            # Disconnected
            if data == 0 or not self.connected:
                self.disconnected()
                return
            data = (buff + data).split("\n")
            buff = data.pop()
            for line in data:
                line = line.strip()
                try:
                    line = line.decode('utf-8')
                except UnicodeDecodeError, e:
                    logging.warn("Failed to decode incoming UTF-8: %s" % e)
                logging.debug("<-%s\t%s" % (self.network, line))
                self.handle(line)

class Network:
    server = ''
    port = 6667
    nicks = ()
    realname = ''
    ident = ''
    primary_channel = None
    name = ''
    
    def __init__(self, server='', port=6667, nicks=None, realname='', ident='', primary_channel=None, name=''):
        self.server = server
        self.port = port
        self.nicks = nicks
        self.realname = realname
        self.ident = ident
        self.primary_channel = primary_channel
        self.name = name
        
    def __str__(self):
        return self.name
    
class User:
    hostname = ''
    nick = ''
    ident = ''
    
    def __init__(self, host='', nick='', ident=''):
        self.hostname = host
        self.nick = nick
        self.ident = ident
        
    def __str__(self):
        return "%s!%s@%s" % (self.nick, self.ident, self.hostname)
