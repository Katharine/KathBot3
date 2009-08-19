# encoding: utf-8
import urllib2

active_server = None

def init():
    add_hook('message', message)
    m('webserver').add_handler('GET', handle_web)
    if 'secondlife-servers' not in m('datastore').general:
       m('datastore').general['secondlife-servers']  = {}

def message(irc, channel, origin, command, args):
    global active_server
    if command == 'slservers':
        servers = m('datastore').general['secondlife-servers']
        for server in servers:
            server = servers[server]
            active = ' ~B(Active)~B' if (active_server is not None and server.key == active_server.key) else ''
            m('irc_helpers').message(irc, channel, '~B%s~B - %s%s' % (server.description, server.region, active), tag='SL')
    elif command == 'setslserv':
        server = ' '.join(args)
        servers = m('datastore').general['secondlife-servers']
        for s in servers:
            if servers[s].description == server:
                active_server = servers[s]
                m('irc_helpers').message(irc, channel, "Changed current server to ~B%s~B." % server, tag='SL')
                break
        else:
            m('irc_helpers').message(irc, channel, "That server does not exist.", tag='SL')
    elif command == 'sensor':
        if active_server is not None:
            results = run_sensor()
            if not results:
                m('irc_helpers').message(irc, channel, "Nobody is near %s." % active_server.description, tag='SL')
            else:
                for result in results:
                    states = []
                    if result.info & LSL.AGENT_FLYING:
                        states.append('flying')
                    if result.info & LSL.AGENT_MOUSELOOK:
                        states.append('mouselook')
                    if result.info & LSL.AGENT_SITTING:
                        states.append('sitting')
                    if result.info & LSL.AGENT_AWAY:
                        states.append('away')
                    if result.info & LSL.AGENT_WALKING:
                        states.append('walking')
                    if result.info & LSL.AGENT_BUSY:
                        states.append('busy')
                    if not states:
                        states.append('nothing interesting')
                    m('irc_helpers').message(irc, channel, "%s (%sm) - %s" % (result.name, LSL.llVecDist(result.pos, active_server.position), ', '.join(states)), tag='SL')
    elif command == 'kick':
        key, name = find_key(args[0])
        if key is None:
            m('irc_helpers').message(irc, channel, "Couldn't find anyone to kick.", tag='SL')
        else:
            active_server.request('kick', key)
            m('irc_helpers').message(irc, channel, "Kicked ~B%s~B." % name, tag='SL')
    elif command == 'ban':
        key, name = find_key(args[0])
        if key is None:
            m('irc_helpers').message(irc, channel, "Couldn't find anyone to ban.", tag='SL')
        else:
            active_server.request('ban', key)
            m('irc_helpers').message(irc, channel, "Banned ~B%s~B." % name, tag='SL')
    elif command == 'slsay':
        active_server.request('say', ' '.join(args))
    elif command == 'slstats':
        data = active_server.request('stats').split('|')
        agents = int(data[0])
        fps = int(round(float(data[1])))
        td = int(round(float(data[2]) * 100))
        m('irc_helpers').message(irc, channel, u'Agents: ~B%s~B ~B·~B FPS: ~B%s~B ~B·~B Time Dilation: ~B%s%%~B' % (agents, fps, td), tag=active_server.region)

def find_key(name, server=None):
    server = server or active_server
    results = run_sensor(server)
    for result in results:
        if name.lower() in result.name.lower():
            return result.key, result.name
    return None, None

def run_sensor(server=None):
    server = server or active_server
    stuffs = server.request('sensor')
    if not stuffs:
        return []
    else:
        stuffs = stuffs.split('\n')
        results = []
        for result in stuffs:
            result = result.split('|')
            results.append(SensorResult(*result))
        return results

def handle_web(request):
    page = request.path.split('/')[2]
    if page == 'register':
        url = request.query['url'][0]
        description = request.query['description'][0]
        key = LSL.key(request.headers['X-SecondLife-Object-Key'])
        
        region = ' ('.join(request.headers['X-SecondLife-Region'].split(' (')[:-1])
        position = LSL.vector.parse(request.headers['X-SecondLife-Local-Position'])
        
        # Yes, we have to do it this way. Otherwise the value isn't saved.
        servers = m('datastore').general['secondlife-servers']
        servers[key] = Server(key=key, url=url, region=region, position=position, description=description)
        m('datastore').general['secondlife-servers'] = servers
        
        logger.info("Registered SL server.")
        return "ok"

class SensorResult(object):
    def __init__(self, key, name, pos, group, velocity, rotation, info):
        self.key = LSL.key(key)
        self.name = name
        self.pos = LSL.vector.parse(pos)
        self.group = bool(group)
        self.velocity = LSL.vector.parse(velocity)
        self.rotation = LSL.rotation.parse(rotation)
        self.info = int(info)
        

class Server(object):
    def __init__(self, key='', url='', region='', position='', description=''):
        self.key = key
        self.url = url
        self.region = region
        self.position = position
        self.description = description
    
    def request(self, page, param=None):
        url = '%s/%s' % (self.url, page)
        
        f = urllib2.urlopen(url, data=param)
        data = f.read()
        f.close()
        return data