# setup for pylal
try:
    from setuptools import setup
    from setuptools.command import install
except ImportError as e:
    from distutils.core import setup
    from distutils.command import install

import os
from misc import generate_vcs_info as gvcsi
from distutils.core import Extension
from distutils.errors import DistutilsError
from distutils.command import build
from distutils import log
from distutils.file_util import write_file
import subprocess
import sys
import time
from numpy.lib.utils import get_include as numpy_get_include

class PkgConfig(object):
    def __init__(self, names):
        def stripfirsttwo(string):
            return string[2:]
        self.libs = map(stripfirsttwo, os.popen("pkg-config --libs-only-l %s" % names).read().split())
        self.libdirs = map(stripfirsttwo, os.popen("pkg-config --libs-only-L %s" % names).read().split())
        self.incdirs = map(stripfirsttwo, os.popen("pkg-config --cflags-only-I %s" % names).read().split())
        self.extra_cflags = os.popen("pkg-config --cflags-only-other %s" % names).read().split()

gsl_pkg_config = PkgConfig("gsl")
lal_pkg_config = PkgConfig("lal")
lalsupport_pkg_config = PkgConfig("lalsupport")
# FIXME:  works for GCC only!!!
lal_pkg_config.extra_cflags += ["-std=c99"]
lalmetaio_pkg_config = PkgConfig("lalmetaio")
lalsimulation_pkg_config = PkgConfig("lalsimulation")
lalinspiral_pkg_config = PkgConfig("lalinspiral")

class pylal_install(install.install):
    def run(self):
        etcdirectory = os.path.join(self.install_data, 'etc')
        if not os.path.exists(etcdirectory):
            os.makedirs(etcdirectory)

        filename = os.path.join(etcdirectory, 'pylal-user-env.sh')
        self.execute(write_file,
                     (filename, [self.extra_dirs]),
                     "creating %s" % filename)

        env_file = open(filename, 'w')
        print >> env_file, "PATH=" + self.install_scripts + ":$PATH"
        print >> env_file, "PYTHONPATH=" + self.install_libbase + ":$PYTHONPATH"
        print >> env_file, "export PYTHONPATH"
        print >> env_file, "export PATH"
        env_file.close()

        #try:
        #    install.install.do_egg_install(self)
        #except DistutilsError as err:
        #    print err
        #else:
        install.install.run(self)
            
def write_build_info():
    """
    Get VCS info from misc/generate_vcs_info.py and add build information.
    Substitute these into misc/git_version.py.in to produce
    pylal/git_version.py.
    """
    date = branch = tag = author = committer = status = builder_name = build_date = ""
    id = "0.9.6"
    
    try:
        v = gvcsi.generate_git_version_info()
        id, date, branch, tag, author = v.id, v.date, b.branch, v.tag, v.author
        committer, status = v.committer, v.status

        # determine current time and treat it as the build time
        build_date = time.strftime('%Y-%m-%d %H:%M:%S +0000', time.gmtime())

        # determine builder
        retcode, builder_name = gvcsi.call_out(('git', 'config', 'user.name'))
        if retcode:
            builder_name = "Unknown User"
        retcode, builder_email = gvcsi.call_out(('git', 'config', 'user.email'))
        if retcode:
            builder_email = ""
        builder = "%s <%s>" % (builder_name, builder_email)
    except:
        pass

    sed_cmd = ('sed',
        '-e', 's/@ID@/%s/' % id,
        '-e', 's/@DATE@/%s/' % date,
        '-e', 's/@BRANCH@/%s/' % branch,
        '-e', 's/@TAG@/%s/' % tag,
        '-e', 's/@AUTHOR@/%s/' % author,
        '-e', 's/@COMMITTER@/%s/' % committer,
        '-e', 's/@STATUS@/%s/' % status,
        '-e', 's/@BUILDER@/%s/' % builder_name,
        '-e', 's/@BUILD_DATE@/%s/' % build_date,
        'misc/git_version.py.in')

    # FIXME: subprocess.check_call becomes available in Python 2.5
    sed_retcode = subprocess.call(sed_cmd,
        stdout=open('pylal/git_version.py', 'w'))
    if sed_retcode:
        raise gvcsi.GitInvocationError
    return id


