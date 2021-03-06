import os
from datetime import date, datetime, timedelta
from struct import unpack

from stdnet import SessionNotAvailable, CommitException
from stdnet.utils import test, encoders, populate, ispy3k
from stdnet.apps.columnts import ColumnTS
from stdnet.lib import redis

from examples.data import tsdata
from examples.tsmodels import ColumnTimeSeries

from tests.py import struct

nan = float('nan')
this_path = os.path.split(os.path.abspath(__file__))[0]

bin_to_float = lambda f : unpack('>d', f)[0]
if ispy3k:  #pragma nocover
    bitflag = lambda value: value
else:   #pragma nocover
    bitflag = ord
    
class timeseries_test1(redis.RedisScript):
    script = (redis.read_lua_file('tabletools'),
              redis.read_lua_file('columnts.columnts'),
              redis.read_lua_file('test1',this_path))
    

class TestMeta(test.CleanTestCase):
    
    def testLuaClass(self):
        session = self.session()
        ts = session.add(ColumnTS(id = 'bla'))
        c = self.backend.client
        r = c.script_call('timeseries_test1',ts.dbid())
        self.assertEqual(r,b'OK')


class TestCase(test.CleanTestCase):
    
    def check_stats(self, stat_field, data):
        N = len(data)
        cdata = list((d for d in data if d==d))
        cdata2 = list((d*d for d in cdata))
        dd = list((a-b for a,b in zip(cdata[1:],cdata[:-1])))
        dd2 = list((d*d for d in dd))
        NC = len(cdata)
        self.assertEqual(stat_field['N'],NC)
        self.assertAlmostEqual(stat_field['min'], min(cdata))
        self.assertAlmostEqual(stat_field['max'], max(cdata))
        self.assertAlmostEqual(stat_field['sum'], sum(cdata)/NC)
        self.assertAlmostEqual(stat_field['sum2'], sum(cdata2)/NC)
        self.assertAlmostEqual(stat_field['dsum'], sum(dd)/(NC-1))
        self.assertAlmostEqual(stat_field['dsum2'], sum(dd2)/(NC-1))
        

