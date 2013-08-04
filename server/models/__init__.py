import pymongo
import cherrypy

db_cfg = cherrypy.config['database']
db_connection = pymongo.MongoClient(db_cfg['host'], db_cfg['port'])

print "Connected to MongoDB on %s:%d" % (db_cfg['host'], db_cfg['port'])
