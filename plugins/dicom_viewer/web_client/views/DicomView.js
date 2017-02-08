import ViewTemplate from '../templates/view.pug';
import TagsTemplate from '../templates/tags.pug';
import '../stylesheets/dicom_viewer.styl';

import { restRequest, apiRoot } from 'girder/rest';
import View from 'girder/views/View';

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

var DicomView = View.extend({
    events: {
        'click .dicom-zoom-in': function (event) {
            event.preventDefault();
            this.camera.zoom(9 / 8);
            this.iren.render();
        },
        'click .dicom-zoom-out': function (event) {
            event.preventDefault();
            this.camera.zoom(8 / 9);
            this.iren.render();
        },
        'click .dicom-reset-zoom': function (event) {
            event.preventDefault();
            this.autoZoom();
            this.iren.render();
        },
        'click .dicom-first': function (event) {
            event.preventDefault();
            this.setIndex(0);
        },
        'click .dicom-previous': function (event) {
            event.preventDefault();
            this.previous();
        },
        'click .dicom-next': function (event) {
            event.preventDefault();
            this.next();
        },
        'click .dicom-last': function (event) {
            event.preventDefault();
            this.setIndex(this.files.length - 1);
        },
        'click .dicom-play': function (event) {
            event.preventDefault();
            this.play();
        },
        'click .dicom-pause': function (event) {
            event.preventDefault();
            this.pause();
        },
        'click .dicom-auto-levels': function (event) {
            event.preventDefault();
            this.autoLevels();
            this.iren.render();
        },
        'input .dicom-slider': _.debounce(function (event) {
            this.setIndex(event.target.value);
        }, 10)
    },

    initialize: function (settings) {
        this.item = settings.item;
        this.files = [];
        this.index = 0;
        this.first = true;
        this.playing = false;
        this.playRate = settings.playRate || 500;
        this.imageData = null;
        this.imageDataCache = {};
        this.tagCache = {};
        this.xhr = null;
        this.loadFileList();
    },

    setIndex: function (index) {
        if (index < 0 || index >= this.files.length) {
            return;
        }
        this.index = parseInt(index);
        this.loadFile(this.files[index]);
        this.$('.dicom-slider').val(index);
    },

    next: function () {
        if (this.index === this.files.length - 1) {
            this.setIndex(0);
        } else {
            this.setIndex(this.index + 1);
        }
    },

    previous: function () {
        if (this.index === 0) {
            this.setIndex(this.files.length - 1);
        } else {
            this.setIndex(this.index - 1);
        }
    },

    play: function () {
        if (this.playing) {
            this.playRate *= 0.5;
            return;
        }
        this.playing = true;
        this.step();
    },

    step: function () {
        if (this.playing) {
            this.next();
            setTimeout(this.step.bind(this), this.playRate);
        }
    },

    pause: function () {
        this.playing = false;
        this.playRate = 500;
    },

    loadFileList: function () {
        restRequest({
            path: '/item/' + this.item.get('_id') + '/dicom',
            data: {
                // don't need the dicom tags, just want the sorted results
                filters: 'dummy'
            }
        }).done(_.bind(function (resp) {
            this.handleFileList(resp);
        }, this));
    },

    handleFileList: function (files) {
        this.files = files;
        var slider = this.$('.dicom-slider')[0];
        slider.min = 0;
        slider.max = this.files.length - 1;
        slider.step = 1;
        this.setIndex(0);
    },

    loadFile: function (file) {
        if (file.name in this.imageDataCache) {
            this.showCached(file);
            return;
        }
        if (this.xhr) {
            this.xhr.abort();
        }
        const xhr = new XMLHttpRequest();
        xhr.open('GET', apiRoot + '/file/' + file._id + '/download', true);
        xhr.responseType = 'arraybuffer';
        xhr.onload = _.bind(function (event) {
            try {
                const dataView = new DataView(xhr.response);
                const image = daikon.Series.parseImage(dataView);
                const imageData = createImageData(image);
                this.imageDataCache[file.name] = imageData;
                this.tagCache[file.name] = this.getTags(image);
                this.showCached(file);
            } catch (e) {
                console.log(e);
            }
        }, this);
        xhr.send();
        this.xhr = xhr;
    },

    getTags: function (image) {
        const result = [];
        const tags = image.tags;
        const keys = Object.keys(tags).sort();
        for (let key of keys) {
            const tag = tags[key];
            const name = daikon.Dictionary.getDescription(tag.group, tag.element);

            if (name === 'PrivateData') {
                continue;
            }
            if (name.startsWith('Group') && name.endsWith('Length')) {
                continue;
            }

            if (tag.sublist) {
                continue;
            } else if (tag.vr === 'SQ') {
                continue;
            } else if (tag.isPixelData()) {
                continue;
            } else if (!tag.value) {
                continue;
            }

            const value = tag.value;

            if (value.toString() === '[object DataView]') {
                continue;
            }

            result.push(_.extend({}, {key: key, name: name, value: value}));
        }
        result.sort(function (a, b) {
            a = a.name.toLowerCase();
            b = b.name.toLowerCase();
            return a.localeCompare(b);
        });
        return result;
    },

    showCached: function (file) {
        this.$('.dicom-filename').text(file.name);
        this.$('.g-dicom-tags').html(TagsTemplate({
            tags: this.tagCache[file.name]
        }));
        this.setImageData(this.imageDataCache[file.name]);
    },

    render: function () {
        this.$el.html(ViewTemplate());
        return this;
    },

    autoLevels: function () {
        if (!this.imageData) {
            return;
        }
        const range = this.imageData.getPointData().getScalars().getRange();
        const ww = range[1] - range[0];
        const wc = (range[0] + range[1]) / 2;
        this.actor.getProperty().setColorWindow(ww);
        this.actor.getProperty().setColorLevel(wc);
    },

    autoZoom: function () {
        if (!this.imageData) {
            return;
        }
        this.ren.resetCamera();
        this.camera.zoom(1.44);

        const up = [0, -1, 0];
        const pos = this.camera.getPosition();
        pos[2] = -Math.abs(pos[2]);
        this.camera.setViewUp(up[0], up[1], up[2]);
        this.camera.setPosition(pos[0], pos[1], pos[2]);
    },

    setImageData: function (imageData) {
        this.imageData = imageData;

        if (this.first) {
            this.first = false;
            this.initVtk(imageData);
            this.autoLevels();
            this.autoZoom();
        } else {
            const mapper = vtkImageMapper.newInstance();
            mapper.setInputData(imageData);
            this.actor.setMapper(mapper);
        }

        this.iren.render();
    },

    initVtk: function (imageData) {
        $('.g-dicom-view').css('display', 'block');
        const container = this.$('.g-dicom-container')[0];

        const ren = vtkRenderer.newInstance();
        ren.setBackground(0.33, 0.33, 0.33);

        const renWin = vtkRenderWindow.newInstance();
        renWin.addRenderer(ren);

        const glWin = vtkOpenGLRenderWindow.newInstance();
        glWin.setContainer(container);
        glWin.setSize(512, 512);
        renWin.addView(glWin);

        const iren = vtkRenderWindowInteractor.newInstance();
        const style = vtkInteractorStyleImage.newInstance();
        iren.setInteractorStyle(style);
        iren.setView(glWin);

        const actor = vtkImageSlice.newInstance();
        ren.addActor(actor);

        const mapper = vtkImageMapper.newInstance();
        actor.setMapper(mapper);
        mapper.setInputData(imageData);

        const camera = ren.getActiveCameraAndResetIfCreated();

        iren.initialize();
        iren.bindEvents(container, document);
        iren.start();

        this.actor = actor;
        this.ren = ren;
        this.iren = iren;
        this.camera = camera;
    }

});

function createImageData(image) {
    const rows = image.getRows()
    const cols = image.getCols();
    const rowSpacing = image.getPixelSpacing()[0];
    const colSpacing = image.getPixelSpacing()[1];

    const imageData = vtkImageData.newInstance();
    imageData.setOrigin(0, 0, 0);
    imageData.setSpacing(colSpacing, rowSpacing, 1);
    imageData.setExtent(0, cols - 1, 0, rows - 1, 0, 0);

    const values = image.getInterpretedData();
    const dataArray = vtkDataArray.newInstance({values: values});
    imageData.getPointData().setScalars(dataArray);

    return imageData;
}

export default DicomView;
