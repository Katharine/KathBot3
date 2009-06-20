import logging

def init():
    add_hook('ping', ping)
    add_hook('error', server_disconnect)

def ping(irc, origin, args):
    irc.raw("PONG :%s" % args[0])
    
def server_disconnect(irc, origin, args):
    irc.disconnect(forced=True)
    logging.error("Disconnected from %s" % irc.network.server)