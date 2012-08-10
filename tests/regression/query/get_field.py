from stdnet import test
from stdnet.utils import populate, zip, is_string

from examples.models import Instrument, Position, ObjectAnalytics,\
                             AnalyticData, Group, Fund
from examples.data import FinanceTest, DataTest, data_generator, INSTS_TYPES,\
                            CCYS_TYPES


class TestInstrument(FinanceTest):
    model = Instrument
    
    def setUp(self):
        self.data.create(self)
        
    def testName(self):
        session = self.session()
        qb = session.query(self.model).all()
        qs = session.query(self.model).get_field('name')
        self.assertEqual(qs._get_field,'name')
        result = qs.all()
        self.assertTrue(result)
        for r in result:
            self.assertTrue(is_string(r))
            
    def testId(self):
        session = self.session()
        qb = session.query(self.model).all()
        qs = session.query(self.model).get_field('id')
        self.assertEqual(qs._get_field,'id')
        result = qs.all()
        self.assertTrue(result)
        for r in result:
            self.assertTrue(isinstance(r,int))
            
            
class TestRelated(FinanceTest):
    model = Position
    
    def setUp(self):
        self.data.makePositions(self)
        
    def testInstrument(self):
        session = self.session()
        qs = session.query(self.model).get_field('instrument')
        self.assertEqual(qs._get_field,'instrument')
        result = qs.all()
        self.assertTrue(result)
        for r in result:
            self.assertTrue(type(r),int)
        
    def testFilter(self):
        session = self.session()
        qs = session.query(self.model).get_field('instrument')
        qi = session.query(Instrument).filter(id__in = qs)
        inst = qi.all()
        ids = qs.all()
        self.assertTrue(inst)
        self.assertTrue(len(ids) >= len(inst))
        idset = set(ids)
        self.assertEqual(len(idset),len(inst))
        self.assertEqual(idset,set((i.id for i in inst)))
        
        
class generator(data_generator):
    sizes = {'tiny': (2,10),
             'small': (5,30),
             'normal': (10,50),
             'big': (30,200),
             'huge': (100,1000)}
    
    def generate(self):
        group_len, obj_len = self.size
        self.inames = populate('string', obj_len, min_len=5, max_len=20)
        self.itypes = populate('choice', obj_len, choice_from=INSTS_TYPES)
        self.iccys = populate('choice', obj_len, choice_from=CCYS_TYPES)
        self.gnames = populate('string', group_len, min_len=5, max_len=20)
    
    def create(self, test):
        with test.session().begin() as t:
            for name, typ, ccy in zip(self.inames, self.itypes, self.iccys):
                t.add(Instrument(name=name, type=typ, ccy=ccy))
            for name in self.gnames:
                t.add(Group(name=name))
            for name, ccy in zip(self.inames, self.iccys):
                t.add(Fund(name=name, ccy=ccy))
        with test.session().begin() as t:
            for i in test.session().query(Instrument).load_only('id'):
                t.add(ObjectAnalytics(model_type=Instrument, object_id=i.id))
            for i in test.session().query(Fund).load_only('id'):
                t.add(ObjectAnalytics(model_type=Fund, object_id=i.id))
    
class TestModelField(DataTest):
    '''Test the get_field method when applied to ModelField'''
    models = (ObjectAnalytics, AnalyticData, Group, Instrument, Fund)
    data_cls = generator
    
    def setUp(self):
        self.data.create(self)
    
    def testLoad(self):
        session = self.session()
        q = session.query(ObjectAnalytics)\
                   .filter(model_type=Instrument).get_field('id')
        i = session.query(Instrument).filter(id=q)
        self.assertEqual(i.count(), session.query(Instrument).count())
        
    def testLoadMissing(self):
        session = self.session()
        session.query(Instrument).filter(id=(1,2,3)).delete()
        q = session.query(ObjectAnalytics)\
                   .filter(model_type=Instrument).get_field('id')
        i = session.query(Instrument).filter(id=q).all()
        
        