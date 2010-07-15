# encoding: utf-8

def init():
    add_hook('message', message)

def message(irc, channel, origin, command, args):
    if command == "help":
        if len(args) == 0:
            m('irc_helpers').message(irc, channel, "This would link to the help page, if it existed yet.")
            return
        search = args[0]
        help = m('datastore').query("SELECT module, usage, description FROM help WHERE command = ?", search)
        if not help:
            m('irc_helpers').message(irc, channel, "%s does not exist." % search, tag="Help")
            return
        module, usage, description = help[0]
        try:
            m(module)
        except ModuleNotLoaded:
            m('irc_helpers').message(irc, channel, "%s will not work, as the %s module is not loaded." % (search, module), tag='Help')
            return
        
        try:
            access = m('security').get_command_access(search)
        except ModuleNotLoaded:
            access = 1
        
        if search[0:4] == "kb3:":
            prefix = "KB3 "
        else:
            try:
                prefix = m('core').get_primary_prefix()
            except ModuleNotLoaded:
                prefix = ''
        
        m('irc_helpers').message(irc, channel, "~B~U%s%s~U~B" % (prefix, usage), tag="Help")
        m('irc_helpers').message(irc, channel, u"Module: ~B%s~B · Required access: ~BLevel %s~B" % (module, access), tag="Help")
        m('irc_helpers').message(irc, channel, description, tag="Help")
