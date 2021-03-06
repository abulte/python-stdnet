from stdnet.utils import test
from stdnet.utils.populate import populate
from stdnet.utils.py2py3 import zip

from examples.models import NumericData
from examples.data import data_generator


class NumberGenerator(data_generator):
    
    def generate(self, **kwargs):
        self.d1 = populate('integer', self.size, start=-5, end=5)
        self.d2 = populate('float', self.size, start=-10, end=10)
        self.d3 = populate('float', self.size, start=-10, end=10)
        self.d4 = populate('float', self.size, start=-10, end=10)
        self.d5 = populate('integer', self.size, start=-5, end=5)
        self.d6 = populate('integer', self.size, start=-5, end=5)
        
        
class NumericTest(test.TestCase):
    multipledb = ['redis', 'mongo']
    data_cls = NumberGenerator
    models = (NumericData,)

    @classmethod
    def setUpClass(cls):
        super(NumericTest, cls).setUpClass()
        cls.data = cls.data_cls(size=cls.size)
        cls.register()
        yield cls.clear_all()
        session = cls.session()
        d = cls.data
        with session.begin() as t:
            for a, b, c, d, e, f in zip(d.d1, d.d2, d.d3, d.d4, d.d5, d.d6):
                t.add(cls.model(pv=a, vega=b, delta=c, gamma=d,
                                data={'test': {'': e,
                                               'inner': f}}))
    
    @classmethod
    def tearDownClass(cls):
        yield cls.clear_all()
        

class TestNumericRange(NumericTest):
                
    def testGT(self):
        session = self.session()
        qs = session.query(NumericData).filter(pv__gt=1)
        self.assertTrue(qs)
        for v in qs:
            self.assertTrue(v.pv > 1)
        qs = session.query(NumericData).filter(pv__gt=-2)
        self.assertTrue(qs)
        for v in qs:
            self.assertTrue(v.pv > -2)
    
    def testGE(self):
        session = self.session()
        qs = session.query(NumericData).filter(pv__ge=-2)
        self.assertTrue(qs)
        for v in qs:
            self.assertTrue(v.pv >= -2)
        qs = session.query(NumericData).filter(pv__ge=0)
        self.assertTrue(qs)
        for v in qs:
            self.assertTrue(v.pv >= 0)
            
    def testLT(self):
        session = self.session()
        qs = session.query(NumericData).filter(pv__lt=2)
        self.assertTrue(qs)
        for v in qs:
            self.assertTrue(v.pv < 2)
        qs = session.query(NumericData).filter(pv__lt=-1)
        self.assertTrue(qs)
        for v in qs:
            self.assertTrue(v.pv < -1)
            
    def testLE(self):
        session = self.session()
        qs = session.query(NumericData).filter(pv__le=1)
        self.assertTrue(qs)
        for v in qs:
            self.assertTrue(v.pv <= 1)
        qs = session.query(NumericData).filter(pv__le=-1)
        self.assertTrue(qs)
        for v in qs:
            self.assertTrue(v.pv <= -1)
            
    def testMix(self):
        session = self.session()
        qs = session.query(NumericData).filter(pv__gt=1, pv__lt=0)
        self.assertFalse(qs)
        qs = session.query(NumericData).filter(pv__ge=-2, pv__lt=3)
        self.assertTrue(qs)
        for v in qs:
            self.assertTrue(v.pv < 3)
            self.assertTrue(v.pv >= -2)
        
    def testMoreThanOne(self):
        session = self.session()
        qs = session.query(NumericData).filter(pv__ge=-2, pv__lt=3)\
                                       .filter(vega__gt=0)
        self.assertTrue(qs)
        for v in qs:
            self.assertTrue(v.pv < 3)
            self.assertTrue(v.pv >= -2)
            self.assertTrue(v.vega > 0)
    
    def testWithString(self):
        session = self.session()
        qs = session.query(NumericData).filter(pv__ge='-2')
        self.assertTrue(qs)
        for v in qs:
            self.assertTrue(v.pv >= -2)
        
    def testJson(self):
        session = self.session()
        qs = session.query(NumericData).filter(data__test__gt=1)
        self.assertTrue(qs)
        for v in qs:
            self.assertTrue(v.data__test > 1)
        qs = session.query(NumericData).filter(data__test__gt='-2')
        self.assertTrue(qs)
        for v in qs:
            self.assertTrue(v.data__test > -2)
        qs = session.query(NumericData).filter(data__test__inner__gt='1')
        self.assertTrue(qs)
        for v in qs:
            self.assertTrue(v.data__test__inner > 1)
        qs = session.query(NumericData).filter(data__test__inner__gt=-2)
        self.assertTrue(qs)
        for v in qs:
            self.assertTrue(v.data__test__inner > -2)
            
    