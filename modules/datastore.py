import sqlite3
import threading
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

def init():
    global connection, users, channels
    connection = sqlite('data/kb3.dat')
    users = UserSettingsCollection()
    channels = ChannelSettingsCollection()

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

class UserSettingsCollection(dict):
    def __getitem__(self, key):
        return UserSettings(key)
    
    def keys(self):
        return [x[0] for x in query("SELECT id FROM users")]
    
    def __setitem__(self, key, value):
        raise RuntimeError, "You can't set users directly."

class UserSettings(dict):
    def __init__(self, uid):
        self.uid = uid
    
    def __getitem__(self, key):
        result = query("SELECT value FROM user_settings WHERE setting = ? AND uid = ?", key, self.uid)
        if len(result) == 0:
            raise KeyError, key
        return result[0][0]
    
    def __setitem__(self, key, value):
        execute("REPLACE INTO user_settings (uid, setting, value) VALUES (?, ?, ?)", self.uid, key, value)
        return value
    
    def keys(self):
        return [x[0] for x in query("SELECT setting FROM user_settings WHERE uid = ?", self.uid)]

class ChannelSettingsCollection(dict):
    def __getitem__(self, key):
        if len(key) != 2:
            raise KeyError, key
        return ChannelSettings(key[0], key[1])
    
    def keys(self):
        return query("SELECT network, channel FROM channel_settings GROUP BY network, channel")
    
    def __setitem__(self, key, value):
        raise RuntimeError, "You can't set channels directly."

class ChannelSettings(dict):
    def __init__(self, network, channel):
        self.network = network
        self.channel = channel
    
    def __getitem__(self, key):
        result = query("SELECT value FROM channel_settings WHERE network = ? AND channel = ? AND setting = ?", self.network, self.channel, key)
        if len(result) == 0:
            raise KeyError, key
        return result[0][0]
    
    def __setitem__(self, key, value):
        execute("REPLACE INTO channel_settings (network, channel, setting, value) VALUES (?, ?, ?, ?)", self.network, self.channel, key, value)
        return value
    
    def keys(self):
        return [x[0] for x in query("SELECT setting FROM channel_settings WHERE network = ? AND channel = ?", self.network, self.channel)]