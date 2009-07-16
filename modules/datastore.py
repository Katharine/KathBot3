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

def init():
    global connection
    connection = sqlite('data/kb3.dat')

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