def message(irc, target, msg):
    irc.raw("PRIVMSG %s :%s" % (target, msg))

def notice(irc, target, msg):
    irc.raw("NOTICE %s: %s" % (target, msg))

def join(irc, channel):
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