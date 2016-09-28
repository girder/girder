import $ from 'jquery';
import _ from 'underscore';

import accessEditorNonModalTemplate from 'girder/templates/widgets/accessEditorNonModal.pug';
import accessEditorTemplate from 'girder/templates/widgets/accessEditor.pug';
import accessEntryTemplate from 'girder/templates/widgets/accessEntry.pug';
import GroupModel from 'girder/models/GroupModel';
import LoadingAnimation from 'girder/views/widgets/LoadingAnimation';
import SearchFieldWidget from 'girder/views/widgets/SearchFieldWidget';
import UserModel from 'girder/models/UserModel';
import View from 'girder/views/View';
import { AccessType } from 'girder/constants';
import { handleClose, handleOpen } from 'girder/dialog';

import 'girder/stylesheets/widgets/accessWidget.styl';

import 'bootstrap/js/tooltip';

import 'girder/utilities/jquery/girderModal';

/**
 * This view allows users to see and control access on a resource.
 */
var AccessWidget = View.extend({
    events: {
        'click button.g-save-access-list': function (e) {
            $(e.currentTarget).attr('disabled', 'disabled');
            this.saveAccessList();
        },
        'click a.g-action-remove-access': 'removeAccessEntry',
        'change .g-public-container .radio input': 'privacyChanged'
    },

    /**
     * @param settings.modelType {string} Display name for the resource type
     *    being edited.
     * @param [settings.hideRecurseOption=false] {bool} Whether to hide the recursive
     *    propagation setting widgets.
     * @param [settings.hideSaveButton=false] {bool} Whether to hide the "save"
     *    button in non-modal view. This allows for users of this widget to
     *    provide their own save button elsewhere on the page that can call the
     *    saveAccessList() method of this widget when pressed.
     * @param [settings.modal=true] {bool} Whether to render the widget as a
     *    modal dialog or not.
     */
    initialize: function (settings) {
        this.modelType = settings.modelType;
        this.hideRecurseOption = settings.hideRecurseOption || false;
        this.hideSaveButton = settings.hideSaveButton || false;
        this.modal = _.has(settings, 'modal') ? settings.modal : true;

        this.searchWidget = new SearchFieldWidget({
            placeholder: 'Start typing a name...',
            modes: ['prefix', 'text'],
            types: ['group', 'user'],
            parentView: this
        }).on('g:resultClicked', this.addEntry, this);

        if (this.model.get('access')) {
            this.render();
        } else {
            this.model.on('g:accessFetched', function () {
                this.render();
            }, this).fetchAccess();
        }
    },

    render: function () {
        if (!this.model.get('access')) {
            new LoadingAnimation({
                el: this.$el,
                parentView: this
            }).render();
            return;
        }

        var closeFunction;
        if (this.modal && this.modelType === 'folder') {
            handleOpen('folderaccess');
            closeFunction = function () {
                handleClose('folderaccess');
            };
        } else if (this.modal) {
            handleOpen('access');
            closeFunction = function () {
                handleClose('access');
            };
        }

        var template = this.modal ? accessEditorTemplate
                                  : accessEditorNonModalTemplate;
        this.$el.html(template({
            model: this.model,
            modelType: this.modelType,
            publicFlag: this.model.get('public'),
            hideRecurseOption: this.hideRecurseOption,
            hideSaveButton: this.hideSaveButton
        }));

        if (this.modal) {
            this.$el.girderModal(this).on('hidden.bs.modal', closeFunction);
        }

        _.each(this.model.get('access').groups, function (groupAccess) {
            this.$('#g-ac-list-groups').append(accessEntryTemplate({
                accessTypes: AccessType,
                type: 'group',
                entry: _.extend(groupAccess, {
                    title: groupAccess.name,
                    subtitle: groupAccess.description
                })
            }));
        }, this);

        _.each(this.model.get('access').users, function (userAccess) {
            this.$('#g-ac-list-users').append(accessEntryTemplate({
                accessTypes: AccessType,
                type: 'user',
                entry: _.extend(userAccess, {
                    title: userAccess.name,
                    subtitle: userAccess.login
                })
            }));
        }, this);

        this._makeTooltips();

        this.searchWidget.setElement(this.$('.g-search-field-container')).render();

        this.privacyChanged();

        return this;
    },

    _makeTooltips: function () {
        this.$('.g-action-remove-access').tooltip({
            placement: 'bottom',
            animation: false,
            delay: {show: 100}
        });
    },

    /**
     * Add a new user or group entry to the access control list UI. If the
     * given user or group already has an entry there, this does nothing.
     */
    addEntry: function (entry) {
        this.searchWidget.resetState();
        if (entry.type === 'user') {
            this._addUserEntry(entry);
        } else if (entry.type === 'group') {
            this._addGroupEntry(entry);
        }
    },

    _addUserEntry: function (entry) {
        var exists = false;
        _.every(this.$('.g-user-access-entry'), function (el) {
            if ($(el).attr('resourceid') === entry.id) {
                exists = true;
            }
            return !exists;
        }, this);

        if (!exists) {
            var model = new UserModel();
            model.set('_id', entry.id).on('g:fetched', function () {
                this.$('#g-ac-list-users').append(accessEntryTemplate({
                    accessTypes: AccessType,
                    type: 'user',
                    entry: {
                        title: model.name(),
                        subtitle: model.get('login'),
                        id: entry.id,
                        level: AccessType.READ
                    }
                }));

                this._makeTooltips();
            }, this).fetch();
        }
    },

    _addGroupEntry: function (entry) {
        var exists = false;
        _.every(this.$('.g-group-access-entry'), function (el) {
            if ($(el).attr('resourceid') === entry.id) {
                exists = true;
            }
            return !exists;
        }, this);

        if (!exists) {
            var model = new GroupModel();
            model.set('_id', entry.id).on('g:fetched', function () {
                this.$('#g-ac-list-groups').append(accessEntryTemplate({
                    accessTypes: AccessType,
                    type: 'group',
                    entry: {
                        title: model.name(),
                        subtitle: model.get('description'),
                        id: entry.id,
                        level: AccessType.READ
                    }
                }));

                this._makeTooltips();
            }, this).fetch();
        }
    },

    saveAccessList: function () {
        // Rebuild the access list
        var acList = {
            users: [],
            groups: []
        };

        _.each(this.$('.g-group-access-entry'), function (el) {
            var $el = $(el);
            acList.groups.push({
                name: $el.find('.g-desc-title').html(),
                id: $el.attr('resourceid'),
                level: parseInt(
                    $el.find('.g-access-col-right>select').val(),
                    10
                )
            });
        }, this);

        _.each(this.$('.g-user-access-entry'), function (el) {
            var $el = $(el);
            acList.users.push({
                login: $el.find('.g-desc-subtitle').html(),
                name: $el.find('.g-desc-title').html(),
                id: $el.attr('resourceid'),
                level: parseInt(
                    $el.find('.g-access-col-right>select').val(),
                    10
                )
            });
        }, this);

        this.model.set({
            access: acList,
            public: this.$('#g-access-public').is(':checked')
        });

        var recurse = this.$('#g-apply-recursive').is(':checked');

        this.model.off('g:accessListSaved')
                  .on('g:accessListSaved', function () {
                      if (this.modal) {
                          this.$el.modal('hide');
                      }

                      this.trigger('g:accessListSaved', {
                          recurse: recurse
                      });
                  }, this).updateAccess({
                      recurse: recurse,
                      progress: true
                  });
    },

    removeAccessEntry: function (event) {
        var sel = '.g-user-access-entry,.g-group-access-entry';
        $(event.currentTarget).tooltip('hide').parents(sel).remove();
    },

    privacyChanged: function () {
        this.$('.g-public-container .radio').removeClass('g-selected');
        var selected = this.$('.g-public-container .radio input:checked');
        selected.parents('.radio').addClass('g-selected');
    }
});

export default AccessWidget;