class TestTimeSeries(struct.StructMixin, TestCase):
    structure = ColumnTS
    name = 'columnts'
    
    def createOne(self, session):
        ts = session.add(ColumnTS(id = 'goog'))
        d1 = date(2012,1,23)
        data = {d1: {'open':586, 'high':588.66,
                     'low':583.16, 'close':585.52},
                date(2012,1,20): {'open':590.53, 'high':591,
                                  'low':581.7, 'close':585.99},
                date(2012,1,19): {'open':640.99, 'high':640.99,
                                  'low':631.46, 'close':639.57}}
        ts.add(d1,data[d1])
        self.data = data
        data = self.data.copy()
        data.pop(d1)
        data = tuple(data.items())
        ts.update(data)
        # test bad add
        self.assertRaises(TypeError, ts.add, date(2012,1,20), 1, 2, 3)
        return ts
    
    def makeGoogle(self):
        session = self.session()
        with session.begin():
            ts = self.createOne(session)
            self.assertTrue(len(ts.cache.fields['open']),2)
            self.assertTrue(len(ts.cache.fields),4)
        self.assertEqual(ts.size(), 3)
        dates, fields = ts.irange()
        self.assertEqual(len(fields),4)
        self.assertEqual(len(dates),3)
        for field in fields:
            values = fields[field]
            self.assertEqual(len(values),3)
            for dt, v in zip(dates, values):
                v2 = self.data[dt.date()][field]
                self.assertAlmostEqual(v,v2)
        return ts
            
    def testEmpty2(self):
        '''Check an empty timeseries'''
        session = self.session()
        ts = session.add(ColumnTS(id='goog'))
        self.assertEqual(ts.size(),0)
        self.assertEqual(ts.numfields(),0)
        self.assertEqual(ts.fields(),())
        
    def testFrontBack(self):
        session = self.session()
        ts = session.add(ColumnTS(pickler=encoders.DateConverter()))
        self.assertEqual(ts.size(),0)
        self.assertEqual(ts.front(), None)
        self.assertEqual(ts.back(), None)
        d2 = date.today()
        d1 = d2 - timedelta(days=2)
        session.begin()
        ts.add(d2,'foo',-5.2)
        ts.add(d1,'foo',789.3)
        self.assertEqual(ts.size(),0)
        self.assertEqual(ts.front(), None)
        self.assertEqual(ts.back(), None)
        session.commit()
        self.assertEqual(ts.size(),2)
        self.assertEqual(ts.front(), (d1,{'foo':789.3}))
        self.assertEqual(ts.back(), (d2,{'foo':-5.2}))
        
    def testAddSimple(self):
        session = self.session()
        ts = session.add(ColumnTS(id='goog'))
        # start a transaction
        session.begin()
        ts.add(date.today(),'pv',56)
        self.assertEqual(ts.size(),0)
        self.assertTrue(ts.cache.fields)
        ts.add(date.today()-timedelta(days=2), 'pv', 53.8)
        self.assertTrue(len(ts.cache.fields['pv']), 2)
        # commit transaction
        session.commit()
        self.assertEqual(ts.fields(),('pv',))
        self.assertEqual(ts.numfields(),1)
        self.assertEqual(ts.size(),2)
        #
        # Check that a string is available at the field key
        bts = ts.backend_structure()
        keys = tuple(bts.allkeys())
        self.assertEqual(len(keys),3)
        self.assertTrue(bts.id in keys)
        self.assertTrue(bts.fieldsid in keys)
        self.assertTrue(bts.fieldid('pv') in keys)
        raw_data = bts.field('pv')
        self.assertTrue(raw_data)
        self.assertEqual(len(raw_data),18)
        a1 = raw_data[:9]
        a2 = raw_data[9:]
        n = bitflag(a1[0])
        self.assertEqual(n, bitflag(a2[0]))
        self.assertEqual(n, 2)
        self.assertEqual(bin_to_float(a1[1:]), 53.8)
        self.assertEqual(bin_to_float(a2[1:]), 56)
        #
        data = ts.irange()
        self.assertEqual(len(data),2)
        dt,fields = data
        self.assertEqual(len(dt),2)
        self.assertTrue('pv' in fields)
        for v, t in zip(fields['pv'],[53.8, 56]):
            self.assertAlmostEqual(v, t)
        
    def testAddNil(self):
        session = self.session()
        # start a transaction
        session.begin()
        ts = session.add(ColumnTS(id='goog'))
        ts.add(date.today(), 'pv', 56)
        ts.add(date.today()-timedelta(days=2), 'pv', nan)
        session.commit()
        self.assertEqual(ts.size(), 2)
        dt, fields = ts.irange()
        self.assertEqual(len(dt), 2)
        self.assertTrue('pv' in fields)
        n = fields['pv'][0]
        self.assertNotEqual(n, n)
        
    def testGoogleDrop(self):
        ts = self.makeGoogle()
        self.assertEqual(ts.fields(),('close','high','low','open'))
        self.assertEqual(ts.numfields(),4)
        self.assertEqual(ts.size(),3)
        
    def testRange(self):
        ts = self.makeGoogle()
        data = ts.irange()
        self.assertEqual(len(data),2)
        dt,fields = data
        self.assertEqual(len(fields),4)
        high = list(zip(dt,fields['high']))
        self.assertEqual(high[0],(datetime(2012,1,19),640.99))
        self.assertEqual(high[1],(datetime(2012,1,20),591))
        self.assertEqual(high[2],(datetime(2012,1,23),588.66))
        
    def testRangeField(self):
        ts = self.makeGoogle()
        data = ts.irange(fields=('low','high','badone'))
        self.assertEqual(len(data),2)
        dt,fields = data
        self.assertEqual(len(fields),2)
        low = list(zip(dt,fields['low']))
        high = list(zip(dt,fields['high']))
        self.assertEqual(high[0],(datetime(2012,1,19),640.99))
        self.assertEqual(high[1],(datetime(2012,1,20),591))
        self.assertEqual(high[2],(datetime(2012,1,23),588.66))
        
    def testRaises(self):
        ts = self.makeGoogle()
        self.assertRaises(TypeError, ts.merge, 5)
        self.assertRaises(ValueError, ts.merge, (5,))
        ts.session = None
        self.assertRaises(SessionNotAvailable, ts.merge, (5, ts))
        
    def testUpdateDict(self):
        '''Test updating via a dictionary.'''
        ts = self.makeGoogle()
        data = {date(2012,1,23):{'open':586.00, 'high':588.66,
                                 'low':583.16, 'close':585.52},
                date(2012,1,25):{'open':586.32, 'high':687.68,
                                 'low':578, 'close':580.93},
                date(2012,1,24):{'open':586.32, 'high':687.68,
                                 'low':578, 'close':580.93}}
        ts.update(data)
        self.assertEqual(ts.size(), 5)
        dates, fields = ts.range(date(2012,1,23), date(2012,1,25))
        self.assertEqual(len(dates),3)
        self.assertEqual(dates[0].date(),date(2012,1,23))
        self.assertEqual(dates[1].date(),date(2012,1,24))
        self.assertEqual(dates[2].date(),date(2012,1,25))
        for field in fields:
            for d, v1 in zip(dates, fields[field]):
                v2 = data[d.date()][field]
                self.assertAlmostEqual(v1, v2)
        
    def testBadQuery(self):
        ts = self.makeGoogle()
        # get the backend id and override it
        id = ts.dbid()
        client = ts.session.backend.client
        client.delete(id)
        client.rpush(id, 'bla')
        client.rpush(id, 'foo')
        self.assertEqual(client.llen(id), 2)
        self.assertRaises(redis.ScriptError, ts.add,
                          date(2012,1,23), {'open':586})
        self.assertRaises(redis.ScriptError, ts.irange)
        self.assertRaises(redis.RedisInvalidResponse, ts.size)
        
    def testGet(self):
        ts = self.makeGoogle()
        v = ts.get(date(2012,1,23))
        self.assertTrue(v)
        self.assertEqual(len(v),4)
        v2 = ts[date(2012,1,23)]
        self.assertEqual(v,v2)
        self.assertEqual(ts.get(date(2014,1,1)),None)
        self.assertRaises(KeyError, lambda: ts[date(2014,1,1)])
        
    def testSet(self):
        ts = self.makeGoogle()
        ts[date(2012,1,27)] = {'open': 600}
        self.assertEqual(len(ts), 4)
        res = ts[date(2012,1,27)]
        self.assertEqual(len(res),4)
        self.assertEqual(res['open'], 600)
        self.assertNotEqual(res['close'],res['close'])
        self.assertNotEqual(res['high'],res['high'])
        self.assertNotEqual(res['low'],res['low'])
        
    def testIter(self):
        ts = self.makeGoogle()
        dates = list(ts)
        self.assertTrue(dates)
        self.assertEqual(len(dates),3)
        for dt in dates:
            self.assertTrue(isinstance(dt,datetime))
        

