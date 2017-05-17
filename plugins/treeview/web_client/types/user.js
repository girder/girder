export default function (user) {
    return {
        id: user._id,
        parent: '#users',
        type: 'user',
        text: user.login,
        model: user,
        children: true
    };
}