version = write_build_info()
log.info("Generated pylal/git_version.py")

setup(
    name = "pycbc-pylal",
    version = version,
    author = 'Ligo Virgo Collaboration - PyCBC team',
    author_email = 'alex.nitz@ligo.org',
    url = 'https://github.com/ligo-cbc/pycbc-pylal',
    download_url = 'https://github.com/a-r-williamson/pycbc-pylal/archive/v0.9.6.tar.gz',
    release = True,
    description = "legacy support python ligo algorithm library",
    license = "See file LICENSE",
    cmdclass = {'install' : pylal_install,},
    packages = [
        "pylal",
        "pylal.dq",
        "pylal.xlal",
        "pylal.xlal.datatypes"
    ],
    ext_modules = [
        Extension(
            "pylal.tools",
            ["src/tools.c"],
            include_dirs = lal_pkg_config.incdirs + lalmetaio_pkg_config.incdirs + lalinspiral_pkg_config.incdirs,
            libraries = lal_pkg_config.libs + lalinspiral_pkg_config.libs,
            library_dirs = lal_pkg_config.libdirs + lalinspiral_pkg_config.libdirs,
            runtime_library_dirs = lal_pkg_config.libdirs + lalinspiral_pkg_config.libdirs,
            extra_compile_args = lal_pkg_config.extra_cflags
        ),
        Extension(
            "pylal.xlal.datatypes.lalunit",
            ["src/xlal/datatypes/lalunit.c"],
            include_dirs = lal_pkg_config.incdirs + ["src/xlal/datatypes"],
            libraries = lal_pkg_config.libs,
            library_dirs = lal_pkg_config.libdirs,
            runtime_library_dirs = lal_pkg_config.libdirs,
            extra_compile_args = lal_pkg_config.extra_cflags
        ),
        Extension(
            "pylal.xlal.datatypes.ligotimegps",
            ["src/xlal/datatypes/ligotimegps.c"],
            include_dirs = lal_pkg_config.incdirs + ["src/xlal/datatypes"],
            libraries = lal_pkg_config.libs,
            library_dirs = lal_pkg_config.libdirs,
            runtime_library_dirs = lal_pkg_config.libdirs,
            extra_compile_args = lal_pkg_config.extra_cflags
        ),
        Extension(
            "pylal.xlal.datatypes.simburst",
            ["src/xlal/datatypes/simburst.c", "src/xlal/misc.c"],
            include_dirs = lal_pkg_config.incdirs + lalmetaio_pkg_config.incdirs + ["src/xlal", "src/xlal/datatypes"],
            libraries = lal_pkg_config.libs,
            library_dirs = lal_pkg_config.libdirs,
            runtime_library_dirs = lal_pkg_config.libdirs,
            extra_compile_args = lal_pkg_config.extra_cflags + ["-DPY_SSIZE_T_CLEAN"]
        ),
        Extension(
            "pylal.xlal.datatypes.siminspiraltable",
            ["src/xlal/datatypes/siminspiraltable.c", "src/xlal/misc.c"],
            include_dirs = lal_pkg_config.incdirs + lalmetaio_pkg_config.incdirs+ ["src/xlal", "src/xlal/datatypes"],
            libraries = lal_pkg_config.libs,
            library_dirs = lal_pkg_config.libdirs,
            runtime_library_dirs = lal_pkg_config.libdirs,
            extra_compile_args = lal_pkg_config.extra_cflags + ["-DPY_SSIZE_T_CLEAN"]
        ),
        Extension(
            "pylal.xlal.datatypes.snglburst",
            ["src/xlal/datatypes/snglburst.c", "src/xlal/misc.c"],
            include_dirs = lal_pkg_config.incdirs + lalmetaio_pkg_config.incdirs + ["src/xlal", "src/xlal/datatypes"],
            libraries = lal_pkg_config.libs,
            library_dirs = lal_pkg_config.libdirs,
            runtime_library_dirs = lal_pkg_config.libdirs,
            extra_compile_args = lal_pkg_config.extra_cflags + ["-DPY_SSIZE_T_CLEAN"]
        ),
        Extension(
            "pylal.xlal.datatypes.snglinspiraltable",
            ["src/xlal/datatypes/snglinspiraltable.c", "src/xlal/misc.c"],
            include_dirs = lal_pkg_config.incdirs + lalmetaio_pkg_config.incdirs + ["src/xlal", "src/xlal/datatypes"],
            libraries = lal_pkg_config.libs,
            library_dirs = lal_pkg_config.libdirs,
            runtime_library_dirs = lal_pkg_config.libdirs,
            extra_compile_args = lal_pkg_config.extra_cflags + ["-DPY_SSIZE_T_CLEAN"]
        ),
        Extension(
            "pylal.xlal.datatypes.snglringdowntable",
            ["src/xlal/datatypes/snglringdowntable.c", "src/xlal/misc.c"],
            include_dirs = lal_pkg_config.incdirs + lalmetaio_pkg_config.incdirs + ["src/xlal", "src/xlal/datatypes"],
            libraries = lal_pkg_config.libs,
            library_dirs = lal_pkg_config.libdirs,
            runtime_library_dirs = lal_pkg_config.libdirs,
            extra_compile_args = lal_pkg_config.extra_cflags
        ),
        Extension(
            "pylal.xlal.date",
            ["src/xlal/date.c", "src/xlal/misc.c"],
            include_dirs = lal_pkg_config.incdirs + [numpy_get_include(), "src/xlal"],
            libraries = lal_pkg_config.libs,
            library_dirs = lal_pkg_config.libdirs,
            runtime_library_dirs = lal_pkg_config.libdirs,
            extra_compile_args = lal_pkg_config.extra_cflags
        ),
        Extension(
            "pylal.xlal.tools",
            ["src/xlal/tools.c", "src/xlal/misc.c"],
            include_dirs = lal_pkg_config.incdirs + lalmetaio_pkg_config.incdirs + lalinspiral_pkg_config.incdirs + [numpy_get_include(), "src/xlal"],
            libraries = lal_pkg_config.libs + lalinspiral_pkg_config.libs,
            library_dirs = lal_pkg_config.libdirs + lalinspiral_pkg_config.libdirs,
            runtime_library_dirs = lal_pkg_config.libdirs + lalinspiral_pkg_config.libdirs,
            extra_compile_args = lal_pkg_config.extra_cflags
        ),
        Extension(
            "pylal.xlal.datatypes.complex16frequencyseries",
            ["src/xlal/datatypes/complex16frequencyseries.c"],
            include_dirs = lal_pkg_config.incdirs + [numpy_get_include(), "src/xlal/datatypes"],
            libraries = lal_pkg_config.libs,
            library_dirs = lal_pkg_config.libdirs,
            runtime_library_dirs = lal_pkg_config.libdirs,
            extra_compile_args = lal_pkg_config.extra_cflags
        ),
        Extension(
            "pylal.xlal.datatypes.complex16timeseries",
            ["src/xlal/datatypes/complex16timeseries.c"],
            include_dirs = lal_pkg_config.incdirs + [numpy_get_include(), "src/xlal/datatypes"],
            libraries = lal_pkg_config.libs,
            library_dirs = lal_pkg_config.libdirs,
            runtime_library_dirs = lal_pkg_config.libdirs,
            extra_compile_args = lal_pkg_config.extra_cflags
        ),
        Extension(
            "pylal.xlal.datatypes.real8frequencyseries",
            ["src/xlal/datatypes/real8frequencyseries.c"],
            include_dirs = lal_pkg_config.incdirs + [numpy_get_include(), "src/xlal/datatypes"],
            libraries = lal_pkg_config.libs,
            library_dirs = lal_pkg_config.libdirs,
            runtime_library_dirs = lal_pkg_config.libdirs,
            extra_compile_args = lal_pkg_config.extra_cflags
        ),
        Extension(
            "pylal.xlal.datatypes.real8timeseries",
            ["src/xlal/datatypes/real8timeseries.c"],
            include_dirs = lal_pkg_config.incdirs + [numpy_get_include(), "src/xlal/datatypes"],
            libraries = lal_pkg_config.libs,
            library_dirs = lal_pkg_config.libdirs,
            runtime_library_dirs = lal_pkg_config.libdirs,
            extra_compile_args = lal_pkg_config.extra_cflags
        ),
        Extension(
            "pylal._spawaveform",
            ["src/_spawaveform.c"],
            include_dirs = lal_pkg_config.incdirs + lalinspiral_pkg_config.incdirs + [numpy_get_include()],
            libraries = lal_pkg_config.libs + lalinspiral_pkg_config.libs,
            library_dirs = lal_pkg_config.libdirs + lalinspiral_pkg_config.libdirs,
            runtime_library_dirs = lal_pkg_config.libdirs + lalinspiral_pkg_config.libdirs,
            extra_compile_args = lal_pkg_config.extra_cflags
        ),
        Extension(
            "pylal.inspiral_metric",
            ["src/inspiral_metric.c", "src/xlal/misc.c"],
            include_dirs = lal_pkg_config.incdirs + lalinspiral_pkg_config.incdirs + ["src/xlal/", "src/xlal/datatypes/"],
            libraries = lal_pkg_config.libs + lalinspiral_pkg_config.libs,
            library_dirs = lal_pkg_config.libdirs + lalinspiral_pkg_config.libdirs,
            runtime_library_dirs = lal_pkg_config.libdirs + lalinspiral_pkg_config.libdirs,
            extra_compile_args = lal_pkg_config.extra_cflags
        ),
    ],
    scripts = [
        os.path.join("bin", "ligolw_cbc_align_total_spin"),
        os.path.join("bin", "ligolw_cbc_cluster_coincs"),
        os.path.join("bin", "ligolw_cbc_dbinjfind"),
        os.path.join("bin", "ligolw_cbc_hardware_inj_page"),
        os.path.join("bin", "ligolw_cbc_jitter_skyloc"),
        os.path.join("bin", "ligolw_cbc_plotcumhist"),
        os.path.join("bin", "ligolw_cbc_plotfm"),
        os.path.join("bin", "ligolw_cbc_plotifar"),
        os.path.join("bin", "ligolw_cbc_plotslides"),
        os.path.join("bin", "ligolw_cbc_printlc"),
        os.path.join("bin", "ligolw_cbc_printmissed"),
        os.path.join("bin", "ligolw_cbc_printsims"),
        os.path.join("bin", "ligolw_cbc_sstinca"),
        os.path.join("bin", "pylal_cbc_cohptf_efficiency"),
        os.path.join("bin", "pylal_cbc_cohptf_html_summary"),
        os.path.join("bin", "pylal_cbc_cohptf_injcombiner"),
        os.path.join("bin", "pylal_cbc_cohptf_injfinder"),
        os.path.join("bin", "pylal_cbc_cohptf_inspiral_horizon"),
        os.path.join("bin", "pylal_cbc_cohptf_sbv_plotter"),
        os.path.join("bin", "pylal_cbc_cohptf_trig_cluster"),
        os.path.join("bin", "pylal_cbc_cohptf_trig_combiner"),
        os.path.join("bin", "pylal_cbc_minifollowups"),
        os.path.join("bin", "pylal_cbc_plotinspiral"),
        os.path.join("bin", "pylal_cbc_plotinspiralrange"),
        os.path.join("bin", "pylal_cbc_plotnumtemplates"),
        os.path.join("bin", "pylal_cbc_sink"),
        os.path.join("bin", "pylal_cbc_svim")
        ],
)
