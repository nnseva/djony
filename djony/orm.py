#! /usr/bin/env python

from django.db.models.loading import AppCache
from django.db import models, connections
from django.conf import settings

from pony.orm import *
from pony.utils import import_module, throw
from pony.orm.dbapiprovider import Converter
from pony.converting import str2time

import datetime
import decimal

class TimeConverter(Converter):
    def validate(converter, val):
        if isinstance(val, datetime.time): return val
        if isinstance(val, basestring): return str2time(val)
        if isinstance(val, (int,long)): return datetime.time(0,0,val)
        throw(TypeError, "Attribute %r: expected type is 'time'. Got: %r" % (converter.attr, val))
    def sql2py(converter, val):
        if not isinstance(val, datetime.time): throw(ValueError,
            'Value of unexpected type received from database: instead of time got %s' % type(val))
        return val
    def sql_type(converter):
        return 'TIME'

from pony.orm.dbproviders.mysql import MySQLProvider
if not (datetime.time, TimeConverter) in MySQLProvider.converter_classes:
    MySQLProvider.converter_classes.append(
          (datetime.time, TimeConverter),
    )

PRIMITIVE_DATA_TYPES = {
    'AutoField':         lambda f,R,**kw: R(int,auto=True,**kw),
    'BooleanField':      lambda f,R,**kw: R(bool,**kw),
    'CharField':         lambda f,R,**kw: R(unicode,int(f.max_length),**kw),
    'CommaSeparatedIntegerField': lambda f,R,**kw: R(unicode,int(f.max_length),**kw),
    'DateField':         lambda f,R,**kw: R(datetime.date,**kw),
    'DateTimeField':     lambda f,R,**kw: R(datetime.datetime,**kw),
    'DecimalField':      lambda f,R,**kw: R(decimal.Decimal,scale=f.decimal_places,precision=f.max_digits,**kw),
    'FileField':         lambda f,R,**kw: R(unicode,int(f.max_length),**kw),
    'FilePathField':     lambda f,R,**kw: R(unicode,int(f.max_length),**kw),
    'FloatField':        lambda f,R,**kw: R(float,**kw),
    'IntegerField':      lambda f,R,**kw: R(int,**kw),
    'BigIntegerField':   lambda f,R,**kw: R(long,**kw),
    'IPAddressField':    lambda f,R,**kw: R(unicode,int(f.max_length),**kw),
    'NullBooleanField':  lambda f,R,**kw: R(bool,**kw),
    'PositiveIntegerField': lambda f,R,**kw: R(int,**kw),
    'PositiveSmallIntegerField': lambda f,R,**kw: R(int,**kw),
    'SlugField':         lambda f,R,**kw: R(unicode,int(f.max_length),**kw),
    'SmallIntegerField': lambda f,R,**kw: R(int,**kw),
    'TextField':         lambda f,R,**kw: R(unicode,**kw),
    'TimeField':         lambda f,R,**kw: R(datetime.time,**kw),
}

# we allow to place DJONY_PRIMITIVE_DATA_TYPES dict to settings.py
PRIMITIVE_DATA_TYPES.update(getattr(settings, 'DJONY_PRIMITIVE_DATA_TYPES', {}))

STRING_FIELD_INTERNAL_TYPES = [
    'TextField','CharField','FileField','SlugField'
] + getattr(settings, 'DJONY_STRING_FIELD_INTERNAL_TYPES', [])

MYSQL_CONVERT_ARGS = {
    'NAME':('db',str),
    'USER':('user',str),
    'PASSWORD':('passwd',str),
    'HOST':('host',str),
    'PORT':('port',int),
}

def mysql_get_args(sett):
    r = dict()
    for n in MYSQL_CONVERT_ARGS:
        k = MYSQL_CONVERT_ARGS[n][0]
        v = None
        try:
            v = MYSQL_CONVERT_ARGS[n][1](sett[n])
        except:
            pass
        if v:
            r[k] = v
    if 'OPTIONS' in sett:
        r.update(sett['OPTIONS'])
    return r

ENGINES = {
    #'sqlite3': {
    #    'provider':'sqlite',
    #},
    'mysql': {
        'provider':'mysql',
        'args_convertor':mysql_get_args,
    },
    #'postgresql_psycopg2': {
    #    'provider':'postgres',
    #},
    #'oracle': {
    #    'provider':'oracle',
    #},
}

