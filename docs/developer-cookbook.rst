Developer Cookbook
==================

This cookbook consists of a set of examples of common tasks that developers may
encounter when developing Girder applications.

Client cookbook
---------------

The following examples are for common tasks that would be performed by a Girder
client application.

Authenticating to the web API
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Clients can make authenticated web API calls by passing a secure temporary token
with their requests. Tokens are obtained via the login process; the standard
login process requires the client to make an HTTP ``GET`` request to the
``api/v1/user/authentication`` route, using HTTP Basic Auth to pass the user
credentials. For example, for a user with login "john" and password "hello",
first base-64 encode the string ``"john:hello"`` which yields ``"am9objpoZWxsbw=="``.
Then take the base-64 encoded value and pass it via the ``Girder-Authorization``
header (The ``Authorization`` header will also work): ::

    Girder-Authorization: Basic am9objpoZWxsbw==

If the username and password are correct, you will receive a 200 status code and
a JSON document from which you can extract the authentication token, e.g.:

.. code-block:: javascript

    {
      "authToken": {
        "token": "urXQSHO8aF6cLB5si0Ch0WCiblvW1m8YSFylMH9eqN1Mt9KvWUnghVDKQy545ZeA",
        "expires": "2015-04-11 00:06:14.598570"
      },
      "message": "Login succeeded.",
      "user": {
        ...
      }
    }

The ``authToken.token`` string is the token value you should pass in subsequent API
calls, which should either be passed as the ``token`` parameter in the query or
form parameters, or as the value of a custom HTTP header with the key ``Girder-Token``, e.g. ::

    Girder-Token: urXQSHO8aF6cLB5si0Ch0WCiblvW1m8YSFylMH9eqN1Mt9KvWUnghVDKQy545ZeA

.. note:: When logging in, the token is also sent to the client in a Cookie header so that web-based
   clients can persist its value conveniently for its duration. However, for security
   reasons, merely passing the cookie value back is not sufficient for authentication.

.. note:: If you are using Girder's JavaScript web client library in a CORS environment,
   be sure to set ``girder.corsAuth = true;`` in your application prior to calling
   ``girder.login``. This will allow users' login sessions to be saved on the origin
   site's cookie.

.. _upload-a-file:

Upload a file
^^^^^^^^^^^^^

If you are using the Girder javascript client library, you can simply call the ``upload``
method of the ``girder.models.FileModel``. The first argument is the parent model
object (an ``ItemModel`` or ``FolderModel`` instance) to upload into, and the second
is a browser ``File`` object that was selected via a file input element. You can
bind to several events of that model, as in the example below.

.. code-block:: javascript

    var fileModel = new girder.models.FileModel();
    fileModel.on('g:upload.complete', function () {
        // Called when the upload finishes
    }).on('g:upload.chunkSent', function (info) {
        // Called on each chunk being sent
    }).on('g:upload.progress', function (info) {
        // Called regularly with progress updates
    }).on('g:upload.error', function (info) {
        // Called if an upload fails partway through sending the data
    }).on('g:upload.errorStarting', function (info) {
        // Called if an upload fails to start
    });
    fileModel.upload(parentFolder, fileObject);

If you don't feel like making your own upload interface, you can simply use
the ``girder.views.UploadWidget`` to provide a nice GUI interface for uploading.
It will prompt the user to drag and drop or browse for files, and then shows
a current and overall progress bar and also provides controls for resuming a
failed upload.

Using the Girder upload widget in a custom app
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Your custom javascript application can easily reuse the existing upload
widget provided in the Girder javascript library if you don't want to write your
own upload view. This can save time spent duplicating functionality, since the
upload widget provides current and overall progress bars, file displays, a
drag-and-droppable file selection button, resume behavior in failure conditions, and
customizable hooks for various stages of the upload process.

The default behavior of the upload widget is to display as a modal dialog, but
many users will want to simply embed it underneath a normal DOM element flow.
The look and behavior of the widget can be customized when the widget is instantiated
by passing in options like so:

