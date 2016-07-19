import _ from 'underscore';
import Backbone from 'backbone';

import EventStream from 'girder/utilities/EventStream';

var events = _.clone(Backbone.Events);

var eventStream = new EventStream({
  // TODO: this needs to be fixed, maybe by check for an environment variable?
  // timeout: girder[sseTimeout] || null
});

export {
  events,
  eventStream
};
