def message(irc, target, msg):
    irc.raw("PRIVMSG %s :%s" % (target, msg))

def notice(irc, target, msg):
    irc.raw("NOTICE %s: %s" % (target, msg))

def join(irc, channel):
    irc.raw("JOIN %s" % channel)

def part(irc, channel, reason=""):
    irc.raw("PART %s :%s" % (channel, reason))