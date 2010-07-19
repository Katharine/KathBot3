# encoding: utf-8
import modules
import re

def init():
    add_hook('message', message)
    add_hook('loaded', loaded)
    try:
        m('webserver').add_handler('GET', show_webpage)
    except ModuleNotLoaded:
        pass

def loaded(module):
    if module == 'webserver':
        m('webserver').add_handler('GET', show_webpage)

def message(irc, channel, origin, command, args):
    if command == "help":
        if len(args) == 0:
            try:
                m('irc_helpers').message(irc, channel, "%shelp" % m('webserver').get_root_address())
            except ModuleNotLoaded:
                m('irc_helpers').message(irc, channel, "The help page is currently unavailable.")
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

def show_webpage(request):
    parts = request.path[1:].split('/')
    if len(parts) < 3:
        if len(parts) == 2:
            mods = [parts[1]]
        else:
            mods = modules.mods.keys()
        
        help = m('datastore').query("SELECT command, module, usage, description FROM help WHERE module IN (%s) ORDER BY module, command" % ', '.join(["\"%s\"" % x for x in mods]))
        
        return render_index(mods, help)

def render_index(mods, help):
    mods.sort()
    output = """<!DOCTYPE html>
<html>
    <head>
        <title>Bot help</title>
        <link rel="stylesheet" href="/static/help/style.css" type="text/css">
    </head>
    <body>"""
    if len(mods) > 1:
        output += """
        <h1>Bot help</h1>
        <p id="command_stats">There are %s commands in %s modules</p>
        <h2>Modules</h2>
        <ul id="module_list">""" % (len(help), len(mods))
        for mod in mods:
            output += """
            <li><a href="/help/%s">%s</a></li>""" % (mod, mod)
        output += """
        </ul>"""
    else:
        module = mods[0]
        output += """
        <h1>%s help</h1>""" % module
        if len(help) == 0:
            output += """
        <p class="error">There are no commands in %s</p>""" % module
        for entry in help:
            command, module, usage, description = entry
            description = re.sub(r"((?:\[|&lt;)[a-z0-9]+?(?:\]|>))", r'<span class="arg">\1</span>', description.replace("<", "&lt;"))
            if command[0:4] == "kb3:":
                prefix = "KB3 "
            else:
                try:
                    prefix = m('core').get_primary_prefix()
                except ModuleNotLoaded:
                    prefix = ''
            output += """
        <div class="command_entry">
            <h2 class="command">%s</h2>
            <p class="usage">%s%s</p>
            <p class="description">%s</p>
        </div>""" % (command, prefix, usage.replace("<", "&lt;"), description.replace("\n", "<br>\n"))
    output += """
    </body>
</html>"""
    
    return output
