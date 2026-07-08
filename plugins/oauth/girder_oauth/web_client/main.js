import './routes';

// Extends and overrides API
import './views/LoginView';
import './views/RegisterView';

const events = girder.events;

// If the current URL contains a `girderToken` query parameter, set the current token to its value
const girderToken = new URLSearchParams(window.location.search).get('girderToken');

if (girderToken) {
    // This means we have been redirected from a successful OAuth login.
    // Save the token, and delete the query parameter from the URL.
    window.localStorage.setItem('girderToken', girderToken);
    girder.auth.setCurrentToken(girderToken);

    const queryParams = new URLSearchParams(window.location.search);
    queryParams.delete('girderToken');
    window.location.search = queryParams.toString();
}

const error = new URLSearchParams(window.location.search).get('error');
if (error) {
    window.localStorage.setItem('oauthError', error);
    const queryParams = new URLSearchParams(window.location.search);
    queryParams.delete('error');
    window.location.search = queryParams.toString();
}

events.on('g:appload.after', function() {
    const error = window.localStorage.getItem('oauthError');
    if (error) {
        var alertText = `OAuth login failed: ${error}`;
        if (error === 'accountApproval') {
            alertText = 'Your account is pending approval by an administrator.';
        }
        setTimeout(() => {
            events.trigger('g:alert', {
                text: alertText,
                type: 'danger',
            });
        }, 100);
        window.localStorage.removeItem('oauthError');
    };
});
