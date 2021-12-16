# Chuong Nguyen 2016
# Water detection project
#
# Zip Reader (read video frames from zip file created by Zip Recorder)
# Author: Chuong Nguyen <chuong.nguyen@anu.edu.au>
#
# License: BSD 3 clause

import os
import cv2
import zipfile
import numpy as np
import datetime
import zedutils

import logging
logging.basicConfig(level=logging.DEBUG,
                    format='(%(threadName)-9s) %(message)s',)

class ZipReader:
    '''Reader for zip video file saved by Manager class object'''
    def __init__(self, ZipFile, TimeStampFile='TimeStamp.txt',
                 InfoFile='Info.txt', ConfigFile=None):
        self.ZipFile = ZipFile
        self.TimeStampFile = TimeStampFile
        self.ConfigFile = ConfigFile
        self.InfoFile = InfoFile
        try:
            self.fZip = zipfile.ZipFile(self.ZipFile, 'r')
        except Exception as e:
            logging.error('Fail to open file %s' % self.ZipFile)
            logging.error('Exception error: %s' % e.message)
            exit()

        self.TimeStampList = self.fZip.read(self.TimeStampFile).decode("utf-8").split('\n')
        # Remove possible empty element due to empty line
        if '' in self.TimeStampList:
            self.TimeStampList.remove('')

        self.ImageFileList = self.fZip.namelist()
        # Remove file names that not of image files
        if self.TimeStampFile in self.ImageFileList:
            self.ImageFileList.remove(self.TimeStampFile)
        if self.InfoFile in self.ImageFileList:
            self.ImageFileList.remove(self.InfoFile)

        assert len(self.ImageFileList) == len(self.TimeStampList), \
            "List sizes don't match : %d vs %d" % \
            (len(self.ImageFileList), len(self.TimeStampList))

        if self.ConfigFile is not None: # file 'SN1994.conf'
            self.map1x, self.map1y, self.map2x, self.map2y, self.mat, self.Q = \
                zedutils.getTransformFromConfig(ConfigFile, Type='CAM_HD')

    def getFrame(self, itemNumber=-1, itemName=None, isRectified=True):
        ''' Acess frame as array element
        '''
        if not self.fZip:
            logging.error('File is not open')
            return None

        if itemNumber >= 0:
            itemName = self.ImageFileList[itemNumber]
        else:
            itemNumber = self.ImageFileList.index(itemName)

        if (itemName is not None):
            try:
                img_data = self.fZip.read(itemName)
                img_array = np.fromstring(img_data, dtype=np.uint8)
                Frame = cv2.imdecode(img_array, -1)

                # split into left right images, rectify and join back
                im1_c = Frame[:, :Frame.shape[1]//2, :]
                im2_c = Frame[:, Frame.shape[1]//2:, :]
                if isRectified and self.ConfigFile is not None:
                    im1_rec = cv2.remap(im1_c, self.map1x, self.map1y,
                                        cv2.INTER_CUBIC)
                    im2_rec = cv2.remap(im2_c, self.map2x, self.map2y,
                                        cv2.INTER_CUBIC)
                    Frame = np.concatenate((im1_rec, im2_rec), axis=1)
                TimeStamp = self.TimeStampList[itemNumber]
                return Frame, TimeStamp
            except:
                if itemNumber >= 0:
                    logging.error('Failed to access frame %d' % itemNumber)
                else:
                    logging.error('Failed to access filename %d' % itemName)
                return None, None

    def stereoRectify(self, Output=None, isShow=True, isCompressed=False, forViso=False):
        '''Rectify stereo image pair captured by ZED camera.
        Option to export rectified images to either a zip file or a folder.
        isCompression only works when output to a zip file'''
        # check if Output is a folder or a file
        isOutput2Folder = False
        if Output is not None:
            if '.' not in os.path.basename(Output):
                isOutput2Folder = True
                if not os.path.exists(Output):
                    os.makedirs(Output)
            # zip with compression or not
            elif isCompressed:
                fzip = zipfile.ZipFile(Output, 'w',
                                       zipfile.ZIP_STORED, allowZip64=True)
            else:
                fzip = zipfile.ZipFile(Output, 'w', allowZip64=True)

        i = 0
        for ImageFile, TimeStamp in zip(self.ImageFileList, self.TimeStampList):
            logging.debug('Read %s' % ImageFile)
            img_data = self.fZip.read(ImageFile)
            img_array = np.fromstring(img_data, dtype=np.uint8)
            try:
                Frame = cv2.imdecode(img_array, -1)
            except:
                logging.debug('Cannot decode file %s' % ImageFile)
                continue

            # split into left right images, rectify and join back
            im1_c = Frame[:, :Frame.shape[1]/2, :]
            im2_c = Frame[:, Frame.shape[1]/2:, :]
            if self.ConfigFile is not None:
                im1_rec = cv2.remap(im1_c, self.map1x, self.map1y,
                                    cv2.INTER_CUBIC)
                im2_rec = cv2.remap(im2_c, self.map2x, self.map2y,
                                    cv2.INTER_CUBIC)
            else:
                im1_rec = im1_c
                im2_rec = im2_c

            FrameRect = np.concatenate((im1_rec, im2_rec), axis=1)

            i += 1
            if Output is not None:
                if not forViso:
                    NameParts = ImageFile.split('.')
                    ret, data = cv2.imencode('.' + NameParts[-1], FrameRect)
                    NameParts[-2] += '_rec'
                    ImageFile2 = '.'.join(NameParts)
                    if isOutput2Folder:
                        with open(os.path.join(Output, ImageFile2), 'w') as f:
                            f.write(data)
                    else:
                        fzip.writestr(ImageFile2, data)
                else:
                    LeftImage = cv2.cvtColor(im1_rec, cv2.COLOR_BGR2GRAY)
                    RightImage = cv2.cvtColor(im2_rec, cv2.COLOR_BGR2GRAY)
                    NameParts = ImageFile.split('.')
                    NameParts[-2] += '_rec'
                    NameParts[-1] = 'png'
                    ImageFile2 = '.'.join(NameParts)
                    cv2.imwrite(os.path.join(Output, 'Left_' + ImageFile2), LeftImage)
                    cv2.imwrite(os.path.join(Output, 'Right_' + ImageFile2), RightImage)
            if isShow:
                cv2.imshow('Input Frame', Frame[::2, ::2])
                cv2.imshow('Rectified Frame', FrameRect[::2, ::2])
                Key = cv2.waitKey(10) & 0xFF
                if Key == ord('q') or Key == 27:
                    break
                if Key == ord('p') or Key == ord(' '):
                    logging.debug('Pause program. Press any key to continue...')
                    cv2.waitKey(0)

        if Output is not None:
            TimeStampStr = '\n'.join(self.TimeStampList[:i])

            Info = '# Info for stereo-rectified images\n'
            Info += 'Mat: # camera matrix for left and right images\n'
            Info += '    ['+', '.join([str(d) for d in self.mat[0, :]]) + ']\n'
            Info += '    ['+', '.join([str(d) for d in self.mat[1, :]]) + ']\n'
            Info += '    ['+', '.join([str(d) for d in self.mat[2, :]]) + ']\n'
            Info += 'Q: # disparity-to-depth mapping matrix\n'
            Info += '    ['+', '.join([str(d) for d in self.Q[0, :]]) + ']\n'
            Info += '    ['+', '.join([str(d) for d in self.Q[1, :]]) + ']\n'
            Info += '    ['+', '.join([str(d) for d in self.Q[2, :]]) + ']\n'
            Info += '    ['+', '.join([str(d) for d in self.Q[3, :]]) + ']\n'

            if isOutput2Folder:
                with open(os.path.join(Output, self.TimeStampFile), 'w') as f:
                    f.write(TimeStampStr)
                with open(os.path.join(Output, self.InfoFile), 'w') as f:
                    f.write(Info)
            else:
                fzip.writestr(self.TimeStampFile, TimeStampStr)
                fzip.writestr(InfoFilename, Info)
                fzip.close()


    def play(self, ComputeDepth=False):
        '''Display image pairs in zip video file.
        Optionally rectify the image if camera config file is provided'''
        window_size = 19
        min_disp = 0
        max_disp = 128
        num_disp = max_disp-min_disp
        #stereo = cv2.StereoBM(min_disp, num_disp, window_size)
        stereo = cv2.StereoSGBM(min_disp, num_disp, window_size)

        for ImageFile, TimeStamp in zip(self.ImageFileList[::10], self.TimeStampList[::10]):
            logging.debug('Read %s' % ImageFile)
            img_data = self.fZip.read(ImageFile)
            img_array = np.fromstring(img_data, dtype=np.uint8)
            try:
                Frame = cv2.imdecode(img_array, -1)
            except:
                logging.debug('Cannot decode file %s' % ImageFile)
                continue

            if ComputeDepth:
                im1_c = Frame[:, :Frame.shape[1]/2, :]
                im2_c = Frame[:, Frame.shape[1]/2:, :]
                if self.ConfigFile is not None:
                    im1_rec = cv2.remap(im1_c, self.map1x, self.map1y, cv2.INTER_CUBIC)
                    im2_rec = cv2.remap(im2_c, self.map2x, self.map2y, cv2.INTER_CUBIC)
                else:
                    im1_rec = im1_c
                    im2_rec = im2_c
                im1 = cv2.cvtColor(im1_rec, cv2.COLOR_BGR2GRAY)
                im2 = cv2.cvtColor(im2_rec, cv2.COLOR_BGR2GRAY)
                if 1:
                    disp = (stereo.compute(im1, im2).astype(np.float32) - min_disp)/16
                else:
                    sobel1 = getSobel(im1, True)
                    sobel2 = getSobel(im2, True)
                    disp = (stereo.compute(sobel1, sobel2).astype(np.float32) - min_disp)/16

                for i in range(0, im1.shape[0], 40):
                    cv2.line(im1_rec, (0, i), (im1.shape[1], i), (0,0,0))
                    cv2.line(im2_rec, (0, i), (im2.shape[1], i), (0,0,0))
                cv2.imshow('Left Rectified Frame', im1_rec[::2, ::2])
                cv2.imshow('Right Rectified Frame', im2_rec[::2, ::2])
                cv2.imshow('Stereo Disparity', disp[::2, ::2]/num_disp)

            # show image at 1/4 resolution
            FrameSmall = np.copy(Frame[::2, ::2, :])
            DateTime = datetime.datetime.fromtimestamp(float(TimeStamp))
            cv2.putText(FrameSmall, DateTime.strftime("%d-%m-%Y %H-%M-%S"),
                        (10, FrameSmall.shape[0]-15),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0))
            cv2.imshow('Play recorded frame. Press: Q or ESC to quit, P or space to pause',
                       FrameSmall)
            Key = cv2.waitKey(10) & 0xFF
            if Key == ord('q') or Key == 27:
                break
            if Key == ord('p') or Key == ord(' '):
                logging.debug('Pause program. Press any key to continue...')
                cv2.waitKey(0)

def getSobel(frame, isPhase=True):
    if len(frame.shape) == 3:
        frameGray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    else:
        frameGray = frame
    sobelX = cv2.Sobel(frameGray, cv2.CV_32F, 1, 0, ksize=5)
    sobelY = cv2.Sobel(frameGray, cv2.CV_32F, 0, 1, ksize=5)
    if isPhase:
        sobel = cv2.phase(sobelX, sobelY)
    else:
        sobel = cv2.magnitude(sobelX, sobelY)

    minVal = np.min(sobel)
    maxVal = np.max(sobel)
    sobel = (255*(sobel - minVal)/(maxVal - minVal)).astype(np.uint8)
    return sobel



