from time import sleep

from stdnet import StructureFieldError
from stdnet.utils import test, populate, zip, to_string, iteritems

from examples.models import SimpleList, Dictionary, SimpleString 

elems = populate('string', 100)


class MultiFieldMixin(object):
    '''Test class which add a couple of tests for multi fields.
You need to implement the get_object_and_field and adddata methods'''
    attrname = 'data'
    defaults = {}
    
    def setUp(self):
        self.register()
        
    def get_object_and_field(self, save=True, **kwargs):
        params = self.defaults.copy()
        params.update(kwargs)
        m = self.model(**params)
        if save:
            m.save()
        return m, getattr(m, self.attrname)
    
    def adddata(self, obj):
        raise NotImplementedError()
    
    def testRaiseStructFieldError(self):
        self.assertRaises(StructureFieldError, self.get_object_and_field, False)
    
    def testMultiFieldId(self):
        '''Here we check for multifield specific stuff like the instance
related keys (keys which are related to the instance rather than the model).'''
        # get instance and field, the field has no data here
        obj, field = self.get_object_and_field()
        # get the object id
        id = to_string(obj.id)
        # get the field database key
        field_key = to_string(field.id)
        self.assertTrue(id in field_key)
        #
        backend = obj.session.backend
        keys = backend.instance_keys(obj)
        if backend.name == 'redis':
            # field id should be in instance keys
            self.assertTrue(field.id in keys)
            lkeys = list(backend.model_keys(self.model._meta))
            # the field has no data, so there is no key in the database
            self.assertFalse(field.id in lkeys)
        #
        # Lets add data
        self.adddata(obj)
        # The field id should be in the server keys
        if backend.name == 'redis':
            lkeys = list(backend.model_keys(self.model._meta))
            self.assertTrue(field.id in lkeys)
        obj.delete()
        lkeys = list(backend.model_keys(self.model._meta))
        self.assertFalse(field.id in lkeys)


class TestStringField(MultiFieldMixin, test.CleanTestCase):
    multipledb = 'redis'
    model = SimpleString
    
    def adddata(self, li):
        '''Add elements to a list without using transactions.'''
        for elem in elems:
            li.data.push_back(elem)
        self.assertEqual(li.data.size(),len(''.join(elems)))
        
    def testIncr(self):
        m = self.model().save()
        self.assertEqual(m.data.incr(),1)
        self.assertEqual(m.data.incr(),2)
        self.assertEqual(m.data.incr(3),5)
        self.assertEqual(m.data.incr(-7),-2)
        
        
class TestListField(MultiFieldMixin, test.CleanTestCase):
    model = SimpleList
    attrname = 'names'
    
    def adddata(self, li):
        '''Add elements to a list without using transactions.'''
        with li.session.begin():
            names = li.names
            for elem in elems:
                names.push_back(elem)
        self.assertEqual(li.names.size(), len(elems))
        
    def testPushBackPopBack(self):
        li = SimpleList()
        self.assertEqual(li.id, None)
        li.save()
        names = li.names
        for elem in elems:
            names.push_back(elem)
        self.assertEqual(li.names.size(), len(elems))
        for elem in reversed(elems):
            self.assertEqual(li.names.pop_back(), elem)
        self.assertEqual(li.names.size(), 0)
        
    def testPushBack(self):
        li = SimpleList().save()
        with li.session.begin():
            names = li.names
            for elem in elems:
                names.push_back(elem)
        for el, ne in zip(elems, names):
            self.assertEqual(el, ne)
        self.assertEqual(li.names.size(), len(elems))
        
    def testPushNoSave(self):
        '''Push a new value to a list field should rise an error if the object
is not saved on databse.'''
        obj = self.model()
        push_back  = lambda : obj.names.push_back('this should fail')
        push_front = lambda : obj.names.push_front('this should also fail')
        self.assertRaises(StructureFieldError, push_back)
        self.assertRaises(StructureFieldError, push_front)
        
    def testPushFront(self):
        li = SimpleList().save()
        if li.session.backend.name == 'redis':
            names = li.names
            for elem in reversed(elems):
                names.push_front(elem)
            li.save()
            for el,ne in zip(elems,names):
                self.assertEqual(el,ne)
        
    def testPushFrontPopFront(self):
        li = SimpleList().save()
        if li.session.backend.name == 'redis':
            names = li.names
            for elem in reversed(elems):
                names.push_front(elem)
            li.save()
            self.assertEqual(li.names.size(),len(elems))
            for elem in elems:
                self.assertEqual(li.names.pop_front(),elem)
            self.assertEqual(li.names.size(),0)
        