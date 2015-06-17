# setup for pylal


import os
from misc import generate_vcs_info as gvcsi
from distutils.core import setup, Extension
from distutils.command import install
from distutils.command import build
from distutils.command import build_py
from distutils.command import sdist
from distutils import log
import subprocess
import sys
import time
from numpy.lib.utils import get_include as numpy_get_include


#
# check python version
#

if sys.version_info[0] != 2 or sys.version_info[1] < 4:
    log.error("Python version is %s.  pylal requires a Python version such that 2.4 <= version < 3" % sys.version)
    sys.exit(1)


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

def remove_root(path, root):
    if root:
        return os.path.normpath(path).replace(os.path.normpath(root), "")
    return os.path.normpath(path)

def write_build_info():
    """
    Get VCS info from misc/generate_vcs_info.py and add build information.
    Substitute these into misc/git_version.py.in to produce
    pylal/git_version.py.
    """
    date = branch = tag = author = committer = status = builder_name = build_date = ""
    id = "0.9.dev1"
    
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

class pylal_build_py(build_py.build_py):
    def run(self):
        log.info("Generated pylal/git_version.py")
        build_py.build_py.run(self)

setup(
    name = "pycbc-pylal",
    version = version,
    author = 'Ligo Virgo Collaboration - PyCBC team',
    author_email = 'alex.nitz@ligo.org',
    url = 'https://github.com/ligo-cbc/pycbc-pylal',
    description = "legacy support python ligo algorithm library",
    license = "See file LICENSE",
    packages = [
        "pylal",
        "pylal.xlal",
        "pylal.xlal.datatypes"
    ],
    cmdclass = {
        "build_py": pylal_build_py,
    },
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
    ],
    scripts = [
        os.path.join("bin", "ligolw_cbc_cluster_coincs"),
        os.path.join("bin", "ligolw_cbc_dbinjfind"),
        os.path.join("bin", "ligolw_cbc_hardware_inj_page"),
        os.path.join("bin", "ligolw_cbc_plotcumhist"),
        os.path.join("bin", "ligolw_cbc_plotfm"),
        os.path.join("bin", "ligolw_cbc_plotifar"),
        os.path.join("bin", "ligolw_cbc_plotslides"),
        os.path.join("bin", "ligolw_cbc_printlc"),
        os.path.join("bin", "ligolw_cbc_printmissed"),
        os.path.join("bin", "ligolw_cbc_printsims"),
        os.path.join("bin", "ligolw_cbc_sstinca"),
        os.path.join("bin", "pylal_cbc_minifollowups"),
        os.path.join("bin", "pylal_cbc_plotinspiral"),
        os.path.join("bin", "pylal_cbc_plotinspiralrange"),
        os.path.join("bin", "pylal_cbc_plotnumtemplates"),
        os.path.join("bin", "pylal_cbc_sink"),
        os.path.join("bin", "pylal_cbc_svim")
        ],
)
