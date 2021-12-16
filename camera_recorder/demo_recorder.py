# Chuong Nguyen 2016
# Water detection project
#
# Demo of Zip Recorder
# Author: Chuong Nguyen <chuong.nguyen@anu.edu.au>
#
# License: BSD 3 clause

import sys
from zip_recorder import ZipRecorder

def demoZipRecorder():
    ''' Demo recording with default PPM image format
    Usage:
        python demo_recorder.py <cameraID> <resolution> <outputFile>
        
        cameraID: index of camera, default is 1
        resolution: resolution of image for, default is HD
        outputFile: default is video_#date_#time.zip
    '''
    camID = 1
    resolution = 'HD'
    outputFile='video_#date_#time.zip'
    if len(sys.argv) >= 2:
        camID = int(sys.argv[1])
        print('Record from camera %d' % camID)
    for arg in sys.argv:
        if arg in ['HD', 'FHD']:
            resolution = arg
            print('Record video at %s resolution' % resolution)
            break
        if arg[-3:] in ['zip', 'ZIP']:
            outputFile = arg
            print('Save video to %s' %outputFile)
            break
    Recorder = ZipRecorder(camID, Resolution=resolution, OutputFile=outputFile)
    Recorder.start()
    Recorder.zipAll()
    Recorder.replay()


def demoZipRecorderJPG():
    ''' Demo recording with JPG image format'''
    Recorder = ZipRecorder(1, ImageFileFormat='jpg', Resolution='FHD',
                       OutputFile='video_#date_#time.zip')
    Recorder.start()
    Recorder.zipAll()
    Recorder.replay()

if __name__ == '__main__':
    demoZipRecorder()
#    demoZipRecorderJPG()

