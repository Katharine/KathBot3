import locale

def init():
    add_hook('message', message)

def message(irc, channel, origin, command, args):
    if command == 'dbhits':
        m('irc_helpers').message(irc, channel, "The datastore has been hit ~B%s~B times since the datastore module was loaded." % locale.format('%i', m('datastore').query_count, True))