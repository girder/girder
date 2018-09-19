import { getCurrentUser } from 'girder/auth';

export default function () {
    const user = getCurrentUser();
    if (user) {
        return user.attributes;
    }
}