.. code-block:: javascript

    new girder.views.UploadWidget({
        option: value,
        ...
    });

The following options are not required, but may be used to modify the behavior
of the widget:

    * ``[parent]`` - If the parent object is known when instantiating this
      upload widget, pass the object here.
    * ``[parentType=folder]`` - If the parent type is known when instantiating this
      upload widget, pass the object here. Otherwise set ``noParent: true`` and
      set it later, prior to starting the upload.
    * ``[noParent=false]`` - If the parent object being uploaded into is not known
      at the time of widget instantiation, pass ``noParent: true``. Callers must
      ensure that the parent is set by the time ``uploadNextFile()`` actually gets called.
    * ``[title="Upload files"]`` - Title for the widget. This is highly recommended
      when rendering as a modal dialog. To disable rendering of the title, simply
      pass a falsy object.
    * ``[modal=true]`` - This widget normally renders as a modal dialog. Pass
      ``modal: false`` to disable the modal behavior and simply render underneath a
      parent element.
    * ``[overrideStart=false]`` - Some callers will want to hook into the pressing
      of the start upload button and add their own logic prior to actually sending
      the files. To do so, set ``overrideStart: true`` and bind to the ``g:uploadStarted``
      event of this widget. The caller is then responsible for calling ``uploadNextFile()``
      on the widget when they have completed their actions and are ready to actually
      send the files.

For general documentation on embedding Girder widgets in a custom application,
see the section on :ref:`client development <client_development_js>`.

Server cookbook
---------------

The following examples refer to tasks that are executed by the Girder application
server.

Creating a REST route
^^^^^^^^^^^^^^^^^^^^^

The process of creating new REST resources and routes is documented
:ref:`here <extending-the-api>`.

The API docs of the ``route`` method can be found
`here <api-docs.html#girder.api.rest.Resource.route>`__.

Loading a resource by its ID
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This is a fundamental element of many REST operations; they receive a parameter
representing a resource's unique ID, and want to load the corresponding resource
from that ID. This behavior is known as model loading. As a brief example, if
we had the ID of a folder within our REST route handler, and wanted to load its
corresponding document from the database, it would look like:

.. code-block:: python

    self.model('folder').load(theFolderId, user=self.getCurrentUser(), level=AccessType.READ)

The `load <api-docs.html#girder.models.model_base.AccessControlledModel.load>`__
method of each model class takes the resource's unique ID as its
first argument (this is the ``_id`` field in the documents). For access controlled
models like the above example, it also requires the developer to specify
which user is requesting the loading of the resource, and what access level is required
on the resource. If the ID passed in does not correspond to a record in the database,
``None`` is returned.

Sometimes models need to be loaded outside the context of being
requested by a specific user, and in those cases the ``force`` flag should be used:

.. code-block:: python

    self.model('folder').load(theFolderId, force=True)

If you need to load a model that is in a plugin rather than a core model, pass
the plugin name as the second argument to the ``model`` method:

.. code-block:: python

    self.model('cat', 'cats').load(...)

The `ModelImporter <api-docs.html#girder.utility.model_importer.ModelImporter>`__ class
conveniently exposes a method for retrieving instances of models that are statically
cached for efficient reuse. You can mix this class into any of your classes to
enable ``self.model`` semantics. The ``ModelImporter.model`` method is
static, so you can also just do the following anywhere:

.. code-block:: python

    ModelImporter.model('folder')...

Send a raw/streaming HTTP response body
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For consistency, the default behavior of a REST endpoint in Girder is to take
the return value of the route handler and encode it in the format specified
by the client in the ``Accepts`` header, usually ``application/json``. However,
in some cases you may want to force your endpoint to send a raw response body
back to the client. A common example would be downloading a file from the server;
we want to send just the data, not try to encode it in JSON.

If you want to send a raw response, simply make your route handler return a
generator function. In Girder, a raw response is also automatically a streaming
response, giving developers full control of the buffer size of the response
body. That is, each time you ``yield`` data in your generator function, the
buffer will be flushed to the client. As a minimal example, the following
route handler would send 10 chunks to the client, and the full response
body would be ``0123456789``.

