# encoding: utf-8
from lupa import LuaRuntime, LuaError
import uuid
import os
import cgi
import errno
import json
import urllib2
import threading

lua_modules = {}
valid_tokens = {}

def init():
    add_hook('message', message)

    # For administrative interface
    try:
        m('webserver').add_handler('GET', web_editor)
        m('webserver').add_handler('POST', web_editor)
    except ModuleNotLoaded:
        logger.warning("Web module missing!")

def web_editor(request):
    parts = request.path[1:].split('/')
    if len(parts) > 1:
        key = parts[1]
        if key not in valid_tokens:
            return "access denied"
        user = valid_tokens[key]
        if len(parts) == 3:
            action = parts[2]
            if action == 'list':
                return render_module_list(user)
            elif action == 'create':
                request.send_response(302)
                request.send_header("Location", request.get_postdata()['name'][0] + "/edit")
                return
        elif len(parts) == 4:
            action = parts[3]
            module = parts[2]
            if action == 'edit':
                return render_module_editor(user, module)
            elif action == 'save':
                p = request.get_postdata()
                try:
                    with open('data/lua/%s.lua' % module.replace('/','_'), 'w') as f:
                        f.write(p['source'][0])
                except:
                    try:
                        if module in lua_modules:
                            lua_modules[module].stop()
                            del lua_modules[module]
                    except:
                        pass
                    return json.dumps({"saved": False, "running": False})
                if module in lua_modules:
                    lua_modules[module].stop()
                    try:
                        load_lua_module(module)
                    except LuaError as e:
                        return json.dumps({"saved": True, "running": False, "lua_error": str(e)})
                    return json.dumps({"saved": True, "running": True})
                else:
                    return json.dumps({"saved": True, "running": False})
            elif action == 'load':
                try:
                    lua_modules[module].stop()
                except:
                    pass
                try:
                    load_lua_module(module)
                except LuaError as e:
                    return json.dumps({'running': False, 'lua_error': str(e)})
                return json.dumps({'running': True})
            elif action == 'unload':
                try:
                    lua_modules[module].stop()
                except:
                    pass
                del lua_modules[module]
                return json.dumps({'running': False})

    raise m('webserver').FileNotFound()

def get_stored_modules():
    modules = sorted(x[:-4] for x in os.listdir('data/lua/'))
    return modules

def load_lua_module(m):
    with open('data/lua/%s.lua' % m.replace('/','_')) as f:
        source = f.read()
    l = LuaModule()
    result = l.run(source)
    try:
        success, result = result
    except:
        success = result
        pass
    if not success:
        raise LuaError(result)
    else:
        lua_modules[m] = l

def render_module_list(origin):
    template = """<!DOCTYPE html>
<html>
    <head>
        <title>Lua module listing</title>
        <link rel="stylesheet" type="text/css" href="/static/lua/style.css">
        <script type="text/javascript" src="https://ajax.googleapis.com/ajax/libs/jquery/1.8.3/jquery.min.js"></script>
        <script type="text/javascript" src="/static/lua/list.js"></script>
    </head>
    <body>
        <h1>List of Lua modules</h1>
        <ul id="module_list">
            %(module_list)s
        </ul>
        <form action="create" method="post" id="create_form">
            <p><input type="text" name="name" placeholder="module_name"> <input type="submit" value="Create new module"></p>
        </form>
        <p>Please do not share this URL, %(nick)s.</p>
    </body>
</html>"""
    module_list = []
    for module in get_stored_modules():
        loaded = module in lua_modules
        t = u"<li>%(n)s – <a href='%(n)s/edit' class='edit'>edit</a> | <a href='#' class='toggle %(a)s' data-module='%(n)s'>%(a)s</a></li>" % {'n':module, 'a': 'unload' if loaded else 'load'}
        module_list.append(t)
    return template % {'module_list': '\n'.join(module_list), 'nick': origin.nick}

def render_module_editor(origin, module):
    template = u"""<!DOCTYPE html>
<html>
    <head>
        <title>Edit module: %(name)s</title>
        <link rel="stylesheet" type="text/css" href="/static/lua/style.css">
        <script type="text/javascript" src="https://ajax.googleapis.com/ajax/libs/jquery/1.8.3/jquery.min.js"></script>

        <script type="text/javascript" src="/static/lua/codemirror/codemirror-compressed.js"></script>
        <link rel="stylesheet" type="text/css" href="/static/lua/codemirror/codemirror.css">
        <link rel="stylesheet" type="text/css" href="/static/lua/codemirror/dialog.css">

        <script type="text/javascript" src="/static/lua/editor.js"></script>
        <script type="text/javascript">
            var gIsLoaded = %(is_loaded)d;
        </script>
    </head>
    <body class='editor'>
        <h1>%(name)s</h1>
        <div id='container'>
            <form>
                <textarea id='text_editor' name='code'>%(source)s</textarea>
                <div id='action_bar'>
                    <p>
                        <input type='submit' value='Save (⌘S)' id='save_btn'>
                        <input type='button' value='%(action)s' id='toggle_running_btn'>
                    </p>
                    <p id='save_status'>

                    </p>
                </div>
                <input type="hidden" name="module" value="%(name)s">
            </form>
        </div>
    </body>
</html>"""
    source = ''
    try:
        with open('data/lua/%s.lua' % module.replace('/','_'), 'r') as f:
            source = f.read()
    except IOError as e:
        if e.errno == errno.ENOENT:
            source = ''
        else:
            raise
    is_loaded = module in lua_modules
    return template % {
        'name': module,
        'source': cgi.escape(source),
        'action': 'Unload' if is_loaded else 'Load',
        'is_loaded': is_loaded
    }

