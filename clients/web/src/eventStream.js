import EventStream  from 'girder/utilities/EventStream';

export var eventStream = new EventStream({
  // TODO: this needs to be fixed, maybe by check for an environment variable?
  // timeout: girder[sseTimeout] || null
});
