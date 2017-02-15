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
import { getCurrentUser } from 'girder/auth';
import { AccessType } from 'girder/constants';
import { handleClose, handleOpen } from 'girder/dialog';
import { restRequest } from 'girder/rest';

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
        'click .g-close-flags-popover': function (e) {
            $(e.currentTarget).parents('.g-access-action-container')
                .find('.g-action-manage-flags').popover('hide');
        },
        'click .g-close-public-flags-popover': function (e) {
            $(e.currentTarget).parents('.g-public-container')
                .find('.g-action-manage-public-flags').popover('hide');
        },
        'click a.g-action-remove-access': 'removeAccessEntry',
        'change .g-public-container .radio input': 'privacyChanged',
        'change .g-flag-checkbox': '_toggleAccessFlag',
        'change .g-public-flag-checkbox': '_togglePublicAccessFlag'
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
        this.currentUser = getCurrentUser();
        this.isAdmin = !!(this.currentUser && this.currentUser.get('admin'));

        this.searchWidget = new SearchFieldWidget({
            placeholder: 'Start typing a name...',
            modes: ['prefix', 'text'],
            types: ['group', 'user'],
            parentView: this
        }).on('g:resultClicked', this.addEntry, this);

        var flagListPromise = restRequest({
            path: 'system/access_flag'
        }).done((resp) => {
            this.flagList = resp;
        });

        $.when(
            flagListPromise,
            this.model.fetchAccess()
        ).then(() => {
            this.render();
        });
    },

    render: function () {
        if (!this.model.get('access') || !this.flagList) {
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
            _,
            model: this.model,
            modelType: this.modelType,
            publicFlag: this.model.get('public'),
            publicFlags: this.model.get('publicFlags'),
            hideRecurseOption: this.hideRecurseOption,
            hideSaveButton: this.hideSaveButton,
            flagList: this.flagList,
            isAdmin: this.isAdmin
        }));

        if (this.modal) {
            this.$el.girderModal(this).on('hidden.bs.modal', closeFunction);
        }

        _.each(this.model.get('access').groups, function (groupAccess) {
            this.$('#g-ac-list-groups').append(accessEntryTemplate({
                _,
                accessTypes: AccessType,
                type: 'group',
                flagList: this.flagList,
                isAdmin: this.isAdmin,
                entry: _.extend(groupAccess, {
                    title: groupAccess.name,
                    subtitle: groupAccess.description
                })
            }));
        }, this);

        _.each(this.model.get('access').users, function (userAccess) {
            this.$('#g-ac-list-users').append(accessEntryTemplate({
                _,
                accessTypes: AccessType,
                type: 'user',
                flagList: this.flagList,
                isAdmin: this.isAdmin,
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
        this.$('.g-access-action-container a,.g-tooltip').tooltip({
            placement: 'bottom',
            animation: false,
            delay: {show: 100}
        });

        this.$('.g-flag-label span').tooltip({
            placement: 'bottom'
        });

        // Re-binding popovers actually breaks them, so we make sure to
        // only bind ones that aren't already bound.
        _.each(this.$('.g-action-manage-flags'), el => {
            if (!$(el).data('bs.popover')) {
                $(el).popover({
                    trigger: 'manual',
                    html: true,
                    placement: 'left',
                    viewport: {
                        selector: 'body',
                        padding: 10
                    },
                    content: function () {
                        return $(this).parent().find('.g-flags-popover-container').html();
                    }
                }).click(function () {
                    $(this).popover('toggle');
                });
            }
        });

        // Re-binding popovers actually breaks them, so we make sure to
        // only bind ones that aren't already bound.
        _.each(this.$('.g-action-manage-public-flags'), el => {
            if (!$(el).data('bs.popover')) {
                $(el).popover({
                    trigger: 'manual',
                    html: true,
                    placement: 'right',
                    viewport: {
                        selector: 'body',
                        padding: 10
                    },
                    content: function () {
                        return $(this).parent().find('.g-public-flags-popover-container').html();
                    }
                }).click(function () {
                    $(this).popover('toggle');
                });
            }
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
                    _,
                    accessTypes: AccessType,
                    type: 'user',
                    entry: {
                        title: model.name(),
                        subtitle: model.get('login'),
                        id: entry.id,
                        level: AccessType.READ
                    },
                    isAdmin: this.isAdmin,
                    flagList: this.flagList
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
                    _,
                    accessTypes: AccessType,
                    type: 'group',
                    entry: {
                        title: model.name(),
                        subtitle: model.get('description'),
                        id: entry.id,
                        level: AccessType.READ
                    },
                    isAdmin: this.isAdmin,
                    flagList: this.flagList
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

        var publicFlags = _.map(this.$('.g-public-flag-checkbox:checked'), checkbox => {
            return $(checkbox).attr('flag');
        });

        _.each(this.$('.g-group-access-entry'), function (el) {
            var $el = $(el);
            acList.groups.push({
                name: $el.find('.g-desc-title').html(),
                id: $el.attr('resourceid'),
                level: parseInt(
                    $el.find('.g-access-col-right>select').val(),
                    10
                ),
                flags: _.map($el.find('.g-flag-checkbox:checked'), (checkbox) => {
                    return $(checkbox).attr('flag');
                })
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
                ),
                flags: _.map($el.find('.g-flag-checkbox:checked'), (checkbox) => {
                    return $(checkbox).attr('flag');
                })
            });
        }, this);

        this.model.set({
            access: acList,
            public: this.$('#g-access-public').is(':checked'),
            publicFlags: publicFlags
        });

        var recurse = this.$('#g-apply-recursive').is(':checked');

        this.model.off('g:accessListSaved', null, this)
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

        if (this.$('#g-access-public').is(':checked')) {
            this.$('.g-action-manage-public-flags').removeClass('hide');
        } else {
            this.$('.g-action-manage-public-flags').addClass('hide');
        }
    },

    _toggleAccessFlag: function (e) {
        var el = $(e.currentTarget),
            type = el.attr('resourcetype'),
            id = el.attr('resourceid'),
            flag = el.attr('flag');

        // Since we clicked in a cloned popover element, we must apply this
        // change within the original element as well.
        this.$(`.g-flags-popover-container[resourcetype='${type}'][resourceid='${id}']`)
            .find(`.g-flag-checkbox[flag="${flag}"]`)
            .attr('checked', el.is(':checked') ? 'checked' : null);
    },

    _togglePublicAccessFlag: function (e) {
        var el = $(e.currentTarget),
            flag = el.attr('flag');

        // Since we clicked in a cloned popover element, we must apply this
        // change within the original element as well.
        this.$('.g-public-flags-popover-container')
            .find(`.g-public-flag-checkbox[flag="${flag}"]`)
            .attr('checked', el.is(':checked') ? 'checked' : null);
    }
});

export default AccessWidget;
