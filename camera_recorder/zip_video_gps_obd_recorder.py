# Chuong Nguyen 2016
# Water detection project
#
# Zip Recorder (capture and store video frames and time stamps into a zip file)
# Author: Chuong Nguyen <chuong.nguyen@anu.edu.au>
#
# License: BSD 3 clause

from multiprocessing import Process, Queue, Value, cpu_count
import cv2
import zipfile
import os
import numpy as np
import time
import datetime
import sys

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from utilities import OBDPort, GPSPort#, SENSORS

import logging
logging.basicConfig(level=logging.DEBUG,
                    format='(%(threadName)-9s) %(message)s',)

IMAGE_DATA = 0
GPS_DATA = 1
ODOM_DATA = 2

class Counter(object):
    def __init__(self):
        self.val = Value('i', 0)

    def increment(self, n=1):
        with self.val.get_lock():
            self.val.value += n

    @property
    def value(self):
        return self.val.value

    @property
    def value_increment(self):
        with self.val.get_lock():
            self.val.value += 1
            return self.val.value

class Message(object):
    def __init__(self, is_running=False, is_recording=False):
        self.values = {}
        self.values['is_running'] = is_running
        self.values['is_recording'] = is_recording

    def value(self, prop):
        return self.values[prop]

    def set_value(self, prop, value):
        self.values[prop] = value


def poll_camera(DataQueue, Camera, message):
    isRecorded = False
    while True:
        ret, Frame = Camera.read()
        timeStamp = time.time()
        status = '- Live view'
        if isRecorded:
            message.set_value('is_recording', True)
            DataQueue.put([IMAGE_DATA, Frame, timeStamp])
            status = '- Recording'

        # display running info
        FrameSmall = np.copy(Frame[::2, ::2, :])
        cv2.putText(FrameSmall, '[%d, %d] px %s' %
                    (Frame.shape[1], Frame.shape[0], status),
                    (10, FrameSmall.shape[0]-15),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0))
        # show image at 1/4 resolution
        cv2.imshow('Press: Q to quit - R to record - S to stop', FrameSmall)
        Key = cv2.waitKey(1) & 0xFF
        if Key == ord('q'):
            isRecorded = False
            message.set_value('is_recording', False)
            message.set_value('is_running', False)
            logging.debug("Quit")
            break
        elif Key == ord('r') or Key == ord('R'):
            isRecorded = True
            message.set_value('is_recording', True)
            logging.debug("Record")
        elif Key == ord('s') or Key == ord('s'):
            isRecorded = False
            message.set_value('is_recording', False)
            logging.debug("Stop")

    cv2.destroyAllWindows()
    DataQueue.put(None)


def poll_gps(DataQueue, GpsPort, message):
    print('Start poll_gps')
    while message.value('is_running'):
        try:
            if message.value('is_recording'):
                lon, lat, alt, q, rollrate, pitchrate, yawrate, tmsp = GpsPort.readGPS()
                print('lat, lon, alt, tmsp = %f, %f, %f, %d' % (lat, lon, alt, tmsp))
                DataQueue.put([GPS_DATA, [lon, lat, alt, q, rollrate, pitchrate, yawrate], tmsp])
            else:
                time.sleep(0.01)
        except:
            print('Exception')
            break
    print('Stop poll_gps')

def save_data(id, DataQueue, ImageFilePattern, ImageCounter, ImageTimeStampFile,
              GpsFilename):
    imgTSFile = open(ImageTimeStampFile, 'w')
    if GpsFilename is not None:
        GpsFile = open(GpsFilename, 'w')
        GpsFile.write('{}, {}, {}, {}, {}, {}, {}, {}\n'.format('latitude',
                      'longitude', 'altitude', 'quaternion','rollrate',
                      'pitchrate', 'yawrate', 'timeStamp'))
    while True:
        Data = DataQueue.get()
        if Data is None:
            break

        Type, Content, timeStamp = Data
        if Type == IMAGE_DATA:
            Index = ImageCounter.value_increment
            cv2.imwrite(ImageFilePattern % Index, Content)
            imgTSFile.write('%f\n' % timeStamp)
        elif Type == GPS_DATA and GpsFilename is not None:
            lon, lat, alt, q, rollrate, pitchrate, yawrate, tmsp = Content
            GpsFile.write('{}, {}, {}, {}, {}, {}, {}, {}\n'.format(
                lon, lat, alt, q, rollrate, pitchrate, yawrate, tmsp))
        logging.debug("%d task: save image %d, queue length %d" %
                      (id, Index, DataQueue.qsize()))
    imgTSFile.close()
    DataQueue.put(None)