# we allow to place DJONY_ENGINES dict to settings.py
ENGINES.update(getattr(settings, 'DJONY_ENGINES', {}))

def _get_primitive_type(f):
    return _get_primitive_type_for(type(f))

def issubclass_name(tp,nm):
    if tp.__name__ == nm:
        return True
    for b in tp.__bases__:
        if b.__name__ == nm:
            return True
        r = issubclass_name(b,nm)
        if r:
            return True
    return False

def _get_primitive_type_for(tp):
    T = None
    if tp.__name__ in PRIMITIVE_DATA_TYPES:
        T = tp.__name__
    else:
        for t in PRIMITIVE_DATA_TYPES:
            if issubclass_name(tp,t):
                T = t
                break
    if not T:
        for b in tp.__bases__:
            T = _get_primitive_type_for(b)
            if T:
                break
    return T

def get_primitive_type(f,**kwargs):
    T = _get_primitive_type(f)
    if not T:
        return
    kw = dict()
    R = Required
    if f.get_internal_type() in STRING_FIELD_INTERNAL_TYPES:
        R = Optional # Text field, special case because of explanation to issue #23
    r = None
    if f.unique:
        kw['unique'] = True
    if f.primary_key:
        R = PrimaryKey
        del kw['unique']
    if f.null:
        R = Optional
        kw['nullable'] = True
    if f.get_default() != None:
        kw['default'] = f.get_default()
    if f.primary_key and f.get_internal_type() in STRING_FIELD_INTERNAL_TYPES and not kw.get('default'):
        kw['default'] = ' '
    kw.update(kwargs)
    r = PRIMITIVE_DATA_TYPES[T](f,R,**kw)
    r.name = f.name
    return r

def get_fk_type(f,fields,db,alias,**kwargs):
    if not isinstance(f,(models.ForeignKey,models.OneToOneField)):
        return None
    my_model = f.model
    my_name = "djony_"+str(my_model._meta.app_label)+"_"+my_model.__name__
    to_model = f.rel.to
    to_name = "djony_"+str(to_model._meta.app_label)+"_"+to_model.__name__
    to_model_args = db.djony['models'].get(to_name)
    if not to_model_args:
        to_model_args = get_pony_model_args(to_model,db,alias=alias) #NOTE: recursive
    kw = dict()
    R = Required
    r = None
    if f.unique:
        kw['unique'] = True
    if f.primary_key:
        R = PrimaryKey
        del kw['unique']
    if f.null:
        R = Optional
        kw['nullable'] = True
    if f.db_column:
        kw['column'] = f.db_column
    else:
        kw['column'] = f.name + "_id"

    if not f.rel.get_related_field().primary_key:
        # special case implemented in django and not implemented in pony
        ff = f.rel.get_related_field()
        T = _get_primitive_type(ff)
        if not T:
            return
        if ff.get_internal_type() in STRING_FIELD_INTERNAL_TYPES:
            R = Optional # Text field, special case because of explanation to issue #23
        r = PRIMITIVE_DATA_TYPES[T](ff,R,**kw)
        r.name = f.name
        return r

    if f.rel.parent_link:
        # special case: inheritance
        for n in fields:
            fld = fields[n]
            if isinstance(fld,PrimaryKey):
                del fields[n]
                break

    if f.rel.related_name:
        kw['reverse'] = str(f.rel.related_name)
    elif isinstance(f,models.OneToOneField):
        kw['reverse'] = str(my_model.__name__.lower())
    else:
        kw['reverse'] = str(my_model.__name__.lower())+'_set'
    kw.update(kwargs)
    r = R(to_name,**kw)
    r.name = f.name
    O = Set
    cascade_delete = (f.rel.on_delete == models.CASCADE)

    if isinstance(f,models.OneToOneField):
        O = Optional
    related = O(my_name,reverse=f.name,cascade_delete=cascade_delete)
    related.name = kw['reverse']
    to_model_args['kw'][kw['reverse']] = related
    return r

