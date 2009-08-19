# Implements a random subset of LSL. Woo.
from uuid import UUID

# Functions
def llVecNorm(vec):
    return (vec / llVecMag(vec))

def llVecMag(vec):
    return (vec.x ** 2 + vec.y ** 2 + vec.z ** 2) ** 0.5

def llVecDist(vec1, vec2):
    return llVecMag(vec1 - vec2)

# Constants
NULL_KEY = '00000000-0000-0000-0000-000000000000'

AGENT_FLYING        = 0x0001
AGENT_ATTACHMENTS   = 0x0002
AGENT_SCRIPTED      = 0x0004
AGENT_MOUSELOOK     = 0x0008
AGENT_SITTING       = 0x0010
AGENT_ON_OBJECT     = 0x0020
AGENT_AWAY          = 0x0040
AGENT_WALKING       = 0x0080
AGENT_IN_AIR        = 0x0100
AGENT_TYPING        = 0x0200
AGENT_CROUCHING     = 0x0400
AGENT_BUSY          = 0x0800
AGENT_ALWAYS_RUN    = 0x1000

# Types
class vector(object):
    def __init__(self, x, y, z):
        self.x = float(x)
        self.y = float(y)
        self.z = float(z)
    
    def __add__(self, other):
        if not isinstance(other, vector):
            raise NotImplemented
        return vector(self.x + other.x, self.y + other.y, self.z + other.z)
    
    def __sub__(self, other):
        if not isinstance(other, vector):
            raise NotImplemented
        return vector(self.x - other.x, self.y - other.y, self.z - other.z)
    
    def __div__(self, other):
        return vector(self.x / other, self.y / other, self.z / other)
    
    def __str__(self):
        return '<%s, %s, %s>' % (self.x, self.y, self.z)
    
    def __repr__(self):
        return 'vector(%s, %s, %s)' % (self.x, self.y, self.z)
    
    @staticmethod
    def parse(string):
        parts = [float(x.strip()) for x in string.strip('()<>').split(',')]
        return vector(*parts)
    
class rotation(object):
    def __init__(self, x, y, z, w):
        self.x = x
        self.y = y
        self.z = z
        self.w = w
    
    @staticmethod
    def parse(string):
        parts = [float(x.strip()) for x in string.strip('()<>').split(',')]
        return rotation(*parts)

class key(object):
    def __init__(self, uuid=NULL_KEY):
        if not isinstance(uuid, UUID):
            self.uuid = UUID(uuid)
        else:
            self.uuid = uuid
    
    def __str__(self):
        return self.uuid.urn.split(':')[2]
    
    def __repr__(self):
        return "key('%s')" % self.__str__()
    
    def __hash__(self):
        return self.uuid.__hash__()
    
    def __eq__(self, other):
        return str(self) == str(other)
    
    def __ne__(self, other):
        return not (self == other)
    
    def __nonzero__(self):
        return (self.uuid.int != 0)
    
    @staticmethod
    def random():
        return key(UUID.uuid4())