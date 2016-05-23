export var UPLOAD_CHUNK_SIZE = 1024 * 1024 * 64; // 64MB

export var SORT_ASC = 1;
export var SORT_DESC = -1;

export var MONTHS = [
    'January', 'February', 'March', 'April', 'May', 'June', 'July',
    'August', 'September', 'October', 'November', 'December'
];

export var AccessType = {
    NONE: -1,
    READ: 0,
    WRITE: 1,
    ADMIN: 2
};

export var AssetstoreType = {
    FILESYSTEM: 0,
    GRIDFS: 1,
    S3: 2
};

export var Layout = {
    DEFAULT: 'default',
    EMPTY: 'empty'
};
