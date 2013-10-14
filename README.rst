=======
Djony
=======

Whats new?
----------

2013-10-14:

The first release (for MySQL only a while)

Base
----

NOTE; this package has been inspired by aldjemy package.

Small package for integration Pony ORM (http://doc.ponyorm.com/)
into an existent Django (https://docs.djangoproject.com) project.
The primary use case of this package is building fast-processing
queries - 6-7 times faster than through the native Django ORM.

You need to include djony at the END (required) of `INSTALLED_APPS`. Note that
only models known in installed apps above the djony will be integrated. When models are
imported, djony will read all models and contribute `p` attribute to them.
The `p` attribute is a Pony model class (mapped to the default database)
equivalent to the correspondent Django model.

Code example::

    from djony import orm
    r = {}
    with orm.db_session:
      for u in orm.select(u for u in User.p):
        r[u.username] = {}
        for p in u.user_permissions:
         if not r[u.username].get((p.content_type.app_label,p.content_type.model)):
          r[u.username][(p.content_type.app_label,p.content_type.model)] = {}
         r[u.username][(p.content_type.app_label,p.content_type.model)][p.codename] = p.codename
    print "PERMISSIONS:",r

You can use other databases declared in the settings.py DATABASES variable.

Use orm.db(alias) to get the other database, and db.djony_<package>_<classname> members
to get access to the correspondent pony model.

Using other databases example (let the other database is identified by other_alias
in Django DATABASES settings):

    from djony import orm
    db = orm.db(other_alias)
    with orm.db_session:
      for u in orm.select(u for u in db.djony_auth_User):
        print "USERNAME:",u.username

Limitations
-----------

 - No mapping for ForeignKey(to_field=...), the correspondent attribute is converted to simple one
 - No mapping for partial database mapping (the only full one is supported)

Notes
-----

The djony is not positioned as Django ORM drop-in replacement. It's a helper for special situations.

We have some stuff in the djony cache too::

    from djony import orm
    orm.db() # The 'default' database for Pony ORM
    orm.db(other_alias) # The other_alias database for Pony ORM

You can use this stuff if you need.

Settings
--------

You can add your own primitive data types mappings for djony
using ``DJONY_PRIMITIVE_DATA_TYPES`` settings parameter. See the
``PRIMITIVE_DATA_TYPES`` in the orm.py.

You can correct list of string-based primitive field internal types
using ``DJONY_STRING_FIELD_INTERNAL_TYPES`` list.

You can add engines to use with djony using
``DJONY_ENGINES`` settings. The format is like the following:
    {
        ...
        'mysql': {
            'provider':'mysql',
            'args_convertor':mysql_get_args,
        },
    }
where the 'args_converter' is a function taking database settings dictionary
from Django and returing dictionary of pony-style keyword parameters passed
to the pony provider class constructor.
