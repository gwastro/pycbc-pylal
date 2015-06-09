# pycbc-pylal repository

This repository contains a stripped down version of lalsuite/pylal for use
with PyCBC until the dependencies contained in this repository are retired.

The repository was created from the 0.7.2 v1 release (ER7 release) with the 
commands:

    git init
    git remote add -f origin git://ligo-vcs.phys.uwm.edu/lalsuite.git
    git checkout pylal-0.7.2-v1
    git filter-branch --subdirectory-filter pylal
    git checkout -b pylal-0.7.2-branch
    git branch -f master pylal-0.7.2-branch
    git checkout master
    git branch -d pylal-0.7.2-branch
    for t in `git tag` ; do git tag -d $t ; done

