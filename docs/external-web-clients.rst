External Web Clients
====================

You may want to build your own custom web applications using Girder. Since
Girder cleanly separates API from UI, it is straightforward to use a mounted
Girder API for app authentication and data storage. You may additionally
use Girder's JavaScript libraries and UI templates to assist in building
applications.


Including the Girder REST API
-----------------------------

Apache
^^^^^^

See the :ref:`deploy` section for instructions on deployment of Girder under
Apache. You may host your web application alongside Girder and use its
REST interface.

Tangelo
^^^^^^^

`Tangelo <http://tangelo.kitware.com>`_ is a CherryPy based web server framework
for rapid data analytics and visualization application development.
Tangelo has options for directly mounting the Girder API and static application
files inside a Tangelo instance. See details in Tangelo's
`setup <https://tangelo.readthedocs.org/en/latest/setup.html>`_ documentation.


Using Girder JavaScript Utilities and Views
-------------------------------------------

Including the JavaScript
^^^^^^^^^^^^^^^^^^^^^^^^

Use the following to include the Girder libraries in your web application,
assuming Girder is hosted at ``/girder``:

.. code-block:: html

    <script src="/girder/static/built/girder.ext.min.js"></script>
    <script src="/girder/static/built/girder.app.min.js"></script>

.. note::
   ``girder.ext.min.js`` includes requirements for Girder, including jQuery,
   Bootstrap, Underscore, and Backbone. You may wish to use your own versions
   of these separately and not include ``girder.ext.min.js``.


Extending Girder's Backbone application
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Girder defines a top-level class at ``girder.App``.  This object is responsible
for bootstraping the application, setting up the overall layout, and responding
to global events like ``g:login`` and ``g:navigateTo``.  Developers can choose
to derive their own application from this class to use the functionality that
it provides.  For example, the following derivation would modify the normal
application bootstrapping

.. code-block:: javascript

   // set the path where girder's API is mounted
   girder.apiRoot = '/girder/api/v1';

   var App = girder.App.extend({
      start: function () {

         // disable girder's router
         girder.router.enabled(false);

         // call the super method
         return girder.App.prototype.start.call(this, {
             fetch: false,  // disable automatic fetching of the user model
             history: false,// disable initialization of Backbone's router
             render: false  // disable automatic rendering on start
         }).then(_.bind(function () {

            // set the current user somehow
            girder.currentUser = new girder.models.UserModel({...});
            girder.eventStream.open();

            // replace the header with a customized class
            this.headerView = new MyHeaderView({parentView: this});

            // render the main page
            this.render();

            // start up the router with the `pushState` option enabled
            Backbone.history.start({pushState: true});
         }, this));
      }
   });

   // initialize the application without starting it
   var app = new App({start: false});

   // start your application after the page loads
   $(document).ready(function () {
      app.start();
   });

Other methods that one may need to override include the following:

``bindGirderEvents``
   Bind handlers to the global ``girder.events`` object.

``render``
   Render (or re-render) the entire page.

.. note::
   ``girder.router.enabled(false)`` must be set to false to disable URL routing
   behavior specific to the full Girder web application.

Using Girder Register and Login UI
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To use Girder UI components, you will need the following CSS files in your HTML:

.. code-block:: html

    <link rel="stylesheet" href="/girder/static/built/girder.ext.min.css">
    <link rel="stylesheet" href="/girder/static/built/girder.app.min.css">

.. note::
   ``girder.ext.min.css`` includes requirements for Girder, including Bootstrap
   and some additional Bootstrap extensions. You may wish to use your own
   versions of these separately and not include ``girder.ext.min.css``.

To make login and logout controls, provide a dialog container and
login/logout/register links, and a container where the dialogs will be rendered:

.. code-block:: html

    <button class="btn btn-link" id="login" href="#">Login</button>
    <button class="btn btn-link" id="register" href="#">Register</button>
    <label class="hidden" id="name" href="#"></label>
    <button class="btn btn-link hidden" id="logout" href="#">Logout</button>
    <div class="modal fade" id="dialog-container"></div>

In your JavaScript, perform callbacks such as the following:

.. code-block:: javascript

    $('#login').click(function () {
        var loginView = new girder.views.LoginView({
            el: $('#dialog-container')
        });
        loginView.render();
    });

    $('#register').click(function () {
        var registerView = new girder.views.RegisterView({
            el: $('#dialog-container')
        });
        registerView.render();
    });

    $('#logout').click(function () {
        girder.restRequest({
            path: 'user/authentication',
            type: 'DELETE'
        }).done(function () {
            girder.currentUser = null;
            girder.events.trigger('g:login');
        });
    });

    girder.events.on('g:login', function () {
        console.log("g:login");
        if (girder.currentUser) {
            $("#login").addClass("hidden");
            $("#register").addClass("hidden");
            $("#name").removeClass("hidden");
            $("#logout").removeClass("hidden");
            $("#name").text(girder.currentUser.get('firstName') + " " + girder.currentUser.get('lastName'));

            // Do anything else you'd like to do on login.
        } else {
            $("#login").removeClass("hidden");
            $("#register").removeClass("hidden");
            $("#name").addClass("hidden");
            $("#logout").addClass("hidden");

            // Do anything else you'd like to do on logout.
        }
    });

    // Check for who is logged in initially
    girder.restRequest({
        path: 'user/authentication',
        error: null
    }).done(function (resp) {
        girder.currentUser = new girder.models.UserModel(resp.user);
        girder.events.trigger('g:login');
    });

You can find an example minimal application using Girder's login and register
dialogs in the source tree at **/clients/web-external**.