class TestColumnTSBase(TestCase):
    '''Class for testing large data'''
    @classmethod
    def setUpClass(cls):
        size = cls.size
        cls.data1 = tsdata(size=size, fields=('a','b','c','d','f','g'))
        cls.data2 = tsdata(size=size, fields=('a','b','c','d','f','g'))
        cls.data3 = tsdata(size=size, fields=('a','b','c','d','f','g'))
        cls.data_mul1 = tsdata(size=size, fields=('eurusd',))
        cls.data_mul2 = tsdata(size=size, fields=('gbpusd',))
        cls.ColumnTS = ColumnTS
        super(TestColumnTSBase, cls).setUpClass()
    
    def create(self):
        '''Create one ColumnTS with six fields and cls.size dates'''
        session = self.session()
        with session.begin():
            ts1 = session.add(self.ColumnTS())
            ts1.update(self.data1.values)
        return ts1
    

class TestOperations(TestColumnTSBase):
    
    def testSimpleStats(self):
        ts1 = self.create()
        dt,fields = ts1.irange()
        self.assertEqual(len(fields),6)
        result = ts1.istats(0,-1)
        self.assertTrue(result)
        self.assertEqual(result['start'],dt[0])
        self.assertEqual(result['stop'],dt[-1])
        self.assertEqual(result['len'],len(dt))
        stats = result['stats']
        for field in ('a','b','c','d','f','g'):
            self.assertTrue(field in stats)
            stat_field = stats[field]
            data = self.data1.sorted_fields[field]
            self.check_stats(stat_field, data)
            
    def testStatsByTime(self):
        ts1 = self.create()
        dt, fields = ts1.irange()
        self.assertEqual(len(fields),6)
        dt = dt[5:-5]
        start = dt[0]
        end = dt[-1]
        # Perform the statistics between start and end
        result = ts1.stats(start, end)
        self.assertTrue(result)
        self.assertEqual(result['start'], start)
        self.assertEqual(result['stop'], end)
        self.assertEqual(result['len'], len(dt))
        stats = result['stats']
        for field in ('a','b','c','d','f','g'):
            self.assertTrue(field in stats)
            stat_field = stats[field]
            data = self.data1.sorted_fields[field][5:-5]
            self.check_stats(stat_field, data)
            
    def test_merge2series(self):
        session = self.session()
        with session.begin():
            ts1 = session.add(self.ColumnTS())
            ts2 = session.add(self.ColumnTS())
            ts1.update(self.data1.values)
            ts2.update(self.data2.values)
        self.assertEqual(ts1.size(),len(self.data1.unique_dates))
        self.assertEqual(ts1.numfields(),6)
        self.assertEqual(ts2.size(),len(self.data2.unique_dates))
        self.assertEqual(ts2.numfields(),6)
        ts3 = self.ColumnTS(id = 'merged')
        # merge ts1 with weight -1  and ts2 with weight 2
        ts3.merge((-1,ts1),(2,ts2))
        session.commit()
        self.assertTrue(ts3.size())
        self.assertEqual(ts3.numfields(),6)
        times, fields = ts3.irange()
        for i,dt in enumerate(times):
            dt = dt.date()
            v1 = ts1.get(dt)
            v2 = ts2.get(dt)
            if dt in self.data1.unique_dates and dt in self.data2.unique_dates:
                for field, values in fields.items():
                    res = 2*v2[field] - v1[field]
                    self.assertAlmostEqual(values[i],res)
            else:
                self.assertTrue(v1 is None or v2 is None)
                for values in fields.values():
                    v = values[i]
                    self.assertNotEqual(v,v)
                 
    def test_merge3series(self):
        session = self.session()
        with session.begin():
            ts1 = session.add(self.ColumnTS())
            ts2 = session.add(self.ColumnTS())
            ts3 = session.add(self.ColumnTS())
            ts1.update(self.data1.values)
            ts2.update(self.data2.values)
            ts3.update(self.data3.values)
        self.assertEqual(ts1.size(),self.data1.length)
        self.assertEqual(ts2.size(),self.data2.length)
        self.assertEqual(ts3.size(),self.data3.length)
        with session.begin():
            ts = self.ColumnTS(id = 'merged')
            ts.merge((0.5,ts1),(1.3,ts2),(-2.65,ts3))
            self.assertEqual(ts.session,session)
        length = ts.size()
        self.assertTrue(length >= max(self.data1.length,self.data2.length,
                                      self.data3.length))
        self.assertEqual(ts.numfields(),6)
        times, fields = ts.irange()
        for i,dt in enumerate(times):
            dt = dt.date()
            v1 = ts1.get(dt)
            v2 = ts2.get(dt)
            v3 = ts3.get(dt)
            if v1 is not None and v2 is not None and v3 is not None:
                for field,values in fields.items():
                    res = 0.5*v1[field] + 1.3*v2[field] - 2.65*v3[field]
                    self.assertAlmostEqual(values[i],res)
            else:
                for values in fields.values():
                    v = values[i]
                    self.assertNotEqual(v,v)

    def testAddMultiply1(self):
        session = self.session()
        with session.begin():
            ts1 = session.add(self.ColumnTS())
            ts2 = session.add(self.ColumnTS())
            mul1 = session.add(self.ColumnTS())
            ts1.update(self.data1.values)
            ts2.update(self.data2.values)
            mul1.update(self.data_mul1.values)
        self.assertEqual(ts1.size(),self.data1.length)
        self.assertEqual(ts2.size(),self.data2.length)
        self.assertEqual(mul1.size(),self.data_mul1.length)
        with session.begin():
            ts = self.ColumnTS(id = 'merged')
            ts.merge((1.5,mul1,ts1),(-1.2,ts2))
            self.assertEqual(ts.session,session)
        length = ts.size()
        self.assertTrue(length >= max(self.data1.length,
                                      self.data2.length))
        self.assertEqual(ts.numfields(),6)
        times, fields = ts.irange()
        for i,dt in enumerate(times):
            dt = dt.date()
            v1 = ts1.get(dt)
            v2 = ts2.get(dt)
            m1 = mul1.get(dt)
            if v1 is not None and v2 is not None and m1 is not None:
                m1 = m1['eurusd']
                for field,values in fields.items():
                    res = 1.5*m1*v1[field] - 1.2*v2[field]
                    self.assertAlmostEqual(values[i],res)
            else:
                for values in fields.values():
                    v = values[i]
                    self.assertNotEqual(v,v)
    
    def testAddMultiply(self):
        session = self.session()
        with session.begin():
            ts1 = session.add(self.ColumnTS())
            ts2 = session.add(self.ColumnTS())
            mul1 = session.add(self.ColumnTS())
            mul2 = session.add(self.ColumnTS())
            ts1.update(self.data1.values)
            ts2.update(self.data2.values)
            mul1.update(self.data_mul1.values)
            mul2.update(self.data_mul2.values)
        self.assertEqual(ts1.size(),self.data1.length)
        self.assertEqual(ts2.size(),self.data2.length)
        self.assertEqual(mul1.size(),self.data_mul1.length)
        self.assertEqual(mul2.size(),self.data_mul2.length)
        with session.begin():
            ts = self.ColumnTS(id='merged')
            ts.merge((1.5,mul1,ts1),(-1.2,mul2,ts2))
            self.assertEqual(ts.session,session)
        length = ts.size()
        self.assertTrue(length >= max(self.data1.length,
                                      self.data2.length))
        self.assertEqual(ts.numfields(),6)
        times, fields = ts.irange()
        for i,dt in enumerate(times):
            dt = dt.date()
            v1 = ts1.get(dt)
            v2 = ts2.get(dt)
            m1 = mul1.get(dt)
            m2 = mul2.get(dt)
            if v1 is not None and v2 is not None and m1 is not None\
                     and m2 is not None:
                m1 = m1['eurusd']
                m2 = m2['gbpusd']
                for field,values in fields.items():
                    res = 1.5*m1*v1[field] - 1.2*m2*v2[field]
                    self.assertAlmostEqual(values[i],res)
            else:
                for values in fields.values():
                    v = values[i]
                    self.assertNotEqual(v,v)
                    
    def testMultiplyNoStore(self):
        session = self.session()
        with session.begin():
            ts1 = session.add(self.ColumnTS())
            ts2 = session.add(self.ColumnTS())
            ts1.update(self.data1.values)
            ts2.update(self.data2.values)
        self.assertEqual(ts1.size(),self.data1.length)
        self.assertEqual(ts2.size(),self.data2.length)
        times, fields = self.ColumnTS.merged_series((1.5,ts1),(-1.2,ts2))
        for i,dt in enumerate(times):
            dt = dt.date()
            v1 = ts1.get(dt)
            v2 = ts2.get(dt)
            if v1 is not None and v2 is not None:
                for field,values in fields.items():
                    res = 1.5*v1[field] - 1.2*v2[field]
                    self.assertAlmostEqual(values[i],res)
            else:
                for values in fields.values():
                    v = values[i]
                    self.assertNotEqual(v,v)

    def testMergedFields(self):
        session = self.session()
        with session.begin():
            ts1 = session.add(self.ColumnTS())
            ts2 = session.add(self.ColumnTS())
            mul1 = session.add(self.ColumnTS())
            mul2 = session.add(self.ColumnTS())
            ts1.update(self.data1.values)
            ts2.update(self.data2.values)
            mul1.update(self.data_mul1.values)
            mul2.update(self.data_mul2.values)
        self.assertEqual(ts1.size(),self.data1.length)
        self.assertEqual(ts2.size(),self.data2.length)
        self.assertEqual(mul1.size(),self.data_mul1.length)
        self.assertEqual(mul2.size(),self.data_mul2.length)
        with session.begin():
            ts = self.ColumnTS(id='merged')
            ts.merge((1.5,mul1,ts1),(-1.2,mul2,ts2),
                     fields = ('a','b','c','badone'))
            self.assertEqual(ts.session,session)
        length = ts.size()
        self.assertTrue(length >= max(self.data1.length,
                                      self.data2.length))
        self.assertEqual(ts.numfields(),3)
        self.assertEqual(ts.fields(),('a','b','c'))
        times, fields = ts.irange()
        for i,dt in enumerate(times):
            dt = dt.date()
            v1 = ts1.get(dt)
            v2 = ts2.get(dt)
            m1 = mul1.get(dt)
            m2 = mul2.get(dt)
            if v1 is not None and v2 is not None and m1 is not None\
                     and m2 is not None:
                m1 = m1['eurusd']
                m2 = m2['gbpusd']
                for field,values in fields.items():
                    res = 1.5*m1*v1[field] - 1.2*m2*v2[field]
                    self.assertAlmostEqual(values[i],res)
            else:
                for values in fields.values():
                    v = values[i]
                    self.assertNotEqual(v,v)


