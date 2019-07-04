/* Convert a number of bytes to a value and units.  The units are the
 * powers of 1024.  For instance, 4096 will result in (4, 1).
 * @param sizeValue: number of bytes to convert.  If this is falsy, an
 *                   empty string is returned.
 * @return .sizeValue: the new size value.  This may be an empty string.
 * @return .sizeUnits: the size units (0-based powers of 1024). */
function sizeToValueAndUnits(sizeValue) {
    var sizeUnits = 0;
    if (sizeValue) {
        for (sizeUnits = 0; sizeUnits < 4 && parseInt(sizeValue / 1024, 10) *
                1024 === sizeValue; sizeUnits += 1) {
            sizeValue /= 1024;
        }
    } else {
        sizeValue = '';
    }
    return { sizeUnits: sizeUnits, sizeValue: sizeValue };
}

/* Convert a number and units to a number of bytes.  The units can either
 * be included as a suffix for the number or are the power of 1024.
 * @param sizeValue: an integer, empty string, or a string with a floating
 *                   point number followed by an SI prefix.
 * @param sizeUnits: the size units (0-based powers of 1024).  Ignored if
 *                   units are given in the string.
 * @return sizeBytes: the number of bytes specified, or the empty string
 *                    for none. */
function valueAndUnitsToSize(sizeValue, sizeUnits) {
    var sizeBytes = sizeValue;
    var match, i, suffixes = 'bkMGT';
    if (parseFloat(sizeValue) > 0) {
        sizeBytes = parseFloat(sizeValue);
        /* parse suffix */
        match = sizeValue.match(
            new RegExp('^\\s*[0-9.]+\\s*([' + suffixes + '])', 'i'));
        if (match && match.length > 1) {
            for (sizeUnits = 0; sizeUnits < suffixes.length;
                sizeUnits += 1) {
                if (match[1].toLowerCase() ===
                        suffixes[sizeUnits].toLowerCase()) {
                    break;
                }
            }
        }
        for (i = 0; i < parseInt(sizeUnits, 10); i += 1) {
            sizeBytes *= 1024;
        }
        sizeBytes = parseInt(sizeBytes, 10);
    }
    return sizeBytes;
}

export {
    sizeToValueAndUnits,
    valueAndUnitsToSize
};
