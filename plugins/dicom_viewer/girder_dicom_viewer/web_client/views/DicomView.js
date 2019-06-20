import _ from 'underscore';
import daikon from 'daikon';
import vtkImageSlice from 'vtk.js/Sources/Rendering/Core/ImageSlice';
import vtkImageData from 'vtk.js/Sources/Common/DataModel/ImageData';
import vtkDataArray from 'vtk.js/Sources/Common/Core/DataArray';
import vtkImageMapper from 'vtk.js/Sources/Rendering/Core/ImageMapper';
import vtkInteractorStyleImage from 'vtk.js/Sources/Interaction/Style/InteractorStyleImage';
import vtkOpenGLRenderWindow from 'vtk.js/Sources/Rendering/OpenGL/RenderWindow';
import vtkRenderer from 'vtk.js/Sources/Rendering/Core/Renderer';
import vtkRenderWindow from 'vtk.js/Sources/Rendering/Core/RenderWindow';
import vtkRenderWindowInteractor from 'vtk.js/Sources/Rendering/Core/RenderWindowInteractor';

import { restRequest } from '@girder/core/rest';
import FileModel from '@girder/core/models/FileModel';
import FileCollection from '@girder/core/collections/FileCollection';
import View from '@girder/core/views/View';

import DicomItemTemplate from '../templates/dicomItem.pug';
import '../stylesheets/dicomItem.styl';
import DicomSliceMetadataTemplate from '../templates/dicomSliceMetadata.pug';
import '../stylesheets/dicomSliceMetadata.styl';

const DicomFileModel = FileModel.extend({
    getSlice: function () {
        if (!this._slice) {
            // Cache the slice on the model
            this._slice = restRequest({
                url: `file/${this.id}/download`,
                xhrFields: {
                    responseType: 'arraybuffer'
                }
            })
                .then((resp) => {
                    const dataView = new DataView(resp);
                    return daikon.Series.parseImage(dataView);
                });
        }
        return this._slice;
    }
});

const DicomFileCollection = FileCollection.extend({
    model: DicomFileModel,

    initialize: function () {
        FileCollection.prototype.initialize.apply(this, arguments);

        this._selectedIndex = null;
    },

    sortField: 'none',

    selectIndex: function (index) {
        this._selectedIndex = index;
        this.trigger('g:selected', this.at(index), index);
    },

    selectNext: function () {
        let newIndex = this._selectedIndex + 1;
        if (newIndex >= this.length) {
            newIndex = 0;
        }
        this.selectIndex(newIndex);
    },

    selectPrevious: function () {
        let newIndex = this._selectedIndex - 1;
        if (newIndex < 0) {
            newIndex = this.length - 1;
        }
        this.selectIndex(newIndex);
    },

    selectFirst: function () {
        this.selectIndex(0);
    },

    selectLast: function () {
        this.selectIndex(this.length - 1);
    }
});

const DicomSliceMetadataWidget = View.extend({
    className: 'g-dicom-tags',

    initialize: function (settings) {
        this._slice = null;
    },

    /**
     * Set the slice to use.
     *
     * `render` should typically be called afterwards.
     *
     * @param {daikon.Image} slice
     */
    setSlice: function (slice) {
        this._slice = slice;
        return this;
    },

    /**
     * Do a full render.
     *
     * May be called without calling `setSlice` first.
     */
    render: function () {
        this.$el.html(DicomSliceMetadataTemplate({
            tags: this._slice ? this._getSliceTags() : []
        }));
        return this;
    },

    _getSliceTags: function () {
        let tags;
        if (!DicomSliceMetadataWidget.tagCache.has(this._slice)) {
            tags = this._extractSliceTags();
            DicomSliceMetadataWidget.tagCache.set(this._slice, tags);
        } else {
            return DicomSliceMetadataWidget.tagCache.get(this._slice);
        }
        return tags;
    },

    _extractSliceTags: function () {
        return _.chain(this._slice.tags)
            .filter((tag) => {
                // Redact tags that have unprintable values
                return (
                    !tag.sublist &&
                    tag.vr !== 'SQ' &&
                    !tag.isPixelData() &&
                    tag.value &&
                    tag.value.toString() !== '[object DataView]'
                );
            })
            .map((tag) => {
                // Transform to a list of tag (name / value) objects
                return {
                    name: daikon.Dictionary.getDescription(tag.group, tag.element),
                    value: tag.value
                };
            })
            .filter((tag) => {
                // Redact private and meta-tag tags
                return (
                    tag.name !== 'PrivateData' &&
                    !(tag.name.startsWith('Group') && tag.name.endsWith('Length'))
                );
            })
            .sortBy((tag) => {
                return tag.name.toLowerCase();
            })
            .value();
    }
}, {
    tagCache: new WeakMap()
});

