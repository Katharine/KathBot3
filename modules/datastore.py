import sqlite3
import threading
import pickle
from Queue import Queue

class sqlite(threading.Thread):
    def __init__(self, db):
        super(sqlite, self).__init__()
        self.db = db
        self.requests = Queue()
        self.start()

    def run(self):
        connection = sqlite3.connect(self.db) 
        cursor = connection.cursor()
        while True:
            request, args, result = self.requests.get()
            if request == '__close__':
                break
            
            try:
                cursor.execute(request, args)
                
                if result:
                    if request.startswith("INSERT"):
                        result.put(cursor.lastrowid)
                    else:
                        result.put(cursor.fetchall())
                else:
                    connection.commit()
            except (sqlite3.OperationalError, sqlite3.InterfaceError, sqlite3.IntegrityError), message:
                if result:
                    result.put([])
                logger.error("SQL error: %s" % message)
            
            cursor.close()
        connection.close()

    def execute(self, req, arg=None, res=None):
        self.requests.put((req, arg or tuple(), res))

    def select(self, query, args=None):
        result = Queue()
        self.execute(query, args, result)
        return result.get(True, 5)

    def close(self):
        self.execute('__close__')

thread = None
query_count = 0
users = None
channels = None
general = None

def init():
    global connection, users, channels, general
    connection = sqlite('data/kb3.dat')
    users = UserSettingsCollection()
    channels = ChannelSettingsCollection()
    general = GlobalSettings()

def shutdown():
    connection.close()

def query(sql, *args):
    global query_count
    query_count += 1
    return connection.select(sql, args)

def execute(sql, *args):
    global query_count
    query_count += 1
    connection.execute(sql, args)

class KBDict(dict):
    def __contains__(self, key):
        try:
            self.__getitem__(key)
            return True
        except KeyError:
            return False

    def get(self, key, default=None):
        try:
            return self.__getitem__(key)
        except KeyError:
            return default
    
    def serialise(self, value):
        if isinstance(value, str):
            return value
        elif isinstance(value, bool):
            if value:
                return '__TRUE__'
            else:
                return '__FALSE__'
        elif isinstance(value, int) or isinstance(value, long):
            return value.__repr__()
        elif isinstance(value, float):
            return str(value)
        elif value is None:
            return None
        else:
            return sqlite3.Binary('__PICKLED_DATA__' + pickle.dumps(value, pickle.HIGHEST_PROTOCOL))
    
    def unserialise(self, value):
        value = str(value)
        if value == '':
            return value
        if value == '__TRUE__':
            return True
        elif value == '__FALSE__':
            return False
        try:
            if value[-1].upper() == 'L':
                return long(value)
            i = int(value)
            f = float(value)
            if i - f < 0.0000001:
                return i
            else:
                return f
        except:
            if value.startswith('__PICKLED_DATA__'):
                try:
                    return pickle.loads(value[16:])
                except:
                    return value
            else:
                return value

class UserSettingsCollection(dict):
    def __getitem__(self, key):
        return UserSettings(key)
    
    def keys(self):
        return [x[0] for x in query("SELECT id FROM users")]
    
    def __setitem__(self, key, value):
        raise RuntimeError, "You can't set users directly."

class UserSettings(KBDict):
    def __init__(self, uid):
        self.uid = uid
    
    def __getitem__(self, key):
        result = query("SELECT value FROM user_settings WHERE setting = ? AND uid = ?", key, self.uid)
        if len(result) == 0:
            raise KeyError, key
        return self.unserialise(result[0][0])
    
    def __setitem__(self, key, value):
        execute("REPLACE INTO user_settings (uid, setting, value) VALUES (?, ?, ?)", self.uid, key, self.serialise(value))
        return value
        
    def __delitem__(self, key):
        execute("DELETE FROM user_settings WHERE setting = ? AND uid = ?", key, self.uid)

    def keys(self):
        return [x[0] for x in query("SELECT setting FROM user_settings WHERE uid = ?", self.uid)]

class ChannelSettingsCollection(dict):
    def __getitem__(self, key):
        if len(key) != 2:
            raise KeyError, key
        network = key[0]
        if hasattr(network, 'network'):
            network = network.network
        if hasattr(network, 'name'):
            network = network.name
        return ChannelSettings(network, key[1])
    
    def keys(self):
        return query("SELECT network, channel FROM channel_settings GROUP BY network, channel")
    
    def __setitem__(self, key, value):
        raise RuntimeError, "You can't set channels directly."

class ChannelSettings(KBDict):
    def __init__(self, network, channel):
        self.network = network
        self.channel = channel
    
    def __getitem__(self, key):
        result = query("SELECT value FROM channel_settings WHERE network = ? AND channel = ? AND setting = ?", self.network, self.channel, key)
        if len(result) == 0:
            raise KeyError, key
        return self.unserialise(result[0][0])
    
    def __setitem__(self, key, value):
        execute("REPLACE INTO channel_settings (network, channel, setting, value) VALUES (?, ?, ?, ?)", self.network, self.channel, key, self.serialise(value))
        return value
    
    def __delitem__(self, key):
        execute("DELETE FROM channel_settings WHERE network = ? AND channel = ? AND setting = ?", self.network, self.channel, key)
    
    def keys(self):
        return [x[0] for x in query("SELECT setting FROM channel_settings WHERE network = ? AND channel = ?", self.network, self.channel)]

class GlobalSettings(KBDict):
    def __getitem__(self, key):
        result = query("SELECT value FROM global_settings WHERE setting = ?", key)
        if len(result) == 0:
            raise KeyError, key
        return self.unserialise(result[0][0])
    
    def __setitem__(self, key, value):
        execute("REPLACE INTO global_settings (setting, value) VALUES (?, ?)", key, self.serialise(value))
        return value
        
    def __delitem__(self, key):
        execute("DELETE FROM global_settings WHERE setting = ?", key)
    
    def keys(self):
        return [x[0] for x in query("SELECT setting FROM global_settings")]