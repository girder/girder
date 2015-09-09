def load(info):
    info['config']['/jquery'] = {
        'tools.staticdir.on': True,
        'tools.staticdir.dir': 'clients/jquery'
    }