const DicomSliceImageWidget = View.extend({
    className: 'g-dicom-image',

    initialize: function (settings) {
        this._slice = null;
        this.vtk = {
            renderer: null,
            actor: null,
            camera: null,
            interactor: null
        };
    },

    destroy: function () {
        if (this.vtk.interactor) {
            this.vtk.interactor.unbindEvents(this.el);
        }
        View.prototype.destroy.apply(this, arguments);
    },

    /**
     * Set the slice to use.
     *
     * `render` or `rerenderSlice` should typically be called afterwards.
     *
     * @param {daikon.Image} slice
     */
    setSlice: function (slice) {
        this._slice = slice;
        return this;
    },

    /**
     * Do a full render.
     *
     * May be called without calling `setSlice` first.
     */
    render: function () {
        this.vtk.renderer = vtkRenderer.newInstance();
        this.vtk.renderer.setBackground(0.33, 0.33, 0.33);

        const renWin = vtkRenderWindow.newInstance();
        renWin.addRenderer(this.vtk.renderer);

        const glWin = vtkOpenGLRenderWindow.newInstance();
        glWin.setContainer(this.el);
        glWin.setSize(512, 512);
        renWin.addView(glWin);

        this.vtk.interactor = vtkRenderWindowInteractor.newInstance();
        const style = vtkInteractorStyleImage.newInstance();
        this.vtk.interactor.setInteractorStyle(style);
        this.vtk.interactor.setView(glWin);

        this.vtk.actor = vtkImageSlice.newInstance();
        this.vtk.renderer.addActor(this.vtk.actor);

        if (this._slice) {
            const mapper = vtkImageMapper.newInstance();
            mapper.setInputData(this._getImageData());
            this.vtk.actor.setMapper(mapper);
        }

        this.vtk.camera = this.vtk.renderer.getActiveCameraAndResetIfCreated();

        this.vtk.interactor.initialize();
        this.vtk.interactor.bindEvents(this.el);
        this.vtk.interactor.start();

        this.autoLevels(false);
        this.autoZoom(false);
        this.vtk.interactor.render();

        return this;
    },

    /**
     * Cheaply update the rendering, usually after `setSlice` is called.
     */
    rerenderSlice: function () {
        if (this.vtk.renderer) {
            if (this._slice) {
                const mapper = vtkImageMapper.newInstance();
                mapper.setInputData(this._getImageData());
                this.vtk.actor.setMapper(mapper);
            }
            this.vtk.interactor.render();
        } else {
            this.render();
        }
        return this;
    },

    /**
     * Requires `render` to be called first.
     */
    autoLevels: function (rerender = true) {
        const range = this._getImageData().getPointData().getScalars().getRange();
        const ww = range[1] - range[0];
        const wc = (range[0] + range[1]) / 2;
        this.vtk.actor.getProperty().setColorWindow(ww);
        this.vtk.actor.getProperty().setColorLevel(wc);

        if (rerender) {
            this.vtk.interactor.render();
        }
        return this;
    },

    /**
     * Requires `render` to be called first.
     */
    autoZoom: function (rerender = true) {
        this.vtk.renderer.resetCamera();
        this.vtk.camera.zoom(1.44);

        const up = [0, -1, 0];
        const pos = this.vtk.camera.getPosition();
        pos[2] = -Math.abs(pos[2]);
        this.vtk.camera.setViewUp(up[0], up[1], up[2]);
        this.vtk.camera.setPosition(pos[0], pos[1], pos[2]);

        if (rerender) {
            this.vtk.interactor.render();
        }
        return this;
    },

    /**
     * Requires `render` to be called first.
     */
    zoomIn: function () {
        this.vtk.camera.zoom(9 / 8);
        this.vtk.interactor.render();
        return this;
    },

    /**
     * Requires `render` to be called first.
     */
    zoomOut: function () {
        this.vtk.camera.zoom(8 / 9);
        this.vtk.interactor.render();
        return this;
    },

    _getImageData: function () {
        let tags;
        if (!DicomSliceImageWidget.imageDataCache.has(this._slice)) {
            tags = this._extractImageData();
            DicomSliceImageWidget.imageDataCache.set(this._slice, tags);
        } else {
            return DicomSliceImageWidget.imageDataCache.get(this._slice);
        }
        return tags;
    },

    _extractImageData: function () {
        const rows = this._slice.getRows();
        const cols = this._slice.getCols();
        const rowSpacing = this._slice.getPixelSpacing()[0];
        const colSpacing = this._slice.getPixelSpacing()[1];

        const imageData = vtkImageData.newInstance();
        imageData.setOrigin(0, 0, 0);
        imageData.setSpacing(colSpacing, rowSpacing, 1);
        imageData.setExtent(0, cols - 1, 0, rows - 1, 0, 0);

        const values = this._slice.getInterpretedData();
        const dataArray = vtkDataArray.newInstance({values: values});
        imageData.getPointData().setScalars(dataArray);

        return imageData;
    }
}, {
    imageDataCache: new WeakMap()
});

