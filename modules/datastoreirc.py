import locale
COMMANDS = frozenset(('dbhits',))

def init():
    add_hook('privmsg', privmsg)

def privmsg(irc, origin, args):
    irc_helpers = m('irc_helpers')
    target, command, args = irc_helpers.parse(args)
    if command not in COMMANDS:
        return
    if not m('security').check_action_permissible(origin, command):
        return
    
    if command == 'dbhits':
        irc_helpers.message(irc, target, "The datastore has been hit ~B%s~B times since the datastore module was loaded." % locale.format('%i', m('datastore').query_count, True))