#
# utils.py (c) Stuart B. Wilkins 2008
#
# $Id: fit.py 114 2010-11-05 23:06:55Z stuwilkins $
# $HeadURL: https://pyspec.svn.sourceforge.net/svnroot/pyspec/trunk/pyspec/fit.py $
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
"""Set of useful utilities for plotting, and life in general!"""
from __future__ import with_statement
import pylab as pl
import numpy as np
import pickle 
import pyspec
import os
from matplotlib.ticker import MultipleLocator, MaxNLocator

# Some constants
golden_mean = (np.sqrt(5)-1.0)/2.0

def printAll(fname = "Plot", hc = False, small = True, lpcommand = 'lp'):
    """Print all figures"""
    for x in range(1, pl.gcf().number + 1):
        f = pl.figure(x)
        if small:
            f.set_size_inches(4, 3)
        pl.savefig('%s%03d.ps' % (fname, x), papertype = 'letter', orientation = 'portrait')
        if hc:
            os.system('%s %s%03d.ps' % (lpcommand, fname, x))

def multifit(sf, scans, var, *args, **kwargs):
    alldata = np.array([])
    allerrors = np.array([])
    pl.figure(figsize=(8.5, 11))

    firstrun = True
    plotnum = 1

    npp = kwargs.get('npp', (6, 2));
    if kwargs.has_key('npp'):
        del kwargs['bgnd']
    bgnd = kwargs.get('bgnd', None);
    if kwargs.has_key('npp'):
        del kwargs['bgnd']
    guessfollow = kwargs.get('guessfollow', False);
    if kwargs.has_key('guessfollow'):
        del kwargs['guessfollow']

    if type(var) == tuple:
        xvar = var[0]
        pvar = var[1]
        if len(var) > 2:
            mvar = var[2]
        else:
            mvar = None

        if len(var) > 3:
            yvar = var[3]
        else:
            yvar = None

    else:
        xvar = var
        pvar = None
        mvar = None
        yvar = None

    for scan in scans:
        pl.subplot(npp[0], npp[1], plotnum)

        sf[scan].plot(new = False, notitles = True, xcol = pvar, ycol = yvar,mcol = mvar)

        pl.subplots_adjust(hspace=0.4)

        if firstrun == True:
            f = pyspec.fit.fitdata(*args, **kwargs)
            firstrun = False
        else:
            if guessfollow:
                kwargs['guess'] = f.result
            f = pyspec.fit.fitdata(*args, **kwargs)

        exec '_xvar = sf[scan].%s' % var[0] 

        alldata = np.concatenate((alldata, np.array([np.mean(_xvar)]), f.result))
        allerrors = np.concatenate((allerrors, np.array([np.std(_xvar)]), f.stdev))

        pl.title('[%s] %f +- %f' % (scan, np.mean(_xvar), np.std(_xvar)))

        if(plotnum == (npp[0] * npp[1])):
            pl.figure(figsize=(8.5, 11))
            plotnum = 1
        else:
            plotnum += 1
            
    alldata = alldata.reshape(-1, len(f.result)+1)
    allerrors = allerrors.reshape(-1, len(f.result)+1)

    return alldata, allerrors

def pickleit(filename, object):
    """Pickle a python object

    filename : filename to pickle to
    object   : Python object to pickle"""
    output = open(filename, 'wb')
    for o in object:
        pickle.dump(o, output)
    output.close()

def unpickleit(filename):
    """Unpickle a python object (created with pickleit)
    
    filename : filename to pickle to"""
    o = []
    f = open(filename, 'rb')
    while(1):
        try:
            o.append(pickle.load(f))
        except EOFError:
            f.close()
            return o

    return None

def makePanelPlot(n = 3, fig = None, 
                  xlmargin = 0.15, ytmargin = 0.10,
                  xrmargin = 0.05, ybmargin = 0.10,
                  ylabels = True):
    """Make a multi panel plot from matplotlib

    n : number of panels
    fig : figure object to use (If None creates new figure)
    xmargin : margin at x-axis
    ymargin : margin at y-axis

    """
    
    if fig is None:
        fig = pl.figure(figsize = [6, 6 * golden_mean * n])
    
    xsize = (1. - (xlmargin + xrmargin)) 
    ysize = (1. - (ybmargin + ytmargin)) / n

    pos = np.array([xlmargin, ybmargin, xsize, ysize])

    allax = []
    for x in range(n):
        ax = fig.add_axes(pos + np.array([0, ysize * x, 0, 0]))
        if x > 0:
            # Remove ticklabels
            ax.xaxis.set_ticklabels("")
        allax.append(ax)

    return allax

def makeNicePlot(ax, xint = 5, yint = 5, mxint = 4, myint = 4):
    """Make nice plot by setting all border widths"""

    # Some constants

    #ax.axesFrame.set_linewidth(2)
    [i.set_linewidth(2) for i in ax.spines.itervalues()]

    ax.xaxis.label.set_fontsize(18)
    ax.yaxis.label.set_fontsize(18)

    if xint:
        ax.xaxis.set_major_locator(MaxNLocator(mxint))
        ax.xaxis.set_minor_locator(MaxNLocator(mxint * xint))
    if yint:
        ax.yaxis.set_major_locator(MaxNLocator(myint))
        ax.yaxis.set_minor_locator(MaxNLocator(myint * yint))

    for tick in ax.xaxis.get_major_ticks() + ax.yaxis.get_major_ticks():
        tick.tick1line.set_markersize(10)
        tick.tick2line.set_markersize(10)
        tick.tick1line.set_markeredgewidth(2)
        tick.tick2line.set_markeredgewidth(2)
        
        tick.label1.set_fontsize(16)

    for tick in ax.xaxis.get_minor_ticks() + ax.yaxis.get_minor_ticks():
        tick.tick1line.set_markersize(8)
        tick.tick2line.set_markersize(8)
        tick.tick1line.set_markeredgewidth(1)
        tick.tick2line.set_markeredgewidth(1)

def setImageRange(data, limits, bins = 100):
    
    h,b = np.histogram(data, bins = bins)
    b = np.arange(data.min(), data.max(), 
                  (data.max() - data.min()) / bins)
    com = (h * np.arange(h.size)).sum() /  h.sum()
    limits = (np.array(limits) / 100.0) * bins

    if (com - limits[0]) < 0:
        dmin = data.min()
    else:
        dmin = b[int(com - limits[0])]
    
    if (com + limits[1]) >= bins:
        dmax = data.max()
    else:
        dmax = b[int(com + limits[1])]

    return dmin, dmax