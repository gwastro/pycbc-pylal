import cgi
import cgitb ; cgitb.enable()
import math
from matplotlib.patches import Patch
import os
import pylab
import shutil
import sys
import tempfile
import time
import urllib
from xml import sax

from glue import lal
from glue import segments
from glue import segmentsUtils
from glue.ligolw import ligolw
from glue.ligolw import metaio
from glue.ligolw import lsctables
from glue.ligolw import docutils

from pylal import SnglBurstUtils
from pylal.support import XLALUTCToGPS

import eventdisplay

#
# =============================================================================
#
#                             CGI display request
#
# =============================================================================
#

class PlotDescription(object):
	def __init__(self):
		# set defaults
		now = lal.LIGOTimeGPS(XLALUTCToGPS(time.gmtime()))
		self.segment = segments.segment(now, now + (-1 * 3600))
		self.ratewidth = 60.0
		self.freqwidth = 16.0
		self.band = segments.segment(0.0, 2500.0)
		self.set_instrument("H1")
		self.seglist = segments.segmentlist([self.segment])
		self.filename = None
		self.format = None	# force update
		self.set_format("png")
		self.cluster = 0

		return self

	def __del__(self):
		self.remove_tmpfile()

	def remove_tmpfile(self):
		if self.filename:
			os.remove(self.filename)

	def set_format(self, format):
		if format not in ["eps", "png", "svg", "xml"]:
			raise Exception, "unrecognized format %s" % format
		if self.format == format:
			return
		self.format = format
		if format == "eps":
			self.set_extension("eps")
		elif format == "png":
			self.set_extension("png")
		elif format == "svg":
			self.set_extension("svg")
		elif format == "xml":
			self.set_extension("xml")

	def set_extension(self, extension):
		self.remove_tmpfile()
		handle, self.filename = tempfile.mkstemp("." + extension.strip(), "webplot_")
		os.close(handle)

	def set_instrument(self, instrument):
		# update cache name along with instrument
		self.instrument = str(instrument)

	def parse_form(self):
		# parse CGI form
		form = cgi.FieldStorage()

		start = lal.LIGOTimeGPS(form.getfirst("start", str(self.segment[0])))
		duration = lal.LIGOTimeGPS(form.getfirst("dur", str(self.segment.duration())))

		self.segment = segments.segment(start, start + duration)
		self.ratewidth = float(form.getfirst("ratewidth", str(self.ratewidth)))
		self.freqwidth = float(form.getfirst("freqwidth", str(self.freqwidth)))
		self.band = segments.segment(float(form.getfirst("lofreq", str(self.band[0]))), float(form.getfirst("hifreq", str(self.band[1]))))
		self.set_instrument(form.getfirst("inst", self.instrument))
		self.set_format(form.getfirst("format", self.format))
		self.cluster = int(form.getfirst("cluster", "0"))

		return self

	def trig_segment(self):
		# interval in which triggers must be read in order to
		# produce a plot
		return self.segment


#
# =============================================================================
#
#               How to get a table of triggers within a segment
#
# =============================================================================
#

def ElementFilter(name, attrs):
	"""
	Filter for reading only sngl_burst, sim_burst and search_summary
	tables.
	"""
	return lsctables.IsTableProperties(lsctables.SnglBurstTable, name, attrs) or lsctables.IsTableProperties(lsctables.SimBurstTable, name, attrs) or lsctables.IsTableProperties(lsctables.SearchSummaryTable, name, attrs)

def CacheURLs(cachename, seg):
	"""
	Open a trigger cache, and return a list of URLs for files
	intersecting seg.
	"""
	return [c.url for c in map(lal.CacheEntry, file(cachename)) if c.segment.intersects(seg)]

def GetTable(doc, Type):
	"""
	Find and return the table of the given type.
	"""
	tables = lsctables.getTablesByType(doc, Type)
	if len(tables) == 0:
		return lsctables.New(Type)
	if len(tables) == 1:
		return tables[0]
	raise Exception, "files contain incompatible %s tables" % Type.tableName

def gettriggers(plotdesc):
	# load documents
	doc = ligolw.Document()
	handler = docutils.PartialLIGOLWContentHandler(doc, ElementFilter)
	for url in CacheURLs(eventdisplay.cache[plotdesc.instrument], plotdesc.segment):
		try:
			ligolw.make_parser(handler).parse(urllib.urlopen(url))
		except ligolw.ElementError, e:
			raise Exception, "error parsing file %s: %s" % (url, str(e))
	docutils.MergeCompatibleTables(doc)

	# extract tables
	plotdesc.seglist = GetTable(doc, lsctables.SearchSummaryTable).get_inlist().coalesce()
	bursttable = GetTable(doc, lsctables.SnglBurstTable)
	simtable = GetTable(doc, lsctables.SimBurstTable)

	# cluster
	if plotdesc.cluster:
		SnglBurstUtils.ClusterSnglBurstTable(bursttable.rows, SnglBurstUtils.CompareSnglBurstByPeakTimeAndFreq, SnglBurstUtils.SnglBurstCluster, SnglBurstUtils.CompareSnglBurstByPeakTime)

	# remove triggers and injections that lie outside the required segment
	bursttable.filterRows(lambda row: row.get_peak() in plotdesc.trig_segment())
	simtable.filterRows(lambda row: row.get_geocent_peak() in plotdesc.trig_segment())

	return bursttable, simtable


#
# =============================================================================
#
#                                    Output
#
# =============================================================================
#

def SendImage(plotdesc):
	if plotdesc.format == "png":
		print >>sys.stdout, "Content-Type: image/png\n"
	elif plotdesc.format == "eps":
		print >>sys.stdout, "Content-Type: application/postscript\n"
	elif plotdesc.format == "svg":
		print >>sys.stdout, "Content-Type: image/svg+xml\n"
	elif plotdesc.format == "xml":
		print >>sys.stdout, "Content-Type: text/xml\n"
	shutil.copyfileobj(file(plotdesc.filename), sys.stdout)
