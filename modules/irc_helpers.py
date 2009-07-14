# encoding=utf-8
def format(msg):
    return msg.replace('~B', chr(2)).replace('~U', chr(31)).replace('~I', chr(22))

def message(irc, target, msg, fmt=True):
    if not isinstance(msg, basestring):
        msg = str(msg)
    if fmt:
        msg = format(msg)
    if msg.startswith("/me"):
        msg = "\x01ACTION %s\x01" % msg[4:]
    irc.raw("PRIVMSG %s :%s" % (target, msg))

def notice(irc, target, msg, fmt=True):
    if fmt:
        msg = format(msg)
    irc.raw("NOTICE %s :%s" % (target, msg))

def join(irc, channel, passkey=None):
    if passkey:
        irc.raw("JOIN %s %s" % (channel, passkey))
    else:
        irc.raw("JOIN %s" % channel)

def part(irc, channel, reason=""):
    irc.raw("PART %s :%s" % (channel, reason))
    
def parse(args):
    line = m('core').check_prefix(args[1])
    if not line:
        return None, None, None
    
    line = line.split(' ')
    command = line.pop(0)
    return args[0], command, line