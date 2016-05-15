var constants = {
    UPLOAD_CHUNK_SIZE: 1024 * 1024 * 64, // 64MB
    SORT_ASC: 1,
    SORT_DESC: -1,
    MONTHS: [
        'January', 'February', 'March', 'April', 'May', 'June', 'July',
        'August', 'September', 'October', 'November', 'December'
    ],
    AccessType: {
        NONE: -1,
        READ: 0,
        WRITE: 1,
        ADMIN: 2
    },
    AssetstoreType: {
        FILESYSTEM: 0,
        GRIDFS: 1,
        S3: 2
    },
    Layout: {
        DEFAULT: 'default',
        EMPTY: 'empty'
    }
};

module.exports = constants;
