import pymongo
import cherrypy

# We setup our global database connection
db_cfg = cherrypy.config['database']

if db_cfg['user'] == '':
    _db_uri = 'mongodb://%s:%d' % (db_cfg['host'], db_cfg['port'])
    _db_uri_redacted = _db_uri
else:
    _db_uri = 'mongodb://%s:%s@%s:%d' % (db_cfg['user'], db_cfg['password'],
                                         db_cfg['host'], db_cfg['port'])
    _db_uri_redacted = 'mongodb://%s@%s:%d' % (db_cfg['user'],
                                               db_cfg['host'], db_cfg['port'])

db_connection = pymongo.MongoClient(_db_uri)

print "Connected to MongoDB: %s" % _db_uri_redacted