def get_m2m_type(f,db,alias,**kwargs):
    if not isinstance(f,models.ManyToManyField):
        return None
    if not f.rel.through._meta.auto_created:
        # special case - intermediate class declared, so the m2m is implemented as two foreign keys already
        return
    my_model = f.model
    my_name = "djony_"+str(my_model._meta.app_label)+"_"+my_model.__name__
    to_model = f.rel.to
    to_name = "djony_"+str(to_model._meta.app_label)+"_"+to_model.__name__
    to_model_args = db.djony['models'].get(to_name)
    if not to_model_args:
        to_model_args = get_pony_model_args(to_model,db,alias=alias) #NOTE: recursive
    kw = dict()
    R = Set
    r = None
    kw['column'] = str(to_model.__name__.lower()) + "_id"
    kw['table'] = f.rel.through._meta.db_table

    if f.rel.related_name:
        kw['reverse'] = str(f.rel.related_name)
    else:
        kw['reverse'] = str(my_model.__name__.lower())+'_set'
    kw.update(kwargs)
    r = R(to_name,**kw)
    r.name = f.name
    O = Set
    related = O(my_name,reverse=f.name,column=str(my_model.__name__.lower()) + "_id")
    related.name = kw['reverse']
    to_model_args['kw'][kw['reverse']] = related
    return r

def get_engine_setting(alias=None):
    if not alias:
        alias = 'default'
    sett = connections.databases.get(alias)
    if not sett:
        return
    s = sett['ENGINE'].rsplit('.')[-1]
    e = {}
    e.update(ENGINES.get(s))
    e['args'] = sett
    if 'args_convertor' in e:
        e['args'] = e['args_convertor'](sett)
    return e

def get_engine(alias=None):
    e = get_engine_setting(alias)
    engine_cls = e['provider']
    if isinstance(engine_cls,basestring):
        engine_module = import_module('pony.orm.dbproviders.' + engine_cls)
        engine_cls = engine_module.provider_cls
        e['provider'] = engine_cls
    return e

def create_pony_db(alias=None):
    e = get_engine(alias)
    return Database(e['provider'],**e['args'])

def db_generate_mapping(db,alias=None):
    if not alias:
        alias = 'default'
    models = get_django_models()

    for model in models:
        get_pony_model_args(model,db,alias=alias)

    for n in db.djony['models']:
        m = db.djony['models'][n]
        t = type(n,(db.Entity,),m['kw'])
        t.__module__ = 'djony.orm.db("%s")' % alias
        if not alias or alias == 'default':
            m['model']._p = t
    db.generate_mapping(create_tables=False)

def get_pony_model_args(model,db,alias=None):
    if not hasattr(db,'djony'):
        db.djony = {
            'models':{},
        }
    name = "djony_"+str(model._meta.app_label)+"_"+model.__name__
    if name in db.djony['models']:
        return db.djony['models']
    db.djony['models'][name] = {
        'name':name,
        'bases':(db.Entity,),
        'kw':{},
        'model':model,
    }
    kw = db.djony['models'][name]['kw']
    for f in model._meta.fields:
        if f.model != model:
            continue
        t = get_primitive_type(f,column=f.db_column)
        if not t:
            t = get_fk_type(f,kw,db,alias=alias)
        if t:
            kw[f.name] = t
    for f in model._meta.many_to_many:
        if f.model != model:
            continue
        t = get_m2m_type(f,db,alias=alias)
        if t:
            kw[f.name] = t
    kw['_table_'] = model._meta.db_table
    return db.djony['models'][name]

def get_django_models():
    ac = AppCache()
    return ac.get_models()

def fix_pony_mode():
    import sys
    import pony
    if hasattr(sys,'ps1'):
        pony.MODE = 'INTERACTIVE'

from pony.utils import localbase
class Databases(localbase):
    def __init__(self):
        self.databases = {}

    def db(self,alias=None):
        if not alias:
            alias = 'default'
        if not alias in self.databases:
            self.databases[alias] = create_pony_db(alias)
            db_generate_mapping(self.databases[alias],alias)
            self.databases[alias].disconnect()
        return self.databases[alias]

    def __call__(self,alias=None):
        return self.db(alias)

db = Databases()

if not hasattr(models.base.ModelBase,'p'):
    # the p-property getter
    def p(self):
        db()
        return self._p
    models.base.ModelBase.p = property(p)