class TestMultivariateStats(TestColumnTSBase):
    
    def testSimpleMultiStats(self):
        ts1 = self.create()
        dt,fields = ts1.irange()
        result = ts1.imulti_stats()
        self.assertTrue(result)
        self.assertEqual(result['type'],'multi')
        self.assertEqual(result['start'],dt[0])
        self.assertEqual(result['stop'],dt[-1])
        self.assertEqual(result['N'],len(dt))
    
    
class TestMissingValues(TestCase):
    
    @classmethod
    def setUpClass(cls):
        d1 = populate('float', size = 20)
        d2 = populate('float', size = 20)
        cls.fields = {'a':d1,'b':d2}
        dates = [date(2010,1,i+1) for i in range(20)]
        d1[3] = d1[0] = d1[18] = nan
        d2[3] =  d2[9] = nan
        cls.data = [(dt,{'a':a,'b':b}) for dt,a,b in zip(dates,d1,d2)]
        cls.ColumnTS = ColumnTS
        super(TestMissingValues, cls).setUpClass()
        
    def setUp(self):
        session = self.session()
        with session.begin():
            ts1 = session.add(self.ColumnTS())
            data1 = populate
            ts1.update(self.data)
        self.ts1 = ts1
    
    def testStats(self):
        result = self.ts1.istats(0,-1)
        stats = result['stats']
        self.assertEqual(len(stats),2)
        for stat in stats:
            self.check_stats(stats[stat],self.fields[stat])
    
    
class TestColumnTSField(TestCase):
    model = ColumnTimeSeries
    
    def setUp(self):
        self.register()
        
    def testMeta(self):
        meta = self.model._meta
        self.assertTrue(len(meta.multifields),1)
        m = meta.multifields[0]
        self.assertEqual(m.name,'data')
        self.assertTrue(isinstance(m.value_pickler, encoders.Double))
        
