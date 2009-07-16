import logging
from networks import networks

handler = None
    
class IRCHandler(logging.Handler):
    def __init__(self, *args, **kwds):
        logging.Handler.__init__(self, *args, **kwds)
        self.setFormatter(logging.Formatter('~B[%(levelname)s]~B %(name)s: %(message)s'))
        
    def emit(self, record):
        for network in networks:
            irc = networks[network]
            if not irc.connected:
                continue
            try:
                lines = self.format(record).split("\n")
                for line in lines:
                    m('irc_helpers').message(irc, irc.network.primary_channel, line)
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