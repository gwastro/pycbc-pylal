# Copyright (C) 2008  Nickolas Fotopoulos
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 2 of the License, or (at your
# option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General
# Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
"""
This module is intended to store generic, reusable, sub-classable plot classes
to minimize formulaic copying and pasting.
"""

from __future__ import division

__author__ = "Nickolas Fotopoulos <nvf@gravity.phys.uwm.edu>"

import itertools

import numpy
import pylab
import re
import copy
import ConfigParser

from glue import iterutils

from pylal import viz

# general defaults
pylab.rc("lines", markersize=12)
pylab.rc("text", usetex=True)

# Utility function
def float_to_latex(x, format="%.2g"):
    """
    Convert a floating point number to a latex representation.  In particular,
    scientific notation is handled gracefully: e -> 10^
    """
    base_str = format % x
    if "e" not in base_str:
        return base_str
    mantissa, exponent = base_str.split("e")
    exponent = exponent.lstrip("0+")
    if mantissa == "1":
        return r"10^{%s}" % exponent
    else:
        return r"%s\times 10^{%s}" % (mantissa, exponent)

##############################################################################
# abstract classes

class BasicPlot(object):
    """
    A very default meta-class to almost any plot you might want to make.
    It provides basic initialization, a savefig method, and a close method.
    It is up to developers to subclass BasicPlot and fill in the add_content()
    and finalize() methods.
    """
    def __init__(self, xlabel="", ylabel="", title="", subtitle="", **kwargs):
        """
        Basic plot initialization.  A subclass can override __init__ and call
        this one (plotutils.BasicPlot.__init__(self, *args, **kwargs)) and
        then initialize variables to hold data to plot and labels.
        """
        self.fig = pylab.figure(**kwargs)
        self.ax = self.fig.add_subplot(111)

        self.ax.set_xlabel(xlabel)
        self.ax.set_ylabel(ylabel)
        if subtitle:
            self.ax.set_title(title, x=0.5, y=1.03)
            self.ax.text(0.5, 1.035, subtitle, horizontalalignment='center',
                         transform=self.ax.transAxes, verticalalignment='top')
        else:
            self.ax.set_title(title)
        self.ax.grid(True)

    def add_content(self, data, label="_nolabel_"):
        """
        Stub.  Replace with a method that appends values or lists of values
        to self.data_sets and appends labels to self.data_labels.  Feel free
        to accept complicated inputs, but try to store only the raw numbers
        that will enter the plot.
        """
        raise NotImplementedError

    def finalize(self):
        """
        Stub.  Replace with a function that creates and makes your plot
        pretty.  Do not do I/O here.
        """
        raise NotImplementedError

    def savefig(self, *args, **kwargs):
        self.fig.savefig(*args, **kwargs)

    def close(self):
        """
        Close the plot and release its memory.
        """
        pylab.close(self.fig)

    def add_legend_if_labels_exist(self, *args, **kwargs):
        """
        Create a legend if there are any non-trivial labels.
        """

        # extract useable parameters that don't get passed to ax.legend
        alpha      = kwargs.pop("alpha", None)
        linewidth  = kwargs.pop("linewidth", None)
        markersize = kwargs.pop("markersize", None)

        # make legend if any data set requires it
        for plot_kwargs in self.kwarg_sets:
            if "label" in plot_kwargs and \
                not plot_kwargs["label"].startswith("_"):
                # generate legend
                self.ax.legend(*args, **kwargs)
                # apply extra formatting
                leg   = self.ax.get_legend()
                frame = leg.get_frame()
                if alpha:
                    frame.set_alpha(alpha)
                if linewidth:
                    for l in leg.get_lines():
                        l.set_linewidth(linewidth)
                return

##############################################################################
# utility functions

def default_colors():
    """
    An infinite iterator of some default colors.
    """
    return itertools.cycle(('b', 'g', 'r', 'c', 'm', 'y', 'k'))

def default_symbols():
    """
    An infinite iterator of some default symbols.
    """
    return itertools.cycle(('x', '^', 'D', 'H', 'o', '1', '+'))

def determine_common_bin_limits(data_sets, default_min=0, default_max=0):
    """
    Given a some nested sequences (e.g. list of lists), determine the largest
    and smallest values over the data sets and determine a common binning.
    """
    max_stat = max(list(iterutils.flatten(data_sets)) + [-numpy.inf])
    min_stat = min(list(iterutils.flatten(data_sets)) + [numpy.inf])
    if numpy.isinf(-max_stat):
        max_stat = default_max
    if numpy.isinf(min_stat):
        min_stat = default_min
    return min_stat, max_stat

def method_callable_once(f):
    """
    Decorator to make a method complain if called more than once.
    """
    def _new(self, *args, **kwargs):
        attr = "_" + f.__name__ + "_already_called"
        if hasattr(self, attr) and getattr(self, attr):
            raise ValueError, f.__name__ + " can only be called once"
        setattr(self, attr, True)
        return f(self, *args, **kwargs)
    _new.__doc__ == f.__doc__
    _new.__name__ = f.__name__
    return _new

_dq_params = {"text.usetex": True,   "text.verticalalignment": "center",
              "lines.linewidth": 2,  "xtick.labelsize": 16,
              "ytick.labelsize": 16, "axes.titlesize": 22,
              "axes.labelsize": 16,  "axes.linewidth": 1,
              "grid.linewidth": 1,   "legend.fontsize": 16,
              "legend.loc": "best",  "figure.figsize": [12,6],
              "figure.dpi": 80,      "image.origin": 'lower',
              "axes.grid": True,     "axes.axisbelow": False}

def set_rcParams(params=_dq_params):
    """
    Update pylab plot parameters, defaulting to parameters for DQ-style trigger
    plots.
    """

    # customise plot appearance
    pylab.rcParams.update(params)

def display_name(columnName):
    """
    Format the string columnName (e.g. xml table column) into latex format for
    an axis label. Formats known acronyms, greek letters, units, subscripts, and
    some miscellaneous entries.

    Examples:

    >>> display_name('snr')
    'SNR'
    >>> display_name('bank_chisq_dof')
    'Bank $\\chi^2$ DOF'
    >>> display_name('hoft')
    '$h(t)$'

    Arguments:

      columnName : str
        string to format
    """

    # define known acronyms
    acro    = ['snr', 'ra','dof', 'id', 'ms', 'far']
    # define greek letters
    greek   = ['alpha', 'beta', 'gamma', 'delta', 'epsilon', 'zeta', 'eta',\
               'theta', 'iota', 'kappa', 'lamda', 'mu', 'nu', 'xi',\
               'pi', 'rho', 'sigma', 'tau', 'upsilon', 'phi', 'chi', 'psi',\
               'omega']
    # define known units
    unit    = {'ns':'ns', 'hz':'Hz'}
    # define known subscripts
    sub     = ['flow', 'fhigh', 'hrss', 'mtotal', 'mchirp']
    # define miscellaneous entries
    misc    = {'hoft': '$h(t)$'}

    if len(columnName)==1:
        return columnName

    # find all words, preserving acronyms in upper case
    words = []
    for w in re.split('\s', columnName):
        if w[:-1].isupper(): words.append(w)
        else:           words.extend(re.split('_', w))

    # parse words
    for i,w in enumerate(words):
        if w.startswith('\\'):
            pass
        wl = w.lower()
        # get miscellaneous definitions
        if wl in misc.keys():
            words[i] = misc[wl]
        # get acronym in lower case
        elif wl in acro:
            words[i] = w.upper()
        # get numerical unit
        elif wl in unit:
            words[i] = '(%s)' % unit[wl]
        # get character with subscript text
        elif wl in sub:
            words[i] = '%s$_{\mbox{\\small %s}}$' % (w[0], w[1:])
        # get greek word
        elif wl in greek:
            words[i] = '$\%s$' % w
        # get starting with greek word
        elif re.match('(%s)' % '|'.join(greek), w):
            if w[-1].isdigit():
                words[i] = '$\%s_{%s}$''' %tuple(re.findall(r"[a-zA-Z]+|\d+",w))
            elif wl.endswith('sq'):
                words[i] = '$\%s^2$' % w[:-2]
        # get everything else
        else:
            if w[:-1].isupper():
                words[i] = w
            else:
                words[i] = w.title()
            # escape underscore
            words[i] = re.sub('(?<!\\\\)_', '\_', words[i])

    return ' '.join(words)

def add_colorbar(ax, mappable=None, visible=True, log=False, clim=None,\
                 label=None, **kwargs):
    """
    Adds a figure colorbar to the given Axes object ax, based on the values
    found in the mappable object. If visible=True, returns the Colorbar object, 
    otherwise, no return.

    Arguments:

        ax : matplotlib.axes.AxesSubplot
            axes object beside which to draw colorbar

    Keyword arguments:

        mappable : [ matplotlib.image.Image | matplotlib.contour.ContourSet... ]
            image object from which to map colorbar values
        visible : [ True | False]
            add colorbar to figure, or simply resposition ax as if to draw one
        log : [ True | False ]
            use logarithmic scale for colorbar
        clim : tuple
            (vmin, vmax) pair for limits of colorbar
        label : str
            label string for colorbar

    All other keyword arguments will be passed to pylab.colorbar. Logarithmic
    colorbars can be created by plotting log10 of the data and setting log=True.
    """

    div = make_axes_locatable(ax)
    cax = div.new_horizontal("3%", pad="1%")
    if not visible:
        return
    else:
        div._fig.add_axes(cax)
    
    # set default tex formatting for colorbar
    if pylab.rcParams['text.usetex']:
        kwargs.setdefault('format',\
            pylab.matplotlib.ticker.FuncFormatter(lambda x,pos: "$%s$"\
                                                  % float_to_latex(x)))

    # set limits
    if not clim:
        cmin = min([c.get_array().min() for c in ax.collections+ax.images])
        cmax = max([c.get_array().max() for c in ax.collections+ax.images])
        clim = [cmin, cmax]
    if log:
        kwargs.setdefault("ticks", numpy.logspace(numpy.log10(clim[0]),\
                                                  numpy.log10(clim[1]), num=9,\
                                                  endpoint=True))
    else:
        kwargs.setdefault("ticks", numpy.linspace(clim[0], clim[1], num=9,\
                                                  endpoint=True))

    # find mappable with lowest maximum
    if not mappable:
        if len(ax.collections+ax.images) == 0:
            norm = log and pylab.matplotlib.colors.LogNorm() or none
            mappable = ax.scatter([1], [1], c=[clim[0]], vmin=clim[0],\
                                   vmax=clim[1], visible=False, norm=norm)
        else:
            minindex = numpy.asarray([c.get_array().min() for c in\
                                      ax.collections+ax.images]).argmin()
            mappable = (ax.collections+ax.images)[minindex]

    # make sure the mappable has at least one element
    if mappable.get_array() is None:
        norm = log and pylab.matplotlib.colors.LogNorm() or none
        mappable = ax.scatter([1], [1], c=[clim[0]], vmin=clim[0],\
                               vmax=clim[1], visible=False, norm=norm)
    
    # generate colorbar
    colorbar = ax.figure.colorbar(mappable, cax=cax, **kwargs)
    if clim: colorbar.set_clim(clim)
    if label: colorbar.set_label(label)
    colorbar.draw_all()

    return colorbar

def parse_plot_config(cp, section):
    """
    Parser ConfigParser.ConfigParser section for plotting parameters. Returns
    a dict that can be passed to any plotutils.plot_xxx function in **kwargs
    form. Set ycolumn to 'hist' or 'rate' to generate those types of plots.

    Arguments:

        cp : ConfigParser.ConfigParser
            INI file object from which to read
        section : str
            section name to read for options

    Basic parseable options:

        xcolumn : str
            parameter to plot on x-axis    
        ycolumn : str
            parameter to plot on y-axis    
        zcolumn : str
            parameter to plot on z-axis    
        rank-by : str
            parameter by which to rank elements
        xlim : list
            [xmin, xmax] pair for x-axis limits
        ylim : list
            [ymin, ymax] pair for y-axis limits
        zlim : list
            [zmin, zmax] pair for z-axis limits
        clim : list
            [cmin, cmax] pair for colorbar limits
        logx : [ True | False ]
            plot x-axis in log scale
        logy : [ True | False ]
            plot y-axis in log scale
        logz : [ True | False ]
            plot z-axis in log scale

    Trigger plot options:

        detchar-style : [ True | False ]
            use S6-style plotting: low snr triggers small with no edges
        detchar-style-theshold : float
            z-column threshold at below which to apply detchar-style

    Trigger rate plot options:

        bins : str
            semi-colon-separated list of comma-separated bins for rate plot

    Histogram options:

        cumulative : [ True | False ]
            plot cumulative counts in histogram
        rate : [ True | False ]
            plot histogram counts as rate
        num-bins : int
            number of bins for histogram
        fill : [ True | False ]
            plot solid colour underneath histogram curve
        color-bins : str
            semi-colon-separated list of comma-separated bins for colorbar
            histogram

    Data plot options:

        zero-indicator : [ True | False ]
            draw vertical dashed red line at t=0

    Other options:

        greyscale : [ True | False ]
            save plot in black-and-white
        bbox-inches : 'tight'
            save figure with tight bounding box around Axes
        calendar-time : [ True | False ]
            plot time axis with date and time instead of time from zero.
    """
    params = dict()

    # define option types
    pairs    = ['xlim', 'ylim', 'zlim', 'colorlim']
    pairlist = ['bins', 'color-bins']
    booleans = ['logx', 'logy', 'logz', 'cumulative', 'rate', 'detchar-style',\
                'greyscale', 'zero-indicator', 'normalized', 'fill',\
                'calendar-time', 'bar']
    floats   = ['detchar-style-threshold', 'dcthreshold']
    ints     = ['num-bins']

    # construct param dict
    for key,val in cp.items(section, raw=True):
        if val == None: continue
        # remove quotes
        val = val.rstrip('"').strip('"')
        # format key key
        hkey = re.sub('_', '-', key)
        ukey = re.sub('-', '_', key)
        # get limit pairs
        if hkey in pairs:
            params[ukey] = map(float, val.split(','))
        # get bins
        elif hkey in pairlist:
            params[ukey] = map(lambda p: map(float,p.split(',')),val.split(';'))
        # get booleans
        elif hkey in booleans:
            params[ukey] = cp.getboolean(section, key)
        # get float values
        elif hkey in floats:
            params[ukey] = float(val)
        # get float values
        elif hkey in ints:
            params[ukey] = int(val)
        # else construct strings
        else:
            params[ukey] = str(val)

    return params

def log_transform(lin_range):
    """
    Return the logarithmic ticks and labels corresponding to the
    input lin_range.
    """
    log_range = numpy.log10(lin_range)
    slope = (lin_range[1] - lin_range[0]) / (log_range[1] - log_range[0])
    inter = lin_range[0] - slope * log_range[0]
    tick_range = [tick for tick in range(int(log_range[0] - 1.0),\
                                         int(log_range[1] + 1.0))\
                  if tick >= log_range[0] and tick<=log_range[1]]
    ticks = [inter + slope * tick for tick in tick_range]
    labels = ["${10^{%d}}$" % tick for tick in tick_range]
    minorticks = []
    for i in range(len(ticks[:-1])):
        minorticks.extend(numpy.logspace(numpy.log10(ticks[i]),\
                                         numpy.log10(ticks[i+1]), num=10)[1:-1])
    return ticks, labels, minorticks

def time_axis_unit(duration):
    """
    Work out renormalisation for the time axis, makes the label more
    appropriate. Returns unit (in seconds) and string descriptor.

    Example:

    >>> time_axis_unit(100)
    (1, 'seconds')

    >>> time_axis_unit(604800)
    (86400, 'days')

    Arguments:

        duration : float
            plot duration to normalise
    """
    if (duration) < 1000:
        return 1,"seconds"
    elif (duration) < 20000:
        return 60,"minutes"
    elif (duration) >= 20000 and (duration) < 604800:
        return 3600,"hours"
    elif (duration) < 8640000:
        return 86400,"days"
    else:
        return 2592000,"months"

def set_time_ticks(ax):
    """
    Quick utility to set better formatting for ticks on a time axis.
    """
    xticks = ax.get_xticks()
    if len(xticks)>1 and xticks[1]-xticks[0]==5:
        ax.xaxis.set_major_locator(pylab.matplotlib.ticker.MultipleLocator(base=2))
    return

def set_minor_ticks(ax, x=True, y=True):
    """
    Labels first minor tick in the case that there is only a single major
    tick label visible.
    """

    def even(x, pos):
        if int(str(int(x*10**8))[0]) % 2:
            return ""
        elif pylab.rcParams["text.usetex"]:
            return "$%s$" % float_to_latex(x)
        else:
            return str(int(x))

    # xticks
    if x:
        ticks = list(ax.get_xticks())
        xlim  = ax.get_xlim()
        for i,tick in enumerate(ticks[::-1]):
            if not xlim[0] <= tick <= xlim[1]:
                ticks.pop(-1)
        if len(ticks) <= 1:
            ax.xaxis.set_minor_formatter(pylab.FuncFormatter(even))

    # yticks
    if y:
        ticks = list(ax.get_yticks())
        ylim  = ax.get_ylim()
        for i,tick in enumerate(ticks[::-1]):
            if not ylim[0] <= tick <= ylim[1]:
                ticks.pop(-1)
        if len(ticks)<=1:
            ax.yaxis.set_minor_formatter(pylab.FuncFormatter(even))

    return

##############################################################################
# generic, but usable classes

class CumulativeHistogramPlot(BasicPlot):
    """
    Cumulative histogram of foreground that also has a shaded region,
    determined by the mean and standard deviation of the background
    population coincidence statistics.
    """
    def __init__(self, *args, **kwargs):
        BasicPlot.__init__(self, *args, **kwargs)
        self.fg_data_sets = []
        self.fg_kwarg_sets = []
        self.bg_data_sets = []
        self.bg_kwargs = {}

    def add_content(self, fg_data_set, **kwargs):
        self.fg_data_sets.append(fg_data_set)
        self.fg_kwarg_sets.append(kwargs)

    def add_background(self, bg_data_sets, **kwargs):
        self.bg_data_sets.extend(bg_data_sets)
        self.bg_kwargs = kwargs

    @method_callable_once
    def finalize(self, num_bins=20, normalization=1):
        epsilon = 1e-8

        # determine binning
        min_stat, max_stat = determine_common_bin_limits(\
            self.fg_data_sets + self.bg_data_sets)
        bins = numpy.linspace(min_stat, max_stat, num_bins + 1, endpoint=True)
        bins_bg = numpy.append(bins, float('Inf'))
        dx = bins[1] - bins[0]

        # plot foreground
        for data_set, plot_kwargs in \
            itertools.izip(self.fg_data_sets, self.fg_kwarg_sets):
            # make histogram
            y, x = numpy.histogram(data_set, bins=bins)
            y = y[::-1].cumsum()[::-1]
            x = x[:-1]

            # plot
            y = numpy.array(y, dtype=numpy.float32)
            y[y <= epsilon] = epsilon
            self.ax.plot(x + dx/2, y*normalization, **plot_kwargs)

        # shade background region
        if len(self.bg_data_sets) > 0:
            # histogram each background instance separately and take stats
            hist_sum = numpy.zeros(len(bins), dtype=float)
            sq_hist_sum = numpy.zeros(len(bins), dtype=float)
            for instance in self.bg_data_sets:
                # make histogram
	        y, x = numpy.histogram(instance, bins=bins_bg)
                x = numpy.delete(x, -1)
                y = y[::-1].cumsum()[::-1]
                hist_sum += y
                sq_hist_sum += y*y

            # get statistics
            N = len(self.bg_data_sets)
            means = hist_sum / N
            stds = numpy.sqrt((sq_hist_sum - hist_sum*means) / (N - 1))

            # plot mean
            means[means <= epsilon] = epsilon
            self.ax.plot(x + dx/2, means*normalization, 'r+', **self.bg_kwargs)

            # shade in the area
            if "label" in self.bg_kwargs:
                self.bg_kwargs["label"] = r"$\mu_\mathrm{%s}$" \
                    % self.bg_kwargs["label"]
            self.bg_kwargs.setdefault("alpha", 0.3)
            self.bg_kwargs.setdefault("facecolor", "y")
            upper = means + stds
            lower = means - stds
            lower[lower <= epsilon] = epsilon
            tmp_x, tmp_y = viz.makesteps(bins, upper, lower)
            self.ax.fill(tmp_x, tmp_y*normalization, **self.bg_kwargs)

        # make semilogy plot
        self.ax.set_yscale("log")

        # adjust plot range
        self.ax.set_xlim((0.9 * min_stat, 1.1 * max_stat))
        possible_ymins = [0.6]
        if len(self.bg_data_sets) > 0:
            possible_ymins.append(0.6 / N)
        else:
            possible_ymins.append(0.6 * normalization)
        self.ax.set_ylim(min(possible_ymins))

        # add legend if there are any non-trivial labels
        self.kwarg_sets = self.fg_kwarg_sets
        self.add_legend_if_labels_exist()

        # decrement reference counts
        del self.kwarg_sets
        del self.fg_data_sets
        del self.fg_kwarg_sets
        del self.bg_data_sets
        del self.bg_kwargs

