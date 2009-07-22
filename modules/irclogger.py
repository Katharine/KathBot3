import logging
from networks import networks

handler = None
    
class IRCHandler(logging.Handler):
    def __init__(self, *args, **kwds):
        logging.Handler.__init__(self, *args, **kwds)
        self.setFormatter(logging.Formatter('%(levelname)s %(name)s: %(message)s'))
        
    def emit(self, record):
        for network in networks:
            irc = networks[network]
            if not irc.connected:
                continue
            try:
                line = self.format(record).split(' ', 1)
                m('irc_helpers').message(irc, irc.network.primary_channel, line[1], tag=line[0])
            except:
                pass

def init():
    global handler
    handler = IRCHandler(level=logging.INFO)
    logging.getLogger().addHandler(handler)
    logger.info("Added IRCHandler.")

def shutdown():
    global handler
    logging.getLogger().removeHandler(handler)
    handler = None
    logger.info("Removed IRCHandler.")