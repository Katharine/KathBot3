def init():
    add_hook('privmsg', privmsg)

def privmsg(irc, origin, args):
    target = args[0]
    if target[0] != '#':
        target = origin.nick
    message = args[1]
    if message.startswith("\x01ACTION") and message.endswith("\x01"):
        stuff = message.split(' ')
        if len(stuff) > 2 and stuff[1] == 'pets' and stuff[2].lower().startswith(irc.nick.lower()):
            m('irc_helpers').message(irc, target, "Mew.")