.. code-block:: python

    from girder.api import access

    @access.public
    def rawExample(self, params):
        def gen():
            for i in range(10):
                yield str(i)
        return gen

Serving a static file
^^^^^^^^^^^^^^^^^^^^^

If you are building a plugin that needs to serve up a static file from a path
on disk, you can make use of the ``staticFile`` utility, as in the following
example:

.. code-block:: python

    import os
    from girder.utility.server import staticFile

    def load(info):
        path = os.path.join(PLUGIN_ROOT_DIR, 'static', 'index.html')
        info['serverRoot'].static_route = staticFile(path)

The ``staticFile`` utility should be assigned to the route corresponding to
where the static file should be served from.

.. note:: If a relative path is passed to ``staticFile``, it will be interpreted
  relative to the current working directory, which may vary. If your static
  file resides within your plugin, it is recommended to use the special
  ``PLUGIN_ROOT_DIR`` property of your server module, or the equivalent
  ``info['pluginRootDir']`` value passed to the ``load`` method.

Sending Emails
^^^^^^^^^^^^^^

Girder has a utility module that make it easy to send emails from the server. For
the sake of maintainability and reusability of the email content itself, emails are stored
as `Mako templates <http://www.makotemplates.org/>`_ in the
**girder/mail_templates** directory. By convention, email templates should
include ``_header.mako`` above and ``_footer.mako`` below the content. If you wish
to send an email from some point within the application, you can use the
utility functions within ``girder.utility.mail_utils``, as in the example
below: ::

    from girder.utility import mail_utils

    ...

    def my_email_sending_code():
        html = mail_utils.renderTemplate('myContentTemplate.mako', {
            'param1': 'foo',
            'param2': 'bar'
        })
        mail_utils.sendEmail(to=email, subject='My mail from Girder', text=html)

If you wish to send email from within a plugin, simply create a
**server/mail_templates** directory within your plugin, and it will be
automatically added to the mail template search path when your plugin is loaded.
To avoid name collisions, convention dictates that mail templates within your
plugin should be prefixed by your plugin name, e.g.,
``my_plugin.my_template.mako``.

If you want to send email to all of the site administrators, there is a
convenience keyword argument for that. Rather than setting the ``to`` field,
pass ``toAdmins=True``.

.. code-block:: python

    mail_utils.sendEmail(toAdmins=True, subject='...', text='...')

.. note:: All emails are sent as rich text (``text/html`` MIME type).

Logging a Message
^^^^^^^^^^^^^^^^^

Girder application servers maintain an error log and an information log and expose
a utility module for sending events to them. Any 500 error that occurs during
execution of a request will automatically be logged in the error log with a
full stack trace. Also, any 403 error (meaning a user who is logged in but
requests access to a resource that they don't have permission to access) will also be logged
automatically. All log messages automatically include a timestamp, so there
is no need to add your own.

If you want to log your own custom error or info messages outside of those default
behaviors, use the following examples:

.. code-block:: python

    from girder import logger

    try:
        ...
    except Exception:
        # Will log the most recent exception, including a traceback, request URL,
        # and remote IP address. Should only be called from within an exception handler.
        logger.exception('A descriptive message')

    # Will log a message to the info log.
    logger.info('Test')

Adding Automated Tests
^^^^^^^^^^^^^^^^^^^^^^

The server side Python tests are run using
`unittest <https://docs.python.org/2/library/unittest.html>`_. All of the actual
test cases are stored under `tests/cases`.

**Adding to an Existing Test Case**

If you want to add tests to an existing test case, just create a new function
in the relevant TestCase class. The function name must start with **test**. If
the existing test case has **setUp** or **tearDown** methods, be advised that
those methods will be run before and after *each* of the test methods in the
class.

**Creating a New Test Case**

To create an entirely new test case, create a new file in **cases** that ends
with **_test.py**. To start off, put the following code in the module (with
appropriate class name of course):

.. code-block:: python

    from .. import base

    def setUpModule():
        base.startServer()

    def tearDownModule():
        base.stopServer()

    class MyTestCase(base.TestCase):

.. note:: If your test case does not need to communicate with the server, you
   do not need to call **base.startServer()** and **base.stopServer()** in the
   **setUpModule()** and **tearDownModule()** functions. Those functions are called
   once per module rather than once per test method.

Then, in the **MyTestCase** class, just add functions that start with **test**,
and they will automatically be run by unittest.

Finally, you'll need to register your test in the `CMakeLists.txt` file in the
`tests` directory. Just add a line like the ones already there at the bottom.
For example, if the test file you created was called `thing_test.py`, you would
add:

.. code-block:: cmake

    add_python_test(thing)

Re-run CMake in the build directory, and then run CTest, and your test will be
run.

.. note:: By default, **add_python_test** allows the test to be run in parallel
   with other tests, which is normally fine since each python test has its own
   assetstore space and its own mongo database, and the server is typically
   mocked rather than actually binding to its port. However, some tests (such
   as those that actually start the cherrypy server) should not be run concurrently
   with other tests that use the same resource. If you have such a test, use the
   ``RESOURCE_LOCKS`` argument to **add_python_test**. If your test requires the
   cherrypy server to bind to its port, declare that it locks the ``cherrypy``
   resource. If it also makes use of the database, declare that it locks the
   ``mongo`` resource. For example: ::

       add_python_test(my_test RESOURCE_LOCKS cherrypy mongo)

Serving a custom app from the server root
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Normally, the root node (``/``) of the server will serve up the Girder web client.
Some plugins will wish to change this so that their own custom app gets served out of
the server root instead, and they may also want to move the Girder web client to
be served out of an alternative route so they can still use it in addition to
their custom front-end application.

To achieve this, you simply have to swap the existing server root with your own
and rebind the old app underneath. In your plugin's ``load`` method, you would
add something like the following:

.. code-block:: python

    info['serverRoot'], info['serverRoot'].girder = CustomAppRoot(), info['serverRoot']

This will make it so that ``/`` serves your ``CustomAppRoot``, and ``/girder`` will
serve the normal Girder web client. That also has the side effect of moving the
web API (normally ``/api``) as well; it would now be moved to ``/girder/api``, which
would require a change to the ``server.api_root`` value in ``girder.local.cfg``.

If you would rather your web API remained at ``/api`` instead of moving under
``/girder/api``, you would simply have to move it underneath the new server root. To
do that, just add the following line below the previous line:

.. code-block:: python

    info['serverRoot'].api = info['serverRoot'].girder.api

This will now serve the api out of *both* ``/api`` and ``/girder/api``, which
may be desirable. If you only want it to be served out of ``/api`` and not
``/girder/api``, just add a final line below that:

.. code-block:: python

    del info['serverRoot'].girder.api

Supporting web browser operations where custom headers cannot be set
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Some aspects of the web browser make it infeasible to pass the usual
``Girder-Token`` authentication header when making a request. For example,
if using an ``EventSource`` object for SSE, or when you must redirect the user's
browser to a download endpoint that serves its content as an attachment.

In such cases, you may allow specific REST API routes to authenticate using the
Cookie. To avoid vulnerabilities to Cross-Site Request Forgery attacks, you
should only do this if the endpoint is "read-only" (that is, the endpoint does
not make modifications to data on the server). Accordingly, only routes for
``HEAD`` and ``GET`` requests allow cookie authentication to be enabled (without
an additional override).

In order to allow cookie authentication for your route, simply add the
``cookie`` decorator to your route handler function. Example:

.. code-block:: python

    from girder.api import access

    @access.cookie
    @access.public
    def download(self, params):
        ...

As a last resort, if your endpoint is not read-only and you are unable to pass
the ``Girder-Token`` header to it, you can pass a ``token`` query parameter
containing the token , but in practice this will probably never be the case.
