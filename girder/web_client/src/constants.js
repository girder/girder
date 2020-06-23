const SORT_ASC = 1;
const SORT_DESC = -1;

const MONTHS = [
    'January', 'February', 'March', 'April', 'May', 'June', 'July',
    'August', 'September', 'October', 'November', 'December'
];

const AccessType = {
    NONE: -1,
    READ: 0,
    WRITE: 1,
    ADMIN: 2
};

const AssetstoreType = {
    FILESYSTEM: 0,
    GRIDFS: 1,
    S3: 2
};

const Layout = {
    DEFAULT: 'default',
    EMPTY: 'empty'
};

export {
    SORT_ASC, SORT_DESC,
    MONTHS,
    AccessType,
    AssetstoreType,
    Layout
};
