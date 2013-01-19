# encoding: utf-8

from lupa import LuaRuntime, LuaError
import threading
import urllib2
import os

lua_modules = {}

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

def handle_message(irc, channel, origin, command, args):
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
        self.lua.globals()['kb_private'] = self.lua.table(
            webget=self.lua_webget,
            schedule_at=self.lua_schedule_at,
            schedule_cron=self.lua_schedule_cron
        )
        self.env.kb['webget'] = self.lua.eval('function(url, callback) kb_private.webget(url, callback) end')
        self.env.kb['schedule_at'] = self.lua.eval('function(when, user_data, callback) kb_private.schedule_at(when, user_data, callback) end')
        self.env.kb['schedule_cron'] = self.lua.eval('function (period, user_data, callback) kb_private.schedule_cron(period, user_data, callback) end')

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

    def lua_schedule_at(self, when, user_data, callback):
        try:
            m('cron').add_at(when, callback, when, user_data)
        except ModuleNotLoaded:
            return False
        else:
            return True

    def lua_schedule_cron(self, period, user_data, callback):
        try:
            m('cron').add_cron(period, callback, user_data)
        except ModuleNotLoaded:
            return False
        else:
            return True

    def stop(self):
        self.lua.globals().running = 0
