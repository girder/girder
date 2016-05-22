var EventStream  = require('girder/utilities/EventStream');

var eventStream = new EventStream({
  // TODO: this needs to be fixed, maybe by check for an environment variable?
  // timeout: girder[sseTimeout] || null
});

module.exports = eventStream;
