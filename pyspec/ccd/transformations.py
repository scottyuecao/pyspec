#
# transformations.py (c) Stuart B. Wilkins 2010 and (c) Sven Partzsch 2010
#
# $Id$
# $HeadURL$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Part of the "pyspec" package
#

import numpy as np
import matplotlib.pyplot as plt
from   pyspec import spec
from   pyspec.diffractometer import Diffractometer
from   pyspec.ccd.PrincetonSPE import *
from   pyspec.ccd.plotter import PlotGrid
import gridder

#
# global help functions
#

def getAreaSet(image, roi):

    """
    selects a region of interest (ROI) from a CCD image
    image : array of the image values in the full window ( [   1, 325,   1, 335 ] )
    roi   : region of interest [xmin, dx, ymin, dy], e.g. [137, 51, 142, 51] for center

    output
    cut   : [ [val00, val01, ..., val0m],
              [val10, val11, ..., val1m],
              ...,
              [valn0, valn1, ..., valnm] ]
    valij is value at (x[i], y[j]) 
    """

    # data points in region of interest at (y, x)
    cut = image[roi[2]-1:roi[2]+roi[3]-1, roi[0]-1:roi[0]+roi[1]-1 ]

    return cut


def getAreaXY(roi):

    """
    calculates (x, y) = (x[0], x[1]) set for each point in region of interest

    output
    z  : [ [ [x00, x10, ..., xn0], [x01, x11, ..., xn1], ..., [x0m, x1m, ..., xnm] ],
           [ [y00, y10, ..., yn0], [y01, y01, ..., yn1], ..., [y0m, y1m, ..., ynm] ] ]
    """

    z  = np.array(np.meshgrid(np.arange(roi[0], roi[0] + roi[1]), np.arange(roi[2], roi[2] + roi[3])))
            
    return z 

#
# image processor class
#

class ImageProcessor():
    """Image Processor class

    This class provides the processing of single and sets of CCD-images
    in more detail: each pixel is transformed into reciprocal space
    the set of reciprocal vectors and intensities is gridded on a regular cuboid
    the needed informations can be provided by a spec scan from the pyspec packed"""

    def __init__(self):
        # set parameters to configure the CCD setup
        # detector distance 30cm and detector pixel size 20um
        self.detDis      = 300
        self.detPixSizeX = 0.020
        self.detPixSizeY = 0.020
        # detector size in pixel
        self.detSizeX    = 1300
        self.detSizeY    = 1340
        self.detX0       = 1300 / 2.0
        self.detY0       = 1340 / 2.0
        # image treatment
        self.conRoi      = None
        self.frameMode   = 1
        self.setName     = 'Set #'
        self.setNum      = 1
        # gridder options
        self.setGridOptions()

    #
    # set part
    #

    def setBins(self, binX, binY):
        """Takes binning into acount"""
        self.detPixSizeX *= binX
        self.detPixSizeX *= binY
        self.detSizeX    /= binX
        self.detSizeY    /= binY
        self.detX0       /= binX
        self.detY0       /= binY

    def setBySpec(self, conScan):
        """get settings from the considered pyspec scan object
        wavelength, filenames, angels, kind of set (scan)"""

        self.waveLen       = conScan.wavelength
        self.imFileNames   = conScan.getCCDFilenames()
        self.darkFileNames = conScan.getCCDFilenames(dark = 1)
        self.settingAngles = conScan.getSIXCAngles()
        self.intentNorm    = conScan.Ring
        self.setName       = 'Scan #'
        self.setNum        = conScan.scan
   
    def setConRoi(self, conRoi):
        """Sets the considered region of interest [xMin, xStep, yMin, yStep]"""
        self.conRoi = conRoi

    def setFrameMode(self, mode):
        """modes of frames are: theta- (1), phi- (2), cartesian- (3) and hkl-frame (4)"""
        self.frameMode = mode

    def setGridOptions(self, Qmin = None, Qmax = None, dQN = None):
        """Sets the options for the gridding of the dataset
        Size of the cuboid: Qmin, Qmax = [Qx, Qy, Qz]_min, max
        Number of parts   : dQN = [Nqx, Nqy, Nqz]"""

        self.Qmin = Qmin
        self.Qmax = Qmax
        self.dQN  = dQN
    
    #
    # help function part
    #

    def _readImage(self, imNum):
        """Read in the considered region of interest of the image
        dark image subtraction and normalization by ring current"""
        
        print '%s%d image #%03d: read image' % (self.setName, self.setNum, imNum)

        # get dark image (first CCD image)
        darkMon  = self.intentNorm[0]
        fileName = self.darkFileNames[0]
        darkVal  = PrincetonSPEFile(fileName)[0].astype(numpy.float64)
        
        # get file name and read image of data point
        pointMon = self.intentNorm[imNum]
        fileName = self.imFileNames[imNum]
        pointVal = PrincetonSPEFile(fileName)[0].astype(numpy.float64)

        # considered region of interest
        if self.conRoi == None:
            self.conRoi   = [1, len(pointVal[0]), 1, len(pointVal)]

        # get considered part of the images
        conDark  = getAreaSet(darkVal,  self.conRoi) / darkMon
        conIm    = getAreaSet(pointVal, self.conRoi) / pointMon - conDark

        return conIm

    def _XY2delgam(self, del0, gam0):

        """
        calculate (delta, gamma) from (x, y), flattend arrays are used
        x, y       : given (x, y)coordinates on CCD
        del0, gam0 : given (delta, gamma) of point0, e.g. center
        x0, y0     : given (x, y) of point0, e.g. center
        """

        # (x, y)-values
        conZ = getAreaXY(self.conRoi)
        x    = np.ravel(conZ[0])
        y    = np.ravel(conZ[1])

        # detector distance
        detDis = self.detDis
        # pixel distance binded 4x4 -> 80um (micro meter)
        pixDisX = self.detPixSizeX
        pixDisY = self.detPixSizeY
        # (x, y) for point0, take center of CCD
        x0 = self.detX0
        y0 = self.detY0

        # work in grad
        delta = del0 - np.arctan( (y-y0)*pixDisY/detDis )/np.pi*180.0
        gamma = gam0 - np.arctan( (x-x0)*pixDisX/detDis )/np.pi*180.0
    
        return delta, gamma

        
    #
    # process part
    #

    def processOneImage(self, imNum):
        """Process one image to (Qx, Qy, Qz, I)
        modes of frames are: theta- (1), phi- (2), cartesian- (3) and hkl-frame (4)"""

        # used mode
        mode = self.frameMode
        # angle alias
        delta = self.settingAngles[imNum, 0]
        theta = self.settingAngles[imNum, 1]
        chi   = self.settingAngles[imNum, 2]
        phi   = self.settingAngles[imNum, 3]
        mu    = self.settingAngles[imNum, 4]
        gamma = self.settingAngles[imNum, 5]
        
        # intensities of considered image part
        intent = np.ravel( self._readImage(imNum) )

        # (delta, gamma)-values at each pixel
        delPix, gamPix = self._XY2delgam(delta, gamma)        

        print '%s%d image #%03d: get (Qx, Qy, Qz)' % (self.setName, self.setNum, imNum)
        
        # diffractometer for angle to q calculations
        scanDiff = Diffractometer()
        scanDiff.setLambda(self.waveLen)
        scanDiff.setAngles(delta = delPix, theta = theta, chi   = chi   ,
                           phi   = phi   , mu    = mu   , gamma = gamPix)
        scanDiff.calc()
        if mode == 1:
            Qxyz = scanDiff.getQTheta()
        elif mode == 2:
            Qxyz = scanDiff.getQPhi()
        elif mode == 3:
            Qxyz = scanDiff.getQCart()
        elif mode == 4:
            Qxyz = scanDiff.getQHKL()
        else:
            print 'mode = %s is no proper mode for calculation of (Qx, Qy, Qz)!'
            print 'choose  theta- (1), phi- (2), cartesian- (3) or hkl-frame (4)'

        # out put (Qx, Qy, Qz, I)
        totIm = np.zeros((intent.size, 4))
        totIm[:,:3] = Qxyz
        totIm[:,3]  = intent

        return totIm

    def processOneSet(self):
        """Process full set of images (Qx, Qy, Qz, I)
        modes of frames are: theta- (1), phi- (2), cartesian- (3) and hkl-frame (4)"""

        print '\n%s%d: process to (Qx, Qy, Qz, I)' % (self.setName, self.setNum)

        # prepare size of full dataset and get data of first scan
        setSize  = self.settingAngles.shape[0]
        totFirst = self.processOneImage(0)
        imSize   = totFirst.shape[0]
        npts     = setSize * imSize
        totSet   = np.zeros((npts, 4))

        # go through all images and get data sets
        j = 0
        k = imSize
        totSet[j:k,:] = totFirst
        for i in range(1, setSize):
            j = j + imSize
            k = k + imSize
            totSet[j:k, :] = self.processOneImage(i)

        return totSet

    def makeGridData(self, totData):
        """Grid the data set into a cuboid
        Size of the cuboid: Qmin, Qmax = [Qx, Qy, Qz]_min, max
        Number of parts   : dQN = [Nqx, Nqy, Nqz]"""

        # prepare min, max,...
        if self.Qmin == None:
            self.Qmin = np.array([ totData[:,0].min(), totData[:,1].min(), totData[:,2].min() ])
        if self.Qmax == None:
            self.Qmax = np.array([ totData[:,0].max(), totData[:,1].max(), totData[:,2].max() ])
        if self.dQN  == None:
            self.dQN = [100, 100, 100]

        # use alias for grid options
        Qmin = self.Qmin
        Qmax = self.Qmax
        dQN  = self.dQN

        # 3D grid of the data set 
        gridData, gridOccu, gridOut = gridder.grid3d(totData, Qmin[0], Qmax[0], dQN[0], Qmin[1], Qmax[1], dQN[1], Qmin[2], Qmax[2], dQN[2])
        if gridOut != 0:
            print "Warning : There are %.2e points outside the grid (%.2e points in the grid)" % (gridOut, gridData.size - gridOut)
        emptNb = (gridOccu == 0).sum()
        if emptNb:
            print "Warning : There are %.2e values zero in the grid" % emptNb

        # mask the gridded data set
        #gridData = ma.array(gridData / gridOccu, mask = (gridOccu == 0))
    
        return gridData, gridOccu, gridOut


####################################
#
# main program, for test
#
####################################


if __name__ == "__main__":

    sf   = spec.SpecDataFile('/home/tardis/spartzsch/2010_09_X1A2/ymn2o5_sep10_1', 
			     ccdpath = '/mounts/davros/nasshare/images/sept10')
    scan = sf[244]

    testData = ImageProcessor()
    testData.setBins(4, 4)
    testData.setBySpec(scan)
    testData.setConRoi([1, 325, 1, 335])
    testData.setFrameMode(1)
    #print testData.processOneImage(40)
    totSet = testData.processOneSet()
    testData, testOccu, testNo = testData.makeGridData(totSet)
    testPlot = PlotGrid()
    testPlot.setGrid(testData, testOccu)
    testPlot.plot2DPro()
    testPlot.plot1DPro()
    plt.show()