#def poll_odom(ObdPort, ObdFile, message):
#    for s in SENSORS:
#        if s.name.strip() == 'Vehicle Speed': #'Coolant Temperature': #
#            sensor = s
#
#    while message['is_running']:
#        try:
#            if messages['is_recording']:
#                value, tmsp = ObdPort.get_sensor_value(sensor)
#                ObdFile.write('{}, {}, {}\n'.format(value, sensor.unit, tmsp))
#                logging.debug("Velocity = {} km/h".format(value))
#            else:
#                time.sleep(0.01)
#        except:
#            break
#    ObdFile.close()


class ZipVideoGpsObdRecorder:
    '''
    Class to record images from ZED stereo camera.
    Possible for use with other webcam.
    '''
    def __init__(self, DeviceIndex=1, Resolution='HD', OutputFile='video_#date_#time.zip',
                 ImageFilePattern='img_%09d.ppm', ImageFileFormat='ppm',
                 TimeStampFile='video_time_stamp_#date_#time.txt',
                 GpsPortName=None, GpsFilename='gps_#date_#time.csv',
                 ObdPortName=None, ObdFilename='odom_#date_#time.csv'):
        ''' Default values:
            - DeviceIndex = 1
            - Resolution = 'HD'; ['2.2K', 'FHD', 'HD', 'HD60', or 'WVGA']
            - OutputFile = 'video.zip'
            - ImageFilePattern = 'img_%09d.ppm'
        '''
        print(GpsPortName)
        self.DataQueue = Queue()
        self.ImageCounter = Counter()
        if 'ppm' in ImageFilePattern.lower() or 'bmp' in ImageFilePattern.lower():
            # one worker is enough
            self.NUMBER_OF_PROCESSES = 1
        else:
            # more processes needed for compression formats
            self.NUMBER_OF_PROCESSES = cpu_count()-1  # one reserve for server

        # ZED stereo camera supported resolutions and framerates
        resolution = {'2.2K': [4416, 1242],
                      'FHD': [3840, 1080],
                      'HD': [2560, 720],
                      'HD60': [2560, 720],
                      'WVGA': [1344, 376]}
        framerate = {'2.2K': 15,
                     'FHD': 30,
                     'HD': 30,
                     'HD60': 60,
                     'WVGA': 100}

        self.Camera = cv2.VideoCapture(DeviceIndex)
        if self.Camera.isOpened():
            ret1 = self.Camera.set(cv2.cv.CV_CAP_PROP_FRAME_WIDTH,
                                   resolution[Resolution][0])
            ret2 = self.Camera.set(cv2.cv.CV_CAP_PROP_FRAME_HEIGHT,
                                   resolution[Resolution][1])
            ret3 = self.Camera.set(cv2.cv.CV_CAP_PROP_FPS,
                                   framerate[Resolution])
            if ret1 or ret2 or ret3:
                print('Failed to set resolution or framerate')
        else:
            print('Failed to open video device #%d' % DeviceIndex)

        today = datetime.datetime.now()
        self.OutputFile = self.apply_data_time(OutputFile, today)
        self.GpsFilename = self.apply_data_time(GpsFilename, today)
        self.ObdFilename = self.apply_data_time(ObdFilename, today)

        self.GpsPort = None
        self.ObdPort = None
        if GpsPortName is not None:
            self.GpsPort = GPSPort(GpsPortName)
#        if ObdPortName is not None:
#            self.ObdPort = OBDPort(ObdPortName)

        self.ImageFilePattern = ImageFilePattern
        self.ImageFileFormat = ImageFileFormat

        # take care of cases where file pattern or format changes
        if 'ppm' not in self.ImageFileFormat:
            OldImageFormat = self.ImageFilePattern.split('.')[-1]
            self.ImageFilePattern = \
                self.ImageFilePattern.replace(OldImageFormat,
                                              self.ImageFileFormat)
        if 'img_%09d.ppm' not in self.ImageFilePattern:
            self.ImageFileFormat = self.ImageFilePattern.split('.')[-1]

        self.TimeStampFile = TimeStampFile

    def apply_data_time(self, Filename, today):
        if '#date' in Filename:
            Filename = \
                Filename.replace('#date', today.strftime("%d-%m-%Y"))
        if '#time' in Filename:
            Filename = \
                Filename.replace('#time', today.strftime("%H-%M-%S"))
        return Filename

    def start(self):
        ''' Start live view and ready to capture images
        '''
        message = Message()
        message.set_value('is_running', True)
        if self.Camera.isOpened():
            print ("starting %d workers" % self.NUMBER_OF_PROCESSES)
