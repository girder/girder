import cherrypy
import json

from .. import base

def setUpModule():
    base.startServer()

def tearDownModule():
    base.stopServer()

class UserTestCase(base.TestCase):
    def testRegisterAndLogin(self):
        """
        Test user registration and logging in.
        """
        params = {
            'email' : 'bad_email',
            'login' : 'illegal@login',
            'firstName' : 'First',
            'lastName' : 'Last',
            'password' : 'bad'
        }
        # First test all of the required parameters.
        self.ensureRequiredParams(path='/user', method='POST', required=params.keys())

        # Now test parameter validation
        resp = self.request(path='/user', method='POST', params=params)
        self.assertStatus(resp, 400)
        self.assertEqual('Login may not have an "@" character.', resp.json['message'])

        params['login'] = 'goodlogin'
        resp = self.request(path='/user', method='POST', params=params)
        self.assertStatus(resp, 400)
        self.assertEqual(cherrypy.config['users']['password_description'], resp.json['message'])

        params['password'] = 'goodpassword'
        resp = self.request(path='/user', method='POST', params=params)
        self.assertStatus(resp, 400)
        self.assertEqual('Invalid email address.', resp.json['message'])

        # Now successfully create the user
        params['email'] = 'good@email.com'
        resp = self.request(path='/user', method='POST', params=params)
        self.assertStatusOk(resp)
        self.assertHasKeys(resp.json, ['_id', 'firstName', 'lastName', 'email', 'login',
                                       'admin', 'size', 'hashAlg'])
        self.assertNotHasKeys(resp.json, ['salt'])

        # Now that our user is created, try to login
        params = {
            'login' : 'incorrect@email.com',
            'password' : 'badpassword'
        }
        self.ensureRequiredParams(path='/user/login', method='POST', required=params.keys())

        # Login with unregistered email
        resp = self.request(path='/user/login', method='POST', params=params)
        self.assertStatus(resp, 403)
        self.assertEqual('Login failed.', resp.json['message'])

        # Correct email, but wrong password
        params['login'] = 'good@email.com'
        resp = self.request(path='/user/login', method='POST', params=params)
        self.assertStatus(resp, 403)
        self.assertEqual('Login failed.', resp.json['message'])

        # Login successfully with email
        params['password'] = 'goodpassword'
        resp = self.request(path='/user/login', method='POST', params=params)
        self.assertStatus(resp, 200)

        # Invalid login
        params['login'] = 'badlogin'
        resp = self.request(path='/user/login', method='POST', params=params)
        self.assertStatus(resp, 403)
        self.assertEqual('Login failed.', resp.json['message'])

        # Login successfully with login
        params['login'] = 'goodlogin'
        resp = self.request(path='/user/login', method='POST', params=params)
        self.assertStatus(resp, 200)

        # Make sure we got a nice cookie
        self.assertTrue(resp.cookie.has_key('authToken'))
        cookieVal = json.loads(resp.cookie['authToken'].value)
        self.assertHasKeys(cookieVal, ['token', 'userId'])
        self.assertEqual(resp.cookie['authToken']['expires'],
                         cherrypy.config['sessions']['cookie_lifetime'] * 3600 * 24)