const DicomItemView = View.extend({
    className: 'g-dicom-view',

    events: {
        'input .g-dicom-slider': _.debounce(function (event) {
            this._files.selectIndex(parseInt(event.target.value));
        }, 10),
        'click .g-dicom-first': function (event) {
            this._files.selectFirst();
        },
        'click .g-dicom-previous': function (event) {
            this._files.selectPrevious();
        },
        'click .g-dicom-play': function (event) {
            this.play();
        },
        'click .g-dicom-pause': function (event) {
            this.pause();
        },
        'click .g-dicom-next': function (event) {
            this._files.selectNext();
        },
        'click .g-dicom-last': function (event) {
            this._files.selectLast();
        },
        'click .g-dicom-zoom-in': function (event) {
            this._sliceImageView.zoomIn();
        },
        'click .g-dicom-zoom-out': function (event) {
            this._sliceImageView.zoomOut();
        },
        'click .g-dicom-reset-zoom': function (event) {
            this._sliceImageView.autoZoom();
        },
        'click .g-dicom-auto-levels': function (event) {
            this._sliceImageView.autoLevels();
        }
    },

    /**
     *
     * @param {ItemModel} settings.item An item with its `dicom` attribute set.
     */
    initialize: function (settings) {
        this._files = new DicomFileCollection(settings.item.get('dicom').files);

        this._sliceMetadataView = null;
        this._sliceImageView = null;

        this._playing = false;
        this._playInterval = settings.playInterval || 500;

        this.listenTo(this._files, 'g:selected', this._onSelectionChanged);
    },

    render: function () {
        this.$el.html(DicomItemTemplate({
            files: this._files
        }));

        this._sliceMetadataView = new DicomSliceMetadataWidget({
            el: this.$('.g-dicom-tags'),
            parentView: this
        });
        this._sliceImageView = new DicomSliceImageWidget({
            el: this.$('.g-dicom-image'),
            parentView: this
        });

        this._files.selectFirst();

        return this;
    },

    _onSelectionChanged: function (selectedFile, selectedIndex) {
        this._toggleControls(false);

        selectedFile.getSlice()
            .done((slice) => {
                this.$('.g-dicom-filename').text(selectedFile.name()).attr('title', selectedFile.name());
                this.$('.g-dicom-slider').val(selectedIndex);

                this._sliceMetadataView
                    .setSlice(slice)
                    .render();
                this._sliceImageView
                    .setSlice(slice)
                    .rerenderSlice();
            })
            .always(() => {
                this._toggleControls(true);
            });
    },

    _toggleControls: function (enable) {
        // This does not disable the "input" slider, as that interferes with dragging usability
        this.$('.g-dicom-controls button').girderEnable(enable);
    },

    play: function () {
        if (this._playing) {
            // Increase the play rate
            this._playInterval *= 0.5;
            return;
        }

        this._playing = true;
        this.step();
    },

    step: function () {
        if (this._playing) {
            this._files.selectNext();
            setTimeout(_.bind(this.step, this), this._playInterval);
        }
    },

    pause: function () {
        this._playing = false;
        this._playInterval = 500;
    }
});

export default DicomItemView;