def message(irc, channel, origin, command, args):
    if command == 'lua':
        if not m('security').check_action_permissible(origin, command):
            m('irc_helpers').message(irc, channel, 'Access denied.')
            return
        try:
            lua = LuaModule()
            output = lua.run(' '.join(args))
        except LuaError as e:
            m('irc_helpers').message(irc, channel, "%s" % e)
        else:
            try:
                output = list(output)
                success = output.pop(0)
            except:
                success = output
                output = []
            if success:
                m('irc_helpers').message(irc, channel, '[lua] %s' % (', '.join([unicode(x) for x in output])))
            else:
                m('irc_helpers').message(irc, channel, '[lua error] %s' % ', '.join(output))
    elif command == 'luatest':
        module_name = args[0]
        source = ' '.join(args[1:])
        l = LuaModule()
        l.run(source)
        lua_modules[module_name] = l
    elif command == 'editlua':
        key = str(uuid.uuid4())
        valid_tokens[key] = origin
        m('irc_helpers').message(irc, origin.nick, '%slua/%s/list' % (m('webserver').get_root_address(), key))

    for n in lua_modules:
        lua_modules[n].event_message(irc, channel, origin, command, args)

class LuaModule(object):
    def __init__(self):
        self.lua = LuaRuntime(register_eval=False, attribute_filter=self.filter)

        # A subset of the standard library
        self.env = self.lua.eval("""{
            assert=assert,
            error=error,
            ipairs=ipairs,
            next=next,
            pairs=pairs,
            pcall=pcall,
            select=select,
            tonumber=tonumber,
            tostring=tostring,
            type=type,
            unpack=unpack,
            _VERSION=_VERSION,
            xpcall=xpcall,
            coroutine=coroutine,
            string=string,
            table=table,
            math=math,
            os={
                clock=os.clock,
                date=os.date,
                difftime=os.difftime,
                time=os.time
            }
        }""")

        self.env.kb = self.lua.table()
        self.env.kb['_private'] = self.lua.table(
            webget=self.lua_webget
        )
        self.env.kb['webget'] = self.lua.eval('function(url, callback) env.kb._private.webget(url, callback) end')

        self.events = self.lua.table()
        self.env.events = self.events

        self.lua.globals().env = self.env

        self.run = self.lua.eval("""
        function (untrusted_code)
          if untrusted_code:byte(1) == 27 then return nil, "binary bytecode prohibited" end
          local untrusted_function, message = loadstring(untrusted_code)
          if not untrusted_function then return nil, message end
          setfenv(untrusted_function, env)
          return pcall(untrusted_function)
        end
        """)

        self.lua.execute("""
            counter = 0
            running = 1
            debug.sethook(function (event, line)
                counter = counter + 1
                if not running or counter > 10000 then
                    error("That's enough!")
                end
            end, "", 1)
        """)

    def filter(self, object, attribute, is_setting):
        raise AttributeError("forbidden")

    def irc_wrapper(self, irc):
        wrapper = self.lua.table()
        wrapper['_network'] = irc
        wrapper['_send_message'] = lambda channel, message: m('irc_helpers').message(irc, channel, message)
        wrapper.send_message = self.lua.eval("function (self, channel, message) self._send_message(channel, message) end")
        return wrapper

    def channel_wrapper(self, irc, channel):
        wrapper = self.lua.table()
        wrapper['irc'] = self.irc_wrapper(irc)
        wrapper['_send'] = lambda message: m('irc_helpers').message(irc, channel, message)
        wrapper['send'] = self.lua.eval("function (self, message) self._send(message) end")
        try:
            chan = m('chantrack').network(irc)[channel]
        except KeyError:
            wrapper['members'] = self.lua.table()
        else:
            wrapper['members'] = self.list_to_table([self.user_wrapper(x) for x in chan.users.values()])
            wrapper['topic'] = chan.topic
        wrapper['name'] = channel
        return wrapper

    def user_wrapper(self, user):
        if user is None:
            return None
        wrapper = self.lua.table(
            hostname=user.hostname,
            nick=user.nick,
            ident=user.ident,
            realname=getattr(user, 'realname', None),
            modes=getattr(user, 'modes', None),
            _send=lambda message: m('irc_helpers').message(irc, user.nick, message),
            send=self.lua.eval('function(self, message) self._send(message) end')
        )
        return wrapper

    def event_message(self, irc, channel, origin, command, args):
        if self.events.received_command:
            self.lua.globals().counter = 0
            self.events.received_command(self.channel_wrapper(irc, channel), self.user_wrapper(origin), command, self.list_to_table(args))

    def list_to_table(self, iter):
        return self.lua.table(*iter)

    def lua_webget(self, url, callback):
        def do_callback():
            try:
                f = urllib2.urlopen(url)
                result = f.read()
            except urllib2.URLError as e:
                callback(False, str(e))
            else:
                callback(True, result)
        threading.Thread(target=do_callback).start()

    def stop(self):
        self.lua.globals().running = 0
