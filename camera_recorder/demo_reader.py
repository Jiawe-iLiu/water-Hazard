# Chuong Nguyen 2016
# Water detection project
#
# Demo of Zip Reader
# Author: Chuong Nguyen <chuong.nguyen@anu.edu.au>
#
# License: BSD 3 clause

import sys
from zip_reader import ZipReader

def demoReader():
    if len(sys.argv) == 2:
        player = ZipReader(sys.argv[1])
    elif len(sys.argv) == 3:
        player = ZipReader(sys.argv[1], ConfigFile=sys.argv[2])
    else:
    #    player = ZipReader('video_21-08-2016_12-14-49.zip', ConfigFile='SN1994.conf') # polarised
    #    player = ZipReader('video_21-08-2016_12-29-52.zip', ConfigFile='SN1994.conf') # normal
    #    player = ZipReader('video_21-08-2016_13-57-28.zip', ConfigFile='SN1994.conf') # polarised
    #    player = ZipReader('video_21-08-2016_14-06-25.zip', ConfigFile='SN1994.conf') # normal
#        player = ZipReader('../data/video_21-08-2016_14-21-39.zip', ConfigFile='../data/SN1994.conf') # polarised
    #    player = ZipReader('video_21-08-2016_14-39-02.zip', ConfigFile='SN1994.conf') # normal
    #    player = ZipReader('video_07-11-2016_11-14-58.zip', ConfigFile='SN1994.conf') # normal
        player = ZipReader('../data/video_18-11-2016_14-32-52.zip', ConfigFile='../data/SN1640.conf') # polarised

    #    player = ZipReader('/run/user/1000/gvfs/smb-share:server=backo.cecs.anu.edu.au,share=acrv/unpublished-data/users/chuong/water-puddles/2016-08-20/video_20-08-2016_15-15-31.zip', ComputeDepth=False)
    #    player = ZipReader('/run/user/1000/gvfs/smb-share:server=backo.cecs.anu.edu.au,share=acrv/unpublished-data/users/chuong/water-puddles/2016-08-20/video_20-08-2016_15-39-38.zip', ComputeDepth=True)
    #    player = ZipReader('/run/user/1000/gvfs/smb-share:server=backo.cecs.anu.edu.au,share=acrv/unpublished-data/users/chuong/water-puddles/2016-08-20/video_20-08-2016_15-56-48.zip', ComputeDepth=True)

#    player = ZipReader('temp.zip')
#    # Show original image pair and rectified pair and possibly depth map
    ComputeDepth=True #False
    for arg in sys.argv:
        if arg.lower() == 'computedepth':
            ComputeDepth = True
            break
    player.play(ComputeDepth=ComputeDepth)

#    # Just show original image pair and rectified pair
#    player.stereoRectify()

#    # Save rectified image pair in zip file
#    player.stereoRectify(Output='temp.zip')

#    # Save rectified image pairs in a folder
#    player.stereoRectify(Output='./rectified')

    # Save rectified image pairs in a folder to be processed by viso2
#    player.stereoRectify(Output='./video_21-08-2016_12-14-49', forViso=True)
#    player.stereoRectify(Output='./video_21-08-2016_14-21-39', forViso=True)


def demoReaderFrame():
    player = ZipReader('video_21-08-2016_12-14-49.zip',
                       ConfigFile='SN1994.conf') # polarised
    for i in range(len(player.ImageFileList)):
        Frame, TimeStamp = player.getFrame(i)
        FrameSmall = Frame[::2, ::2].copy()
        DateTime = datetime.datetime.fromtimestamp(float(TimeStamp))
        cv2.putText(FrameSmall, DateTime.strftime("%d-%m-%Y %H-%M-%S"),
                    (10, FrameSmall.shape[0]-15),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255))
        cv2.imshow('Rectified image pair', FrameSmall)
        Key = cv2.waitKey(10) & 0xFF
        if Key == ord('q') or Key == 27:
            break
        if Key == ord('p') or Key == ord(' '):
            logging.debug('Pause program. Press any key to continue...')
            cv2.waitKey(0)

if __name__ == '__main__':
    demoReader()
#    demoReaderFrame()
