# encoding: utf-8

import cgi
import json
import uuid
import errno
import os
from lupa import LuaError

valid_tokens = {}

def generate_url(origin):
    key = str(uuid.uuid4())
    valid_tokens[key] = origin
    return '%slua/%s/list' % (m('webserver').get_root_address(), key)

def editor(request):
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
                        if module in interpreter.lua_modules:
                            interpreter.lua_modules[module].stop()
                            del interpreter.lua_modules[module]
                    except:
                        pass
                    return json.dumps({"saved": False, "running": False})
                if module in interpreter.lua_modules:
                    interpreter.lua_modules[module].stop()
                    try:
                        interpreter.load_module(module)
                    except LuaError as e:
                        return json.dumps({"saved": True, "running": False, "lua_error": str(e)})
                    return json.dumps({"saved": True, "running": True})
                else:
                    return json.dumps({"saved": True, "running": False})
            elif action == 'load':
                try:
                    interpreter.lua_modules[module].stop()
                except:
                    pass
                try:
                    interpreter.load_module(module)
                except LuaError as e:
                    return json.dumps({'running': False, 'lua_error': str(e)})
                return json.dumps({'running': True})
            elif action == 'unload':
                interpreter.unload_module(module)
                return json.dumps({'running': False})

    raise m('webserver').FileNotFound()

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
    for module in interpreter.get_stored_modules():
        loaded = module in interpreter.lua_modules
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
    is_loaded = module in interpreter.lua_modules
    return template % {
        'name': module,
        'source': cgi.escape(source),
        'action': 'Unload' if is_loaded else 'Load',
        'is_loaded': is_loaded
    }
