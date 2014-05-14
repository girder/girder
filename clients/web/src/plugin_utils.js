/**
 * Wrap the prototype method of a given object.
 *
 * @param obj The object whose prototype to extend, e.g. girder.views.MyView
 * @param funcName The name of the function to wrap, e.g. "render"
 * @param wrapper The wrapper function, which should be a function taking the
 *     underlying wrapped function as its first argument. The wrapped function
 *     should be called with .call(this[, arguments]) inside of the wrapper in
 *     order to preserve "this" semantics.
 */
girder.wrap = function (obj, funcName, wrapper) {
    obj.prototype[funcName] = _.wrap(obj.prototype[funcName], wrapper);
};
