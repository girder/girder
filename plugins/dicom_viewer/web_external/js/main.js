import ViewTemplate from 'templates/view.jade';
import TagsTemplate from 'templates/tags.jade';
import 'stylesheets/dicom_viewer.styl';
import {getTags} from 'js/tags.js';

import dicomParser from 'dicom-parser';
import vtkImageSlice from 'vtk.js/Sources/Rendering/Core/ImageSlice';
import vtkImageData from 'vtk.js/Sources/Common/DataModel/ImageData';
import vtkDataArray from 'vtk.js/Sources/Common/Core/DataArray';
import vtkImageMapper from 'vtk.js/Sources/Rendering/Core/ImageMapper';
import vtkInteractorStyleImage from 'vtk.js/Sources/Interaction/Style/InteractorStyleImage';
import vtkOpenGLRenderWindow from 'vtk.js/Sources/Rendering/OpenGL/RenderWindow';
import vtkRenderer from 'vtk.js/Sources/Rendering/Core/Renderer';
import vtkRenderWindow from 'vtk.js/Sources/Rendering/Core/RenderWindow';
import vtkRenderWindowInteractor from 'vtk.js/Sources/Rendering/Core/RenderWindowInteractor';

import naturalSort from 'javascript-natural-sort';
naturalSort.insensitive = true;

girder.wrap(girder.views.ItemView, 'render', function (render) {
  this.once('g:rendered', function () {
    $('.g-item-header').after('<div id="g-dicom-view"></div>');
    new girder.views.DicomView({
      el: $('#g-dicom-view'),
      parentView: this,
      item: this.model
    });
  }, this);
  render.call(this);
});

girder.views.DicomView = girder.View.extend({
  events: {
    'click #dicom-zoom-in': function (event) {
      event.preventDefault();
      this.camera.zoom(9 / 8);
      this.iren.render();
    },
    'click #dicom-zoom-out': function (event) {
      event.preventDefault();
      this.camera.zoom(8 / 9);
      this.iren.render();
    },
    'click #dicom-reset-zoom': function (event) {
      event.preventDefault();
      this.autoZoom();
      this.iren.render();
    },
    'click #dicom-first': function (event) {
      event.preventDefault();
      this.setIndex(0);
    },
    'click #dicom-previous': function (event) {
      event.preventDefault();
      if (this.index === 0) {
        this.setIndex(this.files.length - 1);
      } else {
        this.setIndex(this.index - 1);
      }
    },
    'click #dicom-next': function (event) {
      event.preventDefault();
      if (this.index === this.files.length - 1) {
        this.setIndex(0);
      } else {
        this.setIndex(this.index + 1);
      }
    },
    'click #dicom-last': function (event) {
      event.preventDefault();
      this.setIndex(this.files.length - 1);
    },
    'click #dicom-auto-levels': function (event) {
      event.preventDefault();
      this.autoLevels();
      this.iren.render();
    },
    'input #dicom-slider': _.debounce(function (event) {
      this.setIndex(event.target.value);
    }, 10)
  },

  initialize: function (settings) {
    this.item = settings.item;
    this.files = [];
    this.index = 0;
    this.first = true;
    this.imageData = null;
    this.xhr = null;
    this.imageCache = {};
    this.tagCache = {};
    this.render();
    this.loadFileList();
  },

  setIndex: function (index) {
    if (index < 0 || index >= this.files.length) {
      return;
    }
    this.index = index;
    document.getElementById("dicom-slider").value = index;
    this.loadFile(this.files[index]);
  },

  loadFileList: function () {
    girder.restRequest({
      path: '/item/' + this.item.get('_id') + '/dicom',
      data: {
        limit: 0
      }
    }).done(_.bind(function (resp) {
      this.handleFileList(resp);
    }, this));
  },

  handleFileList: function (files) {
    if (files.length > 0 && files[0].size > 1024 * 1024 * 2) {
      // don't automatically download huge files
      return;
    }
    // files = files.sort((a, b) => naturalSort(a.name, b.name));
    this.files = files;
    var slider = document.getElementById("dicom-slider");
    slider.min = 0;
    slider.max = this.files.length - 1;
    slider.step = 1;
    this.setIndex(0);
  },

  loadFile: function (file) {
    if (file.name in this.imageCache) {
      this.showCached(file);
      return;
    }
    console.log(file.name);
    if (this.xhr) {
      this.xhr.abort();
    }
    const xhr = new XMLHttpRequest();
    xhr.open('GET', girder.apiRoot + '/file/' + file._id + '/download', true);
    xhr.responseType = 'arraybuffer';
    xhr.onload = _.bind(function (event) {
      try {
        const byteArray = new Uint8Array(xhr.response);
        const dataSet = dicomParser.parseDicom(byteArray);
        const imageData = createImageData(dataSet);
        this.imageCache[file.name] = imageData;
        this.tagCache[file.name] = getTags(dataSet);
        this.showCached(file);
      }
      catch (e) {
        console.log(e);
      }
    }, this);
    xhr.send();
    this.xhr = xhr;
  },

  showCached: function (file) {
    document.getElementById('dicom-filename').innerHTML = file.name;
    document.getElementById('g-dicom-tags').innerHTML = TagsTemplate({
      tags: this.tagCache[file.name]
    });
    this.setImageData(this.imageCache[file.name]);
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
    document.getElementById('g-dicom-view').style.display = 'block';
    const container = document.getElementById('g-dicom-container');

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

function createImageData(dataSet) {
  const rows = dataSet.uint16('x00280010');
  const cols = dataSet.uint16('x00280011');
  const rowSpacing = dataSet.floatString('x00280030', 0);
  const colSpacing = dataSet.floatString('x00280030', 1);

  const imageData = vtkImageData.newInstance();
  imageData.setOrigin(0, 0, 0);
  imageData.setSpacing(colSpacing, rowSpacing, 1);
  imageData.setExtent(0, cols - 1, 0, rows - 1, 0, 0);

  const values = createPixelBuffer(dataSet);
  const dataArray = vtkDataArray.newInstance({values: values});
  imageData.getPointData().addArray(dataArray);

  return imageData;
}

function createPixelBuffer(dataSet) {
  const buffer = dataSet.byteArray.buffer;
  const dataOffset = dataSet.elements.x7fe00010.dataOffset;
  const pixelRepresentation = dataSet.uint16('x00280103');
  const bitsAllocated = dataSet.uint16('x00280100');
  const bitsStored = dataSet.uint16('x00280101');
  const rows = dataSet.uint16('x00280010');
  const cols = dataSet.uint16('x00280011');
  const numPixels = rows * cols;
  const pmi = dataSet.string('x00280004');
  if (pmi !== 'MONOCHROME1' && pmi !== 'MONOCHROME2') {
    throw 'unsupported photometric interpretation';
  }
  // construct proper array type
  let array;
  if (pixelRepresentation === 0 && bitsAllocated === 8) {
    array = new Uint8Array(buffer, dataOffset, numPixels);
  } else if (pixelRepresentation === 0 && bitsAllocated === 16) {
    array = new Uint16Array(buffer, dataOffset, numPixels);
  } else if (pixelRepresentation === 1 && bitsAllocated === 8) {
    array = new Int8Array(buffer, dataOffset, numPixels);
  } else if (pixelRepresentation === 1 && bitsAllocated === 16) {
    array = new Int16Array(buffer, dataOffset, numPixels);
  } else {
    throw 'unrecognized image format';
  }
  // copy values to float buffer
  const values = new Float32Array(array.length);
  if (pixelRepresentation === 0) { // unsigned
    const mask = (1 << bitsStored) - 1;
    for (let i = 0; i < values.length; i++) {
      values[i] = (array[i] & mask) / mask;
    }
  } else {
    for (let i = 0; i < values.length; i++) {
      values[i] = array[i];
    }
  }
  // scale values to be 0 to 1
  let lo = values[0];
  let hi = values[0];
  for (let i = 0; i < values.length; i++) {
    if (values[i] < lo) {
      lo = values[i];
    }
    if (values[i] > hi) {
      hi = values[i];
    }
  }
  for (let i = 0; i < values.length; i++) {
    values[i] = (values[i] - lo) / (hi - lo);
  }
  if (pmi === 'MONOCHROME1') {
    // invert values
    for (let i = 0; i < values.length; i++) {
      values[i] = 1 - values[i];
    }
  }
  return values;
}
