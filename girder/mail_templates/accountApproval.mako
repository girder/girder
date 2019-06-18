<%include file="_header.mako"/>

<p>Someone has registered a new account that needs admin approval.</p>

<p>Login: ${user.get('login')}</p>
<p>Email: ${user.get('email')}</p>
<p>Name: ${user.get('firstName')} ${user.get('lastName')}</p>

<p><a href="${url}">${url}</a></p>

<%include file="_footer.mako"/>