#            self.workers = [Process(target=save_data, args=(i, self.DataQueue, self.ImageFilePattern, self.ImageCounter, self.TimeStampFile))
#                            for i in xrange(self.NUMBER_OF_PROCESSES)]
            self.workers = []
            if self.Camera.isOpened():
                self.workers.append(Process(target=poll_camera,
                                            args=(self.DataQueue,
                                                  self.Camera, message)))
            if self.GpsPort is not None:
                self.workers.append(Process(target=poll_gps,
                                            args=(self.DataQueue,
                                                  self.GpsPort, message)))

#            if self.ObdPort is not None:
#                self.ObdFile = open(self.ObdmFilename, 'w')
#                self.workers.append(Process(target=poll_obd, args=(self.ObdPort, self.ObdFile, message)))

            for w in self.workers:
                w.start()

#            poll_camera(self.DataQueue, self.Camera, message)
            save_data(0, self.DataQueue, self.ImageFilePattern,
                      self.ImageCounter, self.TimeStampFile,
                      self.GpsFilename)

            self.Camera.release()
            self.GpsPort.close()
        else:
            print('Camera is not opened')

    def stop(self):
        self.DataQueue.put(None)
        for i in range(self.NUMBER_OF_PROCESS):
            self.workers[i].join()
        self.DataQueue.close()

    def zipAll(self, isCompressed=False):
        '''Zip all captured images into a single file.
        Zip with compression requires significant computation to zip and unzip.
        '''
        # skip if there is no images to zip
        if self.ImageCounter.value == 0:
            logging.debug('No image was recorded. Skip zipping.')
            return

        # zip with compression or not
        if isCompressed:
            fzip = zipfile.ZipFile(self.OutputFile, 'w', zipfile.ZIP_STORED,
                                   allowZip64=True)
        else:
            fzip = zipfile.ZipFile(self.OutputFile, 'w', allowZip64=True)

        # add image files
        for i in range(self.ImageCounter.value):
            fzip.write(self.ImageFilePattern % (i+1))
            os.remove(self.ImageFilePattern % (i+1))
            if (i*100//self.ImageCounter.value) % 10 == 0:
                logging.debug('Zip %d percent.' % (i*100/self.ImageCounter.value))
        fzip.write(self.TimeStampFile)
        os.remove(self.TimeStampFile)
        fzip.close()

    def replay(self, FileName=''):
        ''' Open zip file and show images.
            If FileName is given the file will be played.
        '''
        if len(FileName) == 0:
            if self.ImageCounter.value == 0:
                logging.debug('No image was recorded. Skip playing.')
                return
            FileName = self.OutputFile

        try:
            fzip = zipfile.ZipFile(FileName, 'r')
        except:
            print('Fail to open file %s' % FileName)
            return

        TimeStampList = fzip.read(self.TimeStampFile).split('\n')
        TimeStampList.remove('')
        ImageFileList = fzip.namelist()
        ImageFileList.remove(self.TimeStampFile)
        assert len(ImageFileList) == len(TimeStampList), \
                                        "List sizes don't match"
        for ImageFile, TimeStamp in zip(ImageFileList, TimeStampList):
            logging.debug('Read %s' % ImageFile)
            img_data = fzip.read(ImageFile)
            img_array = np.fromstring(img_data, dtype=np.uint8)
            DateTime = datetime.datetime.fromtimestamp(float(TimeStamp))
            try:
                Frame = cv2.imdecode(img_array, -1)
                # show image at 1/4 resolution
                FrameSmall = np.copy(Frame[::2, ::2, :])
                cv2.putText(FrameSmall, DateTime.strftime("%d-%m-%Y %H-%M-%S"),
                            (10, FrameSmall.shape[0]-15),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0))
                cv2.imshow('Replay recorded frame. Press: Q or ESC to quit',
                           FrameSmall)
                Key = cv2.waitKey(10) & 0xFF
                if Key == ord('q') or Key == 27:
                    break
                if Key == ord('p') or Key == ord(' '):
                    print('Pause program. Press any key to continue...')
                    cv2.waitKey(0)
            except:
                logging.debug('Cannot decode file %s' % ImageFile)
                continue

        fzip.close()
