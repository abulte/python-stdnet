from . import ranges


class TestWhere(ranges.NumericTest):
    multipledb = True
    
    def testWhere(self):
        session = self.session()
        qs = session.query(self.model).where('this.vega > this.delta')
        self.assertTrue(qs.count())
        for m in qs:
            self.assertTrue(m.vega > m.delta)
        
    def testConcatenation(self):
        session = self.session()
        qs = session.query(self.model)
        qs = qs.filter(pv__gt=0).where('this.vega > this.delta')
        self.assertTrue(qs.count())
        for m in qs:
            self.assertTrue(m.pv > 0)
            self.assertTrue(m.vega > m.delta)
            
    def testLoadOnly(self):
        '''load only is only used in redis'''
        session = self.session()
        qs = session.query(self.model).where('this.vega > this.delta',
                                             load_only=('vega','foo','delta'))
        self.assertTrue(qs.count())
        for m in qs:
            self.assertTrue(m.vega > m.delta)