#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
#  Copyright Kitware Inc.
#
#  Licensed under the Apache License, Version 2.0 ( the "License" );
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
###############################################################################

"""
Record a directory containing dicom objects in
the chronicle couch database.

Use --help to see options.

TODO:
* this should work equally on all dicom object instances,
so the image specific things should be factored out.
* consider making binary VRs into attachments (but maybe not,
since full object is available already as attachment)

"""

import os
import sys
import traceback
import json
import dicom
#import couchdb
import girder_client
import argparse

from girder_client import HttpError
from dicom_json_conversion import dataElementToJSON, datasetToJSON

try:
    import PIL
    import PIL.Image as Image
except ImportError:
    # for some reason easy_install doesn't generate a PIL layer on mac
    import Image

import numpy


# {{{ ChronicleRecord

class ChronicleRecord():
    """Performs the recording of DICOM objects
    """

    def __init__(self):
        #self.couchDB_URL=couchDB_URL
        #self.databaseName=databaseName

        #print(self.couchDB_URL)
        #self.couch = couchdb.Server(self.couchDB_URL)
        #try:
        #    print(self.databaseName)
        #    self.db = self.couch[self.databaseName]
        #except couchdb.ResourceNotFound:
        #    self.db = self.couch.create(self.databaseName)

        #self.gc = girder_client.GirderClient(port=8080)
        #self.gc.authenticate('jcfr', 'dicomweb')

        self.gc = girder_client.GirderClient(host='data.kitware.com', port=443, scheme='https')
        self.gc.token = 'Z472wxLYsFVcQNM3TVTXqWHhpNvXps6bqN7RBx3NbnlOGyVWBdqJhZpiJqIdpTQz'


    def windowedData(self,data, window, level):
        """Apply the RGB Look-Up Table for the given data and window/level value."""
        # deal with case of multiple values for window/level - use the first one in the list
        try:
            window = window[0]
            level = level[0]
        except TypeError:
            pass
        window = float(window) # convert from DS
        level = float(level) # convert from DS
        return numpy.piecewise(data,
            [data <= (level - 0.5 - (window-1)/2),
                data > (level - 0.5 + (window-1)/2)],
                [0, 255, lambda data: ((data - (level - 0.5))/(window-1) + 0.5)*(255-0)])

    def imageFromDataset(self,dataset):
        """return an image from the dicom dataset using the Python Imaging Library (PIL)"""
        if ('PixelData' not in dataset):
            # DICOM dataset does not have pixel data
            print('no pixels')
            return None
        if ('WindowWidth' not in dataset) or ('WindowCenter' not in dataset):
            print("No window width or center in the dataset")
            # no width/center, so use whole
            bits = dataset.BitsAllocated
            samples = dataset.SamplesperPixel
            if bits == 8 and samples == 1:
                mode = "L"
            elif bits == 8 and samples == 3:
                mode = "RGB"
            elif bits == 16:
                mode = "I;16" # from sample code: "not sure about this
                            # -- PIL source says is 'experimental' and no documentation.
                            # Also, should bytes swap depending on endian of file and system??"
            elif bits == 1 and samples == 1:
                mode = "1"
            else:
                raise TypeError, "Don't know PIL mode for %d BitsAllocated and %d SamplesPerPixel" % (bits, samples)
            # PIL size = (width, height)
            size = (dataset.Columns, dataset.Rows)
            # Recommended to specify all details by
            #  http://www.pythonware.com/library/pil/handbook/image.htm
            try:
                image = Image.frombuffer(mode, size, dataset.PixelData, "raw", mode, 0, 1).convert('L')
            except ValueError:
                print("ValueError getting image")
                image = None
        else:
            try:
                image = self.windowedData(
                                    dataset.pixel_array,
                                    dataset.WindowWidth, dataset.WindowCenter
                                    )
            except NotImplementedError:
                print("NotImplementedError: cannot get image data")
                return None
            except ValueError:
                print("ValueError: cannot get image data")
                return None
            # Convert mode to L since LUT has only 256 values:
            #  http://www.pythonware.com/library/pil/handbook/image.htm
            if image.dtype != 'int16':
                print('Type is not int16, converting')
                image = numpy.array(image, dtype='int16')
            try:
                image = Image.fromarray(image).convert('L')
            except TypeError:
                print('Type can not be converted')
                return None
        return image

    def imagesFromDataset(self,dataset, sizes = (32,64,128,256,512)):
        """
        returns a dictionary of pil images for each size where
        keys are the image size.
        """
        images = {}
        image = self.imageFromDataset(dataset)
        if image:
            for size in sizes:
                aspectRatio = image.size[0]/(1. * image.size[1])
                newSize = ( size, int(size / aspectRatio) )
                images[size] = image.resize(newSize,Image.ANTIALIAS)
        return images

    def recordDirectory(self,directoryPath):
        """Perform the record"""
        for root, dirs, files in os.walk(directoryPath):
            for fileName in files:
                fileNamePath = os.path.join(root,fileName)
                self.recordFile(fileNamePath)

    def recordFile(self,fileNamePath):
        print("Considering file: %s" % fileNamePath)

        # create dataset, skip non-dicom
        try:
            dataset = dicom.read_file(fileNamePath)
        except:
            print("...apparently not dicom")
            return

        # XXX Improve script to support folder_id parameter
        #folderId = '55f47d389069ef3b6b926582'
        folderId = '56005a768d777f6ddc3da1fb'
        #folderId = '560063958d777f6ddc3da201'

        uid = dataset.SOPInstanceUID

        # check if instance is already in database
        items = self.gc.listItem(folderId, name=uid)
        if items:
            print("... %s already in database" % uid)
            return

        print('...creating item...')
        item = self.gc.createItem(folderId, uid, "")

        # make a girder item that contains the dataset in json
        jsonDictionary = datasetToJSON(dataset)
        #document = {
        #    '_id' : dataset.SOPInstanceUID,
        #    'fileNamePath' : fileNamePath,
        #    'dataset': jsonDictionary
        #}

        self.gc.addMetadataToItem(item['_id'], jsonDictionary)

        # attach png images to the object if possible
        if self.attachImages:
          doc = self.db.get(doc_id)
          images = self.imagesFromDataset(dataset)
          for imageSize in images.keys():
            print('...thumbnail %d...' % imageSize)
            imageName = "image%d.png" % imageSize
            imagePath = "/tmp/" + imageName
            images[imageSize].save(imagePath) # TODO: generalize
            fp = open(imagePath)
            self.db.put_attachment(doc, fp, imageName)
            fp.close()
            os.remove(imagePath)

        # attach the original file
        if self.attachOriginals:
          print('...attaching dicom object...')
          self.gc.uploadFileToItem(item['_id'], fileNamePath)

        print ("...recorded %s" % uid)

        #sys.exit(0)

# }}}

# {{{ main, test, and arg parse

def usage():
    print ("record [directoryPath] <CouchDB_URL> <DatabaseName>")
    print (" CouchDB_URL default http://localhost:5984")
    print (" DatabaseName default 'chronicle'")

def main ():

    parser = argparse.ArgumentParser(description="Record DICOM documents into Chronicle of CouchDB")
    parser.add_argument("inputDirectory",help="Input path to search for files to record")
    #parser.add_argument("--url",dest="couchDB_URL",type=str,default="http://localhost:5984",help="CouchDB instance URL")
    #parser.add_argument("--dbName",dest="databaseName",type=str,default="chronicle",help="Name of the database")
    parser.add_argument("--dontAttachImages",dest="dontAttachImages",action="store_true",default=True,help="Flag to generate and attach image thumbnails")
    parser.add_argument("--dontAttachOriginals",dest="dontAttachOriginals",action="store_true",default=False,help="Flag to attach original DICOM files")
    ns = parser.parse_args()

    global recorder # for ipython debugging
    recorder = ChronicleRecord()
    recorder.attachImages = not ns.dontAttachImages
    recorder.attachOriginals = not ns.dontAttachOriginals

    path = ns.inputDirectory
    if os.path.isdir(path):
      recorder.recordDirectory(path)
    elif os.path.isfile(path):
      recorder.recordFile(path)

if __name__ == '__main__':
    try:
        main()
    except Exception, e:
        print ('ERROR, UNEXPECTED EXCEPTION')
        print str(e)
        traceback.print_exc()

# }}}
