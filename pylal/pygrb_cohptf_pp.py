# Copyright (C) 2015 Andrew Williamson
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 3 of the License, or (at your
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
# =============================================================================
#
#                                   Preamble
#
# =============================================================================
#
"""
This module is used to prepare output from the coherent matched filter workflow
for post-processing (post-processing = calculating significance of candidates
and making any rates statements).
For details of this module and its capabilities see here:
https://ldas-jobs.ligo.caltech.edu/~cbc/docs/pycbc/NOTYETCREATED.html
"""

from __future__ import division

import os
import os.path
import logging
import Pegasus.DAX3 as dax
from glue import segments
from pycbc.workflow.core import File, FileList, make_analysis_dir
from pylal.legacy_ihope import select_generic_executable

def setup_coh_PTF_post_processing(workflow, trigger_files, trigger_cache, 
        output_dir, segment_dir, timeslide_trigger_files=None,
        injection_trigger_files=None, injection_files=None,
        injection_trigger_caches=None, injection_caches=None, config_file=None,
        run_dir=None, ifos=None, web_dir=None, segments_plot=None,
        inj_tags=None, tags=None, **kwargs):
    """
    This function aims to be the gateway for running postprocessing on the
    output of lalapps_coh_PTF_inspiral for the PyGRB+coh_PTF hybrid workflow.

    Parameters
    -----------
    workflow : pycbc.workflow.core.Workflow
        The Workflow instance that the coincidence jobs will be added to.
    trigger_files : pycbc.workflow.core.FileList
        A FileList of the trigger files from the on/off source analysis jobs.
    trigger_cache : pycbc.workflow.core.File
        A cache file pointing to the trigger files.
    output_dir : path
        The directory in which output files will be stored.
    segment_dir : path
        The directory in which data segment information is stored.
    timeslide_trigger_files : pycbc.workflow.core.FileList
        A FileList of the trigger files produced by timeslide jobs.
    injection_trigger_files : pycbc.workflow.core.FileList
        A FileList of the trigger files produced by injection jobs.
    injection_trigger_caches : pycbc.workflow.core.FileList
        A FileList containing the cache files that point to the injection
        trigger files.
    injection_caches : pycbc.workflow.core.FileList
        A FileList containing cache files that point to the injection files.
    config_file : pycbc.workflow.core.File
        The parsed configuration file.
    run_dir : path
        The run directory.
    ifos : list
        A list containing the analysis interferometers.
    web_dir : path
        The directory where the result webpage will be placed.
    segments_plot : pycbc.workflow.core.File
        The plot showing the analysis segments for each IFO around the GRB time.
        This is produced at the time of workflow generation.
    inj_tags : list
        List containing the strings used to uniquely identify the injection
        sets included in the analysis.
    tags : list of strings (optional, default = [])
        A list of the tagging strings that will be used for all jobs created
        by this call to the workflow. An example might be ['POSTPROC1'] or
        ['DENTYSNEWPOSTPROC']. This will be used in output names.

    Returns
    --------
    post_proc_files : pycbc.workflow.core.FileList
        A list of the output from this stage.

    """
    if inj_tags is None:
        inj_tags = []
    if tags is None:
        tags = []
    logging.info("Entering post-processing stage.")
    make_analysis_dir(output_dir)

    # Parse for options in .ini file
    post_proc_method = workflow.cp.get_opt_tags("workflow-postproc",
                                                "postproc-method", tags)

    # Scope here for adding different options/methods here. For now we only
    # have the single_stage ihope method which consists of converting the
    # ligolw_thinca output xml into one file, clustering, performing injection
    # finding and putting everything into one SQL database.
    if post_proc_method in ["COH_PTF_WORKFLOW", "COH_PTF_OFFLINE"]:
        post_proc_files = setup_postproc_coh_PTF_offline_workflow(workflow,
                trigger_files, trigger_cache, timeslide_trigger_files,
                injection_trigger_files, injection_files,
                injection_trigger_caches, injection_caches, config_file,
                output_dir, web_dir, segment_dir, segments_plot, ifos=ifos,
                inj_tags=inj_tags, tags=tags, **kwargs)
    elif post_proc_method == "COH_PTF_ONLINE":
        post_proc_files = setup_postproc_coh_PTF_online_workflow(workflow,
                trigger_files, trigger_cache, timeslide_trigger_files,
                injection_trigger_files, injection_files,
                injection_trigger_caches, injection_caches, config_file,
                output_dir, web_dir, segment_dir, segments_plot, ifos=ifos,
                inj_tags=inj_tags, tags=tags, **kwargs)
    else:
        errMsg = "Post-processing method not recognized. Must be one of "
        errMsg += "COH_PTF_WORKFLOW, COH_PTF_OFFLINE, COH_PTF_ONLINE."
        raise ValueError(errMsg)

    logging.info("Leaving post-processing module.")

    return post_proc_files


def setup_coh_PTF_injections_pp(wf, inj_trigger_files, inj_files,
                                inj_trigger_caches, inj_caches,
                                pp_nodes, pp_outs, inj_tags, out_dir, seg_dir,
                                ifos, tags=None):
    """
    Set up post processing for injections
    """
    injfinder_nodes = []
    injcombiner_parent_nodes = []
    inj_sbv_plotter_parent_nodes = []
    full_segment = inj_trigger_files[0].segment

    injfinder_exe = os.path.basename(wf.cp.get("executables", "injfinder"))
    injfinder_class = select_generic_executable(wf, "injfinder")
    injfinder_jobs = injfinder_class(wf.cp, "injfinder", ifo=ifos,
                                     out_dir=out_dir, tags=tags)

    injcombiner_exe = os.path.basename(wf.cp.get("executables", "injcombiner"))
    injcombiner_class = select_generic_executable(wf, "injcombiner")
    injcombiner_jobs = injcombiner_class(wf.cp, "injcombiner", ifo=ifos,
                                         out_dir=out_dir, tags=tags)

    injfinder_outs = FileList([])
    for inj_tag in inj_tags:
        triggers = FileList([file for file in inj_trigger_files \
                             if inj_tag in file.tag_str])
        injections = FileList([file for file in inj_files \
                               if inj_tag in file.tag_str])
        trig_cache = [file for file in inj_trigger_caches \
                      if inj_tag in file.tag_str][0]
        inj_cache = [file for file in inj_caches \
                     if inj_tag in file.tag_str][0]
        injfinder_node, curr_outs = injfinder_jobs.create_node(\
                triggers, injections, seg_dir, tags=[inj_tag])
        injfinder_nodes.append(injfinder_node)
        pp_nodes.append(injfinder_node)
        wf.add_node(injfinder_node)
        injfinder_outs.extend(curr_outs)
        if "DETECTION" not in curr_outs[0].tagged_description:
            injcombiner_parent_nodes.append(injfinder_node)
        else:
            inj_sbv_plotter_parent_nodes.append(injfinder_node)

    pp_outs.extend(injfinder_outs)

    # Make injfinder output cache
    fm_cache = File(ifos, "foundmissed", full_segment,
                    extension="lcf", directory=out_dir)
    fm_cache.PFN(fm_cache.cache_entry.path, site="local")
    injfinder_outs.convert_to_lal_cache().tofile(\
            open(fm_cache.storage_path, "w"))
    pp_outs.extend(FileList([fm_cache]))

    # Set up injcombiner jobs
    injcombiner_outs = FileList([f for f in injfinder_outs \
                                 if "DETECTION" in f.tag_str])
    injcombiner_tags = [inj_tag for inj_tag in inj_tags \
                        if "DETECTION" not in inj_tag]
    injcombiner_out_tags = [i.tag_str.rsplit('_', 1)[0] for i in \
                            injcombiner_outs if "FOUND" in i.tag_str]
    injcombiner_nodes = []

    for injcombiner_tag in injcombiner_tags:
        max_inc = wf.cp.get_opt_tags("injections", "max-inc",
                                     [injcombiner_tag])
        inj_str = injcombiner_tag.replace("INJ", "")
        inputs = FileList([f for f in injfinder_outs \
                           if injcombiner_tag in f.tagged_description])
        injcombiner_node, curr_outs = injcombiner_jobs.create_node(\
                fm_cache, inputs, inj_str, max_inc, wf.analysis_time)
        injcombiner_nodes.append(injcombiner_node)
        injcombiner_out_tags.append("%s_FILTERED_%s"
                                    % (inj_str.split(max_inc)[0], max_inc))
        injcombiner_outs.extend(curr_outs)
        pp_outs.extend(curr_outs)
        pp_nodes.append(injcombiner_node)
        wf.add_node(injcombiner_node)
        for parent_node in injcombiner_parent_nodes:
            dep = dax.Dependency(parent=parent_node._dax_node,
                                 child=injcombiner_node._dax_node)
            wf._adag.addDependency(dep)

    return (wf, injfinder_nodes, injfinder_outs, fm_cache, injcombiner_nodes,
            injcombiner_outs, injcombiner_out_tags,
            inj_sbv_plotter_parent_nodes, pp_nodes, pp_outs)


def setup_coh_PTF_plotting_jobs(workflow, unclust_file, clust_file,
        sbv_plotter_jobs, efficiency_jobs, inj_efficiency_jobs,
        off_node, dep_node, offsource_clustered, injfinder_nodes,
        injcombiner_nodes, injcombiner_outs, inj_sbv_plotter_parent_nodes,
        inj_tags, injcombiner_out_tags, pp_nodes, output_dir, segment_dir,
        ifos, out_tag, do_injs=False, tags=None):
    """
    Creates signal-based veto and efficiency jobs
    """
    if out_tag != "ONSOURCE":
        # Add sbv_plotter job
        sbv_out_tags = [out_tag, "_clustered"]
        sbv_plotter_node = sbv_plotter_jobs.create_node(clust_file,
                                                        segment_dir,
                                                        tags=sbv_out_tags)
        pp_nodes.append(sbv_plotter_node)
        workflow.add_node(sbv_plotter_node)
        for n in set((off_node, dep_node)):
            dep = dax.Dependency(parent=n._dax_node,
                                 child=sbv_plotter_node._dax_node)
            workflow._adag.addDependency(dep)

        # Add injection sbv_plotter nodes if appropriate
        if out_tag == "OFFSOURCE" and do_injs:
            found_inj_files = FileList([file for file in injcombiner_outs \
                                        if "FOUND" in file.tag_str])
            for curr_injs in found_inj_files:
                curr_tags = [tag for tag in injcombiner_out_tags \
                             if tag in curr_injs.name]
                curr_tags.append("_clustered")
                sbv_plotter_node = sbv_plotter_jobs.create_node(clust_file,
                        segment_dir, inj_file=curr_injs, tags=curr_tags)
                pp_nodes.append(sbv_plotter_node)
                workflow.add_node(sbv_plotter_node)
                dep = dax.Dependency(parent=dep_node._dax_node,
                                     child=sbv_plotter_node._dax_node)
                workflow._adag.addDependency(dep)
                if "DETECTION" in curr_injs.tagged_description:
                    for parent_node in inj_sbv_plotter_parent_nodes:
                        dep = dax.Dependency(parent=parent_node._dax_node,
                                child=sbv_plotter_node._dax_node)
                        workflow._adag.addDependency(dep)
                else:
                    for parent_node in injcombiner_nodes:
                        dep = dax.Dependency(parent=parent_node._dax_node,
                                child=sbv_plotter_node._dax_node)
                        workflow._adag.addDependency(dep)

        # Also add sbv_plotter job for unclustered triggers
        #sbv_plotter_node = sbv_plotter_jobs.create_node(unclust_file,
        #        segment_dir, tags=[out_tag, "_unclustered"])
        #pp_nodes.append(sbv_plotter_node)
        #workflow.add_node(sbv_plotter_node)
        #dep = dax.Dependency(parent=trig_combiner_node._dax_node,
        #                     child=sbv_plotter_node._dax_node)
        #workflow._adag.addDependency(dep)
    else:
        # Add efficiency job for on/off
        efficiency_node = efficiency_jobs.create_node(clust_file,
                offsource_clustered, segment_dir, tags=[out_tag])
        pp_nodes.append(efficiency_node)
        workflow.add_node(efficiency_node)
        dep = dax.Dependency(parent=dep_node._dax_node,
                             child=efficiency_node._dax_node)
        workflow._adag.addDependency(dep)

        if do_injs:
            for tag in injcombiner_out_tags:
                if "_FILTERED_" in tag:
                    inj_set_tag = [t for t in inj_tags if \
                                   str(tag).replace("_FILTERED_", "") \
                                   in t][0]
                else:
                    inj_set_tag = str(tag)
                
                found_file = [file for file in injcombiner_outs \
                              if tag + "_FOUND" in file.tag_str][0]
                missed_file = [file for file in injcombiner_outs \
                               if tag + "_MISSED" in file.tag_str][0]
                inj_efficiency_node = inj_efficiency_jobs.create_node(\
                        clust_file, offsource_clustered, segment_dir,
                        found_file, missed_file, tags=[out_tag, tag,
                                                       inj_set_tag])
                pp_nodes.append(inj_efficiency_node)
                workflow.add_node(inj_efficiency_node)
                dep = dax.Dependency(parent=dep_node._dax_node,
                                     child=inj_efficiency_node._dax_node)
                workflow._adag.addDependency(dep)
                for injcombiner_node in injcombiner_nodes:
                    dep = dax.Dependency(parent=injcombiner_node._dax_node,
                                         child=inj_efficiency_node._dax_node)
                    workflow._adag.addDependency(dep)
                for injfinder_node in injfinder_nodes:
                    dep = dax.Dependency(parent=injfinder_node._dax_node,
                                         child=inj_efficiency_node._dax_node)
                    workflow._adag.addDependency(dep)

    return workflow, pp_nodes


def setup_postproc_coh_PTF_offline_workflow(workflow, trig_files, trig_cache,
        ts_trig_files, inj_trig_files, inj_files, inj_trig_caches, inj_caches,
        config_file, output_dir, html_dir, segment_dir, segs_plot, ifos,
        inj_tags=None, tags=None):
    """
    This module sets up the post-processing stage in the workflow, using a
    coh_PTF style set up. This consists of running trig_combiner to find
    coherent triggers, and injfinder to look for injections. It then runs
    a horizon_dist job, trig_cluster to cluster triggers, and injcombiner to
    calculate injection statistics. Finally, efficiency and sbv_plotter jobs
    calculate efficiency and signal based veto statistics and make plots.
    
    Parameters
    -----------
    workflow : pycbc.workflow.core.Workflow
        The Workflow instance that the coincidence jobs will be added to.
    trig_files : pycbc.workflow.core.FileList
        A FileList of the trigger files from the on/off source analysis jobs.
    trig_cache : pycbc.workflow.core.File
        A cache file pointing to the trigger files.
    ts_trig_files : pycbc.workflow.core.FileList
        A FileList of the trigger files from the timeslide analysis jobs.
    inj_trig_files : pycbc.workflow.core.FileList
        A FileList of the trigger files produced by injection jobs.
    inj_files : pycbc.workflow.core.FileList
        A FileList of the injection set files.
    inj_trig_caches : pycbc.workflow.core.FileList
        A FileList containing the cache files that point to the injection
        trigger files.
    inj_caches : pycbc.workflow.core.FileList
        A FileList containing cache files that point to the injection files.
    config_file : pycbc.workflow.core.File
        The parsed configuration file.
    output_dir : path
        The directory in which output files will be stored.
    html_dir : path
        The directory where the result webpage will be placed.
    segment_dir : path
        The directory in which data segment information is stored.
    segs_plot : pycbc.workflow.core.File
        The plot showing the analysis segments for each IFO around the GRB time.
        This is produced at the time of workflow generation.
    ifos : list
        A list containing the analysis interferometers.
    inj_tags : list
        List containing the strings used to uniquely identify the injection
        sets included in the analysis.
    tags : list of strings (optional, default = [])
        A list of the tagging strings that will be used for all jobs created
        by this call to the workflow. An example might be ['POSTPROC1'] or
        ['DENTYSNEWPOSTPROC']. This will be used in output names.

    Returns
    --------
    pp_outs : pycbc.workflow.core.FileList
        A list of the output from this stage.
    """
    if inj_tags is None:
        inj_tags = []
    if tags is None:
        tags = []
    cp = workflow.cp
    full_segment = trig_files[0].segment
    trig_name = cp.get("workflow", "trigger-name")
    grb_string = "GRB" + trig_name
    num_trials = int(cp.get("trig_combiner", "num-trials"))
    do_injections = cp.has_section("workflow-injections")

    pp_outs = FileList([])
    pp_nodes = []

    # Set up needed exe classes
    trig_combiner_class = select_generic_executable(workflow, "trig_combiner")

    trig_cluster_class = select_generic_executable(workflow, "trig_cluster")

    sbv_plotter_class = select_generic_executable(workflow, "sbv_plotter")
    
    efficiency_class = select_generic_executable(workflow, "efficiency")

    #horizon_dist_class = select_generic_executable(workflow, "horizon_dist")

    html_summary_class = select_generic_executable(workflow, "html_summary")

    # Set up injection jobs if desired
    if do_injections:
        workflow, injfinder_nodes, injfinder_outs, fm_cache, \
                injcombiner_nodes, injcombiner_outs, injcombiner_out_tags, \
                inj_sbv_plotter_parent_nodes, pp_nodes, pp_outs = \
                setup_coh_PTF_injections_pp(workflow, inj_trig_files,
                        inj_files, inj_trig_caches, inj_caches, pp_nodes,
                        pp_outs, inj_tags, output_dir, segment_dir, ifos,
                        tags=tags)

        # Initialise injection_efficiency class
        inj_efficiency_jobs = efficiency_class(cp, "inj_efficiency", ifo=ifos,
                                               out_dir=output_dir, tags=tags)

    # Set up main trig_combiner class and tags
    trig_combiner_out_tags = ["OFFSOURCE", "ONSOURCE", "ALL_TIMES"]
    slides = all("COHERENT_NO_INJECTIONS" in t.name for t in trig_files) and \
            cp.has_option_tag("inspiral", "do-short-slides",
                              "coherent_no_injections")
    if slides:
        trig_combiner_out_tags.extend(["ZEROLAG_OFF", "ZEROLAG_ALL"])
    
    trig_combiner_jobs = trig_combiner_class(cp, "trig_combiner", ifo=ifos, 
                                             out_dir=output_dir, tags=tags)

    # Do first stage of trig_combiner and trig_cluster jobs if desired
    if workflow.cp.has_option("workflow-postproc", "do-two-stage-clustering"):
        logging.info("Doing two-stage clustering.")
        trig_combiner_s1_jobs = trig_combiner_class(cp, "trig_combiner",
                ifo=ifos, out_dir=output_dir, tags=tags+["INTERMEDIATE"])

        num_stage_one_jobs = int(workflow.cp.get("workflow-postproc",
            "num-stage-one-cluster-jobs"))
        num_inputs_per_job = -(-len(trig_files) // num_stage_one_jobs)
        split_trig_files = (trig_files[p:p + num_inputs_per_job] for p in \
                            xrange(0, len(trig_files), num_inputs_per_job))
        trig_cluster_s1_jobs = trig_cluster_class(cp, "trig_cluster", ifo=ifos,
                out_dir=output_dir, tags=tags+["INTERMEDIATE"])
        trig_cluster_s1_nodes = []
        trig_cluster_s1_outs = FileList([])
        for j, s1_inputs in zip(range(num_stage_one_jobs), split_trig_files):
            trig_combiner_s1_node, trig_combiner_s1_outs = \
                    trig_combiner_s1_jobs.create_node(s1_inputs,
                            segment_dir, workflow.analysis_time,
                            out_tags=trig_combiner_out_tags, tags=tags+[str(j)])
            pp_nodes.append(trig_combiner_s1_node)
            workflow.add_node(trig_combiner_s1_node)

            unclust_file = [f for f in trig_combiner_s1_outs \
                            if "ALL_TIMES" in f.tag_str][0]
            trig_cluster_s1_node, curr_outs = trig_cluster_s1_jobs.create_node(\
                    unclust_file)
            trig_cluster_s1_outs.extend(curr_outs)
            clust_file = curr_outs[0]
            trig_cluster_s1_nodes.append(trig_cluster_s1_node)
            pp_nodes.append(trig_cluster_s1_node)
            workflow.add_node(trig_cluster_s1_node)
            dep = dax.Dependency(parent=trig_combiner_s1_node._dax_node,
                                 child=trig_cluster_s1_node._dax_node)
            workflow._adag.addDependency(dep)

        trig_combiner_node, trig_combiner_outs = \
                trig_combiner_jobs.create_node(trig_cluster_s1_outs,
                        segment_dir, workflow.analysis_time,
                        out_tags=trig_combiner_out_tags, tags=tags)
        pp_nodes.append(trig_combiner_node)
        workflow.add_node(trig_combiner_node)
        pp_outs.extend(trig_combiner_outs)
        for trig_cluster_s1_node in trig_cluster_s1_nodes:
            dep = dax.Dependency(parent=trig_cluster_s1_node._dax_node,
                                 child=trig_combiner_node._dax_node)
            workflow._adag.addDependency(dep)

    else:
        trig_combiner_node, trig_combiner_outs = \
                trig_combiner_jobs.create_node(trig_files, segment_dir,
                        workflow.analysis_time, out_tags=trig_combiner_out_tags,
                        tags=tags)
        pp_nodes.append(trig_combiner_node)
        workflow.add_node(trig_combiner_node)
        pp_outs.extend(trig_combiner_outs)

    # Initialise trig_cluster class
    trig_cluster_outs = FileList([])
    trig_cluster_jobs = trig_cluster_class(cp, "trig_cluster", ifo=ifos,
                                           out_dir=output_dir, tags=tags)

    # Initialise sbv_plotter class
    sbv_plotter_outs = FileList([])
    sbv_plotter_jobs = sbv_plotter_class(cp, "sbv_plotter", ifo=ifos,
                                         out_dir=output_dir, tags=tags)

    # Initialise efficiency class
    efficiency_outs = FileList([])
    efficiency_jobs = efficiency_class(cp, "efficiency", ifo=ifos,
                                       out_dir=output_dir, tags=tags)

    # Set up trig_cluster jobs
    trig_cluster_nodes = []
    for out_tag in trig_combiner_out_tags:
        unclust_file = [f for f in trig_combiner_outs \
                        if out_tag in f.tag_str][0]
        trig_cluster_node, curr_outs = trig_cluster_jobs.create_node(\
                unclust_file)
        trig_cluster_outs.extend(curr_outs)
        clust_file = curr_outs[0]
        trig_cluster_nodes.append(trig_cluster_node)
        pp_nodes.append(trig_cluster_node)
        workflow.add_node(trig_cluster_node)
        dep = dax.Dependency(parent=trig_combiner_node._dax_node,
                             child=trig_cluster_node._dax_node)
        workflow._adag.addDependency(dep)
        # Are we not doing time slides?
        if ts_trig_files is None:
            if out_tag == "OFFSOURCE":
                off_node = trig_cluster_node
                offsource_clustered = clust_file

            # Add sbv_plotter and efficiency jobs
            workflow, pp_nodes = setup_coh_PTF_plotting_jobs(workflow, 
                    unclust_file, clust_file, sbv_plotter_jobs,
                    efficiency_jobs, inj_efficiency_jobs, off_node,
                    trig_cluster_node, offsource_clustered, injfinder_nodes,
                    injcombiner_nodes, injcombiner_outs,
                    inj_sbv_plotter_parent_nodes, inj_tags,
                    injcombiner_out_tags, pp_nodes, output_dir, segment_dir,
                    ifos, out_tag, do_injs=do_injections, tags=tags)

    # If doing time slides
    if ts_trig_files is not None:
        trig_combiner_ts_nodes = []
        trig_cluster_ts_nodes = []
        trig_cluster_all_times_nodes = []
        ts_all_times_outs = FileList([out for out in trig_cluster_outs
                                      if "ALL_TIMES" in out.tag_str])
        trig_combiner_ts_out_tags = ["ALL_TIMES", "OFFSOURCE"]
        ts_tags = list(set([[ts_tag for ts_tag in ts_trig_file.tags
                             if "SLIDE" in ts_tag][0]
                            for ts_trig_file in ts_trig_files]))
        for ts_tag in ts_tags:
            # Do one slide at a time
            ts_trigs = FileList([ts_trig_file for ts_trig_file in ts_trig_files
                                 if ts_tag in ts_trig_file.tags])

            # And do two-stage clustering if desired
            if workflow.cp.has_option("workflow-postproc",
                                      "do-two-stage-clustering"):

                split_trig_files = (ts_trigs[p:p + num_inputs_per_job]
                        for p in xrange(0, len(ts_trigs), num_inputs_per_job))
                trig_cluster_s1_nodes = []
                trig_cluster_s1_outs = FileList([])
                for j, s1_inputs in zip(range(num_stage_one_jobs),
                                        split_trig_files):
                    trig_combiner_s1_node, trig_combiner_s1_outs = \
                            trig_combiner_s1_jobs.create_node(s1_inputs,
                                     segment_dir, workflow.analysis_time,
                                     out_tags=trig_combiner_ts_out_tags,
                                     slide_tag=ts_tag, tags=tags+[str(j)])
                    pp_nodes.append(trig_combiner_s1_node)
                    workflow.add_node(trig_combiner_s1_node)

                    unclust_file = [f for f in trig_combiner_s1_outs \
                                    if "ALL_TIMES" in f.tag_str][0]
                    trig_cluster_s1_node, curr_outs = \
                            trig_cluster_s1_jobs.create_node(unclust_file)
                    trig_cluster_s1_outs.extend(curr_outs)
                    clust_file = curr_outs[0]
                    trig_cluster_s1_nodes.append(trig_cluster_s1_node)
                    pp_nodes.append(trig_cluster_s1_node)
                    workflow.add_node(trig_cluster_s1_node)
                    dep = dax.Dependency(parent=trig_combiner_s1_node._dax_node,
                                         child=trig_cluster_s1_node._dax_node)
                    workflow._adag.addDependency(dep)

                trig_combiner_ts_node, trig_combiner_ts_outs = \
                        trig_combiner_jobs.create_node(trig_cluster_s1_outs,
                                segment_dir, workflow.analysis_time,
                                slide_tag=ts_tag,
                                out_tags=trig_combiner_ts_out_tags, tags=tags)
                trig_combiner_ts_nodes.append(trig_combiner_ts_node)
                pp_nodes.append(trig_combiner_ts_node)
                workflow.add_node(trig_combiner_ts_node)
                pp_outs.extend(trig_combiner_ts_outs)
                for trig_cluster_s1_node in trig_cluster_s1_nodes:
                    dep = dax.Dependency(parent=trig_cluster_s1_node._dax_node,
                                         child=trig_combiner_ts_node._dax_node)
                    workflow._adag.addDependency(dep)
            else:
                trig_combiner_ts_node, trig_combiner_ts_outs = \
                        trig_combiner_jobs.create_node(ts_trigs, segment_dir,
                                workflow.analysis_time, slide_tag=ts_tag,
                                out_tags=trig_combiner_ts_out_tags, tags=tags)
                trig_combiner_ts_nodes.append(trig_combiner_ts_node)
                pp_nodes.append(trig_combiner_ts_node)
                workflow.add_node(trig_combiner_ts_node)
                pp_outs.extend(trig_combiner_ts_outs)

            # Set up trig cluster jobs for each timeslide
            for ts_out_tag in trig_combiner_ts_out_tags:
                unclust_file = [f for f in trig_combiner_ts_outs \
                                if ts_out_tag in f.tag_str][0]
                trig_cluster_node, curr_outs = trig_cluster_jobs.create_node(\
                        unclust_file)
                trig_cluster_outs.extend(curr_outs)
                clust_file = curr_outs[0]
                trig_cluster_ts_nodes.append(trig_cluster_node)
                pp_nodes.append(trig_cluster_node)
                workflow.add_node(trig_cluster_node)
                dep = dax.Dependency(parent=trig_combiner_ts_node._dax_node,
                                     child=trig_cluster_node._dax_node)
                workflow._adag.addDependency(dep)        
                if ts_out_tag == "ALL_TIMES":
                    trig_cluster_all_times_nodes.append(trig_cluster_node)
                    ts_all_times_outs.extend(FileList([clust_file]))

        # Combine all timeslides
        trig_combiner_all_node, trig_combiner_all_outs = \
                trig_combiner_jobs.create_node(ts_all_times_outs, segment_dir,
                            workflow.analysis_time, slide_tag="ALL_SLIDES",
                            out_tags=trig_combiner_ts_out_tags, tags=tags)
        pp_nodes.append(trig_combiner_all_node)
        workflow.add_node(trig_combiner_all_node)
        for trig_cluster_ts_node in trig_cluster_all_times_nodes:
            dep = dax.Dependency(parent=trig_cluster_ts_node._dax_node,
                                 child=trig_combiner_all_node._dax_node)
            workflow._adag.addDependency(dep)        

        for out_tag in trig_combiner_ts_out_tags:
            trig_cluster_outs = FileList([f for f in trig_cluster_outs
                                          if out_tag not in f.tag_str])
        trig_cluster_outs.extend(trig_combiner_all_outs)
        off_node = trig_combiner_all_node
        offsource_clustered = [f for f in trig_cluster_outs
                               if "OFFSOURCE" in f.tag_str
                               and "ZERO_LAG" not in f.tag_str][0]

        # Add sbv_plotter and efficiency jobs
        for out_tag in trig_combiner_out_tags:
            clust_file = [f for f in trig_cluster_outs \
                          if out_tag in f.tag_str][0]

            workflow, pp_nodes = setup_coh_PTF_plotting_jobs(workflow, 
                    unclust_file, clust_file, sbv_plotter_jobs,
                    efficiency_jobs, inj_efficiency_jobs, off_node, off_node,
                    offsource_clustered, injfinder_nodes, injcombiner_nodes,
                    injcombiner_outs, inj_sbv_plotter_parent_nodes, inj_tags,
                    injcombiner_out_tags, pp_nodes, output_dir, segment_dir,
                    ifos, out_tag, do_injs=do_injections, tags=tags)

    trial = 1
    while trial <= num_trials:
        trial_tag = "OFFTRIAL_%d" % trial
        unclust_file = [f for f in trig_combiner_outs \
                        if trial_tag in f.tag_str][0]
        trig_cluster_node, clust_outs = trig_cluster_jobs.create_node(\
                unclust_file)
        clust_file = clust_outs[0]
        trig_cluster_outs.extend(clust_outs)
        pp_nodes.append(trig_cluster_node)
        workflow.add_node(trig_cluster_node)
        dep = dax.Dependency(parent=trig_combiner_node._dax_node,
                             child=trig_cluster_node._dax_node)
        workflow._adag.addDependency(dep)

        # Add efficiency job
        efficiency_node = efficiency_jobs.create_node(clust_file,
                offsource_clustered, segment_dir, tags=[trial_tag])
        pp_nodes.append(efficiency_node)
        workflow.add_node(efficiency_node)
        dep = dax.Dependency(parent=off_node._dax_node,
                             child=efficiency_node._dax_node)
        workflow._adag.addDependency(dep)
        dep = dax.Dependency(parent=trig_cluster_node._dax_node,
                             child=efficiency_node._dax_node)
        workflow._adag.addDependency(dep)

        # Adding inj_efficiency job
        if do_injections:
            for tag in injcombiner_out_tags:
                if "_FILTERED_" in tag:
                    inj_set_tag = [t for t in inj_tags if \
                                   str(tag).replace("_FILTERED_", "") in t][0]
                else:
                    inj_set_tag = str(tag)

                found_file = [file for file in injcombiner_outs \
                              if tag + "_FOUND" in file.tag_str][0]
                missed_file = [file for file in injcombiner_outs \
                               if tag + "_MISSED" in file.tag_str][0]
                inj_efficiency_node = inj_efficiency_jobs.create_node(\
                        clust_file, offsource_clustered, segment_dir,
                        found_file, missed_file, tags=[trial_tag, tag,
                                                       inj_set_tag])
                pp_nodes.append(inj_efficiency_node)
                workflow.add_node(inj_efficiency_node)
                dep = dax.Dependency(parent=off_node._dax_node,
                                     child=inj_efficiency_node._dax_node)
                workflow._adag.addDependency(dep)
                for injcombiner_node in injcombiner_nodes:
                    dep = dax.Dependency(parent=injcombiner_node._dax_node,
                                         child=inj_efficiency_node._dax_node)
                    workflow._adag.addDependency(dep)
                for injfinder_node in injfinder_nodes:
                    dep = dax.Dependency(parent=injfinder_node._dax_node,
                                         child=inj_efficiency_node._dax_node)
                    workflow._adag.addDependency(dep)

        trial += 1

    # Initialise html_summary class and set up job
    #FIXME: We may want this job to run even if some jobs fail
    html_summary_jobs = html_summary_class(cp, "html_summary", ifo=ifos,
                                           out_dir=output_dir, tags=tags)
    if do_injections:
        tuning_tags = [inj_tag for inj_tag in injcombiner_out_tags \
                       if "DETECTION" in inj_tag]
        exclusion_tags = [inj_tag for inj_tag in injcombiner_out_tags \
                          if "DETECTION" not in inj_tag]
        html_summary_node = html_summary_jobs.create_node(c_file=config_file,
                tuning_tags=tuning_tags, exclusion_tags=exclusion_tags,
                seg_plot=segs_plot, html_dir=html_dir, time_slides=slides)
    else:
        html_summary_node = html_summary_jobs.create_node(c_file=config_file,
                seg_plot=segs_plot, html_dir=html_dir, time_slides=slides)
    workflow.add_node(html_summary_node)
    for pp_node in pp_nodes:
        dep = dax.Dependency(parent=pp_node._dax_node,
                             child=html_summary_node._dax_node)
        workflow._adag.addDependency(dep)

    # Make the open box shell script
    try:
        open_box_cmd = html_summary_node.executable.get_pfn() + " "
    except:
        exe_path = html_summary_node.executable.get_pfn('nonlocal').replace(\
                "https", "http")
        exe_name = exe_path.rsplit('/', 1)[-1]
        open_box_cmd = "wget %s\n" % exe_path
        open_box_cmd += "chmod 500 ./%s\n./%s " % (exe_name, exe_name)
    open_box_cmd += ' '.join(html_summary_node._args + \
                             html_summary_node._options)
    open_box_cmd += " --open-box"
    open_box_path = "%s/open_the_box.sh" % output_dir
    f = open(open_box_path, "w")
    f.write("#!/bin/sh\n%s" % open_box_cmd)
    f.close()
    os.chmod(open_box_path, 0500)

    pp_outs.extend(trig_cluster_outs)

    return pp_outs

