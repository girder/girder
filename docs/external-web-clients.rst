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

All Girder code is packaged within ES6 modules, and may be directly included in other web
applications via
`imports <https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Statements/import>`_.
The `Webpack <https://webpack.js.org/>`_ tool is recommended as a way to resolve imports and build
deployable applications.

Extending Girder's Backbone application
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Girder defines a main application class, ``App``.  This object is responsible
for bootstrapping the application, setting up the overall layout, and responding
to global events like ``g:login`` and ``g:navigateTo``.  Developers can choose
to derive their own application from this class to use the functionality that
it provides.  For example, the following derivation would modify the normal
application bootstrapping

.. code-block:: javascript

    import Backbone from 'backbone';

    import { setCurrentUser } from '@girder/core/auth';
    import UserModel from '@girder/core/models/UserModel';
    import { setApiRoot } from '@girder/core/rest';
    import router from '@girder/core/router';
    import eventStream from '@girder/core/utilities/EventStream';
    import App from '@girder/core/views/App';

    // set the path where girder's API is mounted
    setApiRoot('/girder/api/v1');

    var MyApp = App.extend({
        start: function () {
            // disable girder's router
            router.enabled(false);

            // call the super method
            return App.prototype.start.call(this, {
                fetch: false,   // disable automatic fetching of the user model
                history: false, // disable initialization of Backbone's router
                render: false   // disable automatic rendering on start
            }).done(() => {
                // set the current user somehow
                setCurrentUser(new UserModel({...}));
                eventStream.open();

                // replace the header with a customized class
                this.headerView = new MyHeaderView({parentView: this});

                // render the main page
                this.render();

                // start up the router with the `pushState` option enabled
                Backbone.history.start({pushState: true});
            });
        }
    });

    // initialize the application without starting it
    var app = new MyApp({start: false});

    // start your application after the page loads
    $(function () {
        app.start();
    });

Other methods that one may need to override include the following:

``bindGirderEvents``
   Bind handlers to the global ``events`` object.

``render``
   Render (or re-render) the entire page.

.. note::
   ``router.enabled(false)`` must be set to false to disable URL routing
   behavior specific to the full Girder web application.

Using Girder Register and Login UI
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To use Girder UI components, you will need the following CSS file in your page:

.. code-block:: html

    <link rel="stylesheet" href="/girder/static/built/girder_lib.min.css">

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

    import { getCurrentUser, setCurrentUser } from '@girder/core/auth';
    import events from '@girder/core/events';
    import UserModel from '@girder/core/models/UserModel';
    import { restRequest } from '@girder/core/rest';
    import LoginView from '@girder/core/views/layout/LoginView';
    import RegisterView from '@girder/core/views/layout/RegisterView';

    $('#login').click(function () {
        var loginView = new LoginView({
            el: $('#dialog-container')
        });
        loginView.render();
    });

    $('#register').click(function () {
        var registerView = new RegisterView({
            el: $('#dialog-container')
        });
        registerView.render();
    });

    $('#logout').click(function () {
        restRequest({
            url: 'user/authentication',
            type: 'DELETE'
        }).done(function () {
            setCurrentUser(null);
            events.trigger('g:login');
        });
    });

    events.on('g:login', function () {
        console.log('g:login');
        var currentUser = getCurrentUser();
        if (currentUser) {
            $('#login').addClass('hidden');
            $('#register').addClass('hidden');
            $('#name').removeClass('hidden');
            $('#logout').removeClass('hidden');
            $('#name').text(currentUser.get('firstName') + ' ' + currentUser.get('lastName'));

            // Do anything else you'd like to do on login.
        } else {
            $('#login').removeClass('hidden');
            $('#register').removeClass('hidden');
            $('#name').addClass('hidden');
            $('#logout').addClass('hidden');

            // Do anything else you'd like to do on logout.
        }
    });

    // Check for who is logged in initially
    restRequest({
        url: 'user/authentication',
        error: null
    }).done(function (resp) {
        setCurrentUser(UserModel(resp.user));
        events.trigger('g:login');
    });
