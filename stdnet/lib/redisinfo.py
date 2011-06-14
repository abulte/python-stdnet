from distutils.version import StrictVersion

from stdnet.utils.collections import OrderedDict
from stdnet import orm

init_data = {'set':{'count':0,'size':0},
             'zset':{'count':0,'size':0},
             'list':{'count':0,'size':0},
             'hash':{'count':0,'size':0},
             'ts':{'count':0,'size':0},
             'string':{'count':0,'size':0},
             'unknown':{'count':0,'size':0}}




class RedisStats(object):
    
    def __init__(self, rpy):
        self.r = rpy
        self.data = init_data.copy()

    def keys(self):
        return self.r.keys()
    
    def size(self):
        return self.r.dbsize()
    
    def incr_count(self, t, s = 0):
        d = self.data[t]
        d['count'] += 1
        d['size'] += s
        
    def __len__(self):
        return self.size()
    
    def __iter__(self):
        return self.data().__iter__()
    
    def cached_data(self):
        if not hasattr(self,'_data'):
            self._data = self.keys()
        return self._data
    
    def __getitem__(self, slic):
        data = self.cached_data()[slic]
        type_length = self.type_length
        for key in data:
            keys = key.decode()
            typ,len,ttl = type_length(key)
            if ttl == -1:
                ttl = False
            yield (keys,typ,len,ttl)

    def type_length(self, key):
        '''Retrive the type and length of a redis key.
        '''
        r = self.r
        pipe = r.pipeline()
        pipe.type(key).ttl(key)
        tt = pipe.execute()
        typ = tt[0].decode()
        if typ == 'set':
            cl = pipe.scard(key).srandmember(key).execute()
            l = cl[0]
            self.incr_count(typ,len(cl[1]))       
        elif typ == 'zset':
            cl = pipe.zcard(key).zrange(key,0,0).execute()
            l = cl[0]
            self.incr_count(typ,len(cl[1][0]))
        elif typ == 'list':
            l = pipe.llen(key).lrange(key,0,0)
            self.incr_count(typ,len(cl[1][0]))
        elif typ == 'hash':
            l = r.hlen(key)
            self.incr_count(typ)
        elif typ == 'ts':
            l = r.execute_command('TSLEN', key)
            self.incr_count(typ)
        elif typ == 'string':
            try:
                l = r.strlen(key)
            except:
                l = None
            self.incr_count(typ)
        else:
            self.incr_count('unknown')
            l = None
        return typ,l,tt[1]

    
class RedisDbData(orm.FakeModel):
    
    def __init__(self, rpy = None, db = None, keys = None, expires = None):
        self.rpy = rpy
        self.id = db
        if rpy:
            self.id = rpy.db
        self.keys = keys
        self.expires = expires
    
    @property
    def db(self):
        return self
    
    def __unicode__(self):
        return '{0}'.format(self.id)
    
    def stats(self):
        return RedisStats(self.rpy)


class RedisData(list):
    
    def append(self, **kwargs):
        instance = RedisDbData(**kwargs)
        super(RedisData,self).append(instance)
    
    @property
    def totkeys(self):
        keys = 0
        for db in self:
            keys += db.keys
        return keys


def format_int(val):
    def _iter(n):
        n = int(val)
        c = 0
        for v in reversed(str(abs(n))):
            if c == 3:
                c = 0
                yield ','
            else:
                yield v
    n = int(val)
    c = ''.join(reversed(_iter(n)))
    if n < 0:
        c = '-{0}'.format(c)
    return c


def niceadd(l,name,value):
    if value is not None:
        l.append({'name':name,'value':value})


def nicedate(t):
    try:
        d = datetime.fromtimestamp(t)
        return '%s %s' % (format(d.date(),site.settings.DATE_FORMAT),
                          time_format(d.time(),site.settings.TIME_FORMAT)) 
    except:
        return ''
    

def getint(v):
    try:
        return int(v)
    except:
        return None


def get_version(info):
    if 'redis_version' in info:
        return info['redis_version']
    else:
        return info['Server']['redis_version']


class RedisInfo(object):
    
    def __init__(self, version, info):
        self.version = version
        self.info = info
        self._panels = OrderedDict()
        self.makekeys()
        
    def __get_panels(self):
        if not self._panels:
            self.fill()
        return self._panels
    panels = property(__get_panels)
    
    def _dbs(self,keydata):
        for k in keydata:
            if k[:2] == 'db':
                try:
                    n = int(k[2:])
                except:
                    continue
                else:
                    yield k,n,keydata[k]
    
    def dbs(self,keydata):
        return sorted(self._dbs(keydata), key = lambda x : x[1])
            
    def db(self,n):
        return self.info['db{0}'.format(n)]
    
    def makekeys(self):
        self._makekeys(self.info)
        
    def _makekeys(self, kdata):
        rd = RedisData()
        tot = 0
        databases = []
        for k,n,data in self.dbs(kdata):
            keydb = data['keys']
            rd.append(db = n, keys = data['keys'], expires = data['expires'])
        self.databases = rd
    
    def fill(self):
        info = self.info
        server = self._panels['Server'] = []
        niceadd(server, 'Redis version', self.version)
        niceadd(server, 'Process id', info['process_id'])
        niceadd(server, 'Total keys', format_int(self.databases.totkeys))
        niceadd(server, 'Memory used', info['used_memory_human'])
        niceadd(server, 'Up time', nicetimedelta(info['uptime_in_seconds']))
        niceadd(server, 'Append Only File', 'yes' if info.get('aof_enabled',False) else 'no')
        niceadd(server, 'Virtual Memory enabled', 'yes' if info['vm_enabled'] else 'no')
        niceadd(server, 'Last save', nicedate(info['last_save_time']))
        niceadd(server, 'Commands processed', format_int(info['total_commands_processed']))
        niceadd(server, 'Connections received', format_int(info['total_connections_received']))
    

class RedisInfo22(RedisInfo):
    names = ('Server','Memory','Persistence','Diskstore','Replication','Clients','Stats','CPU')
    
    def makekeys(self):
        return self._makekeys(self.info['Keyspace'])
        
    def makepanel(self, name):
        pa = self._panels[name] = []
        for k,v in iteritems(self.info[name]):
            if v == 0:
                v = icons.circle_check()
            elif v == 1:
                v = icons.circle_check()
            pa.append({'name':nicename(k),'value':v})
            
    def fill(self):
        info = self.info
        for name in self.names:
            self.makepanel(name)
            
            
def redis_info(info):
    version = get_version(info)
    if StrictVersion(version) >= StrictVersion('2.2.0'):
        return RedisInfo22(version,info)
    else:
        return RedisInfo(version,info)
    