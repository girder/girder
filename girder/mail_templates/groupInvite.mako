<%include file="_header.mako"/>

<p>Hello ${userToInvite['firstName']},</p>

<p>
<b>${user['firstName']} ${user['lastName']} (${user['login']})</b> has invited
you to join the <b>${group['name']}</b> group! To join the group,
<a href="${host}#group/${group['_id']}">click here</a> and then click
"Join group".
</p>

<%include file="_footer.mako"/>
