var SORT_ASC = 1;
var SORT_DESC = -1;

var MONTHS = [
    'January', 'February', 'March', 'April', 'May', 'June', 'July',
    'August', 'September', 'October', 'November', 'December'
];

var AccessType = {
    NONE: -1,
    READ: 0,
    WRITE: 1,
    ADMIN: 2
};

var AssetstoreType = {
    FILESYSTEM: 0,
    GRIDFS: 1,
    S3: 2
};

var Layout = {
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
