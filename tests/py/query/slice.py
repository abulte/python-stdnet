'''Slice Query to obtain subqueries.'''
from stdnet import QuerySetError
from stdnet.utils import test

from examples.models import Instrument
from examples.data import FinanceTest


class TestFilter(FinanceTest):
    model = Instrument
    
    def setUp(self):
        self.data.create(self)
        
    def testAll(self):
        session = self.session()
        qs = session.query(self.model)
        self.assertTrue(qs.count() > 0)
        q1 = qs.all()
        self.assertEqual(len(q1),qs.count())
        
    def testUnsortedSliceSimple(self):
        session = self.session()
        qs = session.query(self.model)
        self.assertTrue(qs.count() > 0)
        q1 = qs[0:2]
        self.assertEqual(len(q1),2)
        self.assertEqual([q.id for q in q1],[1,2])
        
    def testUnsortedSliceComplex(self):
        session = self.session()
        qs = session.query(self.model)
        N = qs.count()
        self.assertTrue(N)
        q1 = qs[0:-1]
        self.assertEqual(len(q1),N-1)
        for id,q in enumerate(q1,1):
            self.assertEqual(q.id,id)
        q1 = qs[2:4]
        self.assertEqual(len(q1),2)
        self.assertEqual(q1[0].id,3)
        self.assertEqual(q1[1].id,4)
            
    def testUnsortedSliceToEnd(self):
        session = self.session()
        qs = session.query(self.model)
        N = qs.count()
        self.assertTrue(N)
        q1 = qs[0:]
        self.assertEqual(len(q1),N)
        # This time the result is sorted by ids
        q1 = qs[3:]
        self.assertEqual(len(q1),N-3)
        for id,q in enumerate(q1,4):
            self.assertEqual(q.id,id)
            
    def testSliceBack(self):
        session = self.session()
        qs = session.query(self.model)
        N = qs.count()
        self.assertTrue(N)
        q1 = qs[-2:]
        self.assertEqual(len(q1),2)
        self.assertEqual(q1[0].id,N-1)
        self.assertEqual(q1[1].id,N)
        # This time the result is sorted by ids
        q1 = qs[-2:-1]
        self.assertEqual(len(q1),1)
        self.assertEqual(q1[0].id,N-1)
        
    def testSliceGetField(self):
        '''test silve in conjunction with get_field method'''
        session = self.session()
        qs = session.query(self.model).get_field('id')
        self.assertRaises(QuerySetError, lambda: qs[:2])
    