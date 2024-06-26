#!/usr/bin/env python3

"""Electron-phonon calculations."""
from __future__ import print_function, division, unicode_literals, absolute_import

import sys
import os
import abipy.data as abidata
import abipy.abilab as abilab
import abipy.flowtk as flowtk


def build_flow(options):

    # Working directory (default is the name of the script with '.py' removed and "run_" replaced by "flow_")
    if not options.workdir:
        options.workdir = os.path.basename(sys.argv[0]).replace(".py", "").replace("run_", "flow_")

    # Preparatory run for E-PH calculations.
    # The sequence of datasets makes the ground states and
    # all of the independent perturbations of the single Al atom
    # for the irreducible qpoints in a 4x4x4 grid.
    # Note that the q-point grid must be a sub-grid of the k-point grid (here 8x8x8)
    pseudos = abidata.pseudos("B.psp8","Mg.psp8")

    structure = abilab.Structure.from_file("POSCAR")

    gs_inp = abilab.AbinitInput(structure, pseudos)

    gs_inp.set_vars(
        ecut=35.0,
        occopt=4,    # include metallic occupation function with a small smearing
        tsmear=0.04,
        tolvrs=1e-8,
    )

    gs_inp.set_kmesh(
        ngkpt=[16, 16, 12],
        shiftk=[0.0, 0.0, 0.0],
    )

    # Phonon calculation with 8x8x6
    ddb_ngqpt = [8, 8, 6]
    qpoints = gs_inp.abiget_ibz(ngkpt=ddb_ngqpt, shiftk=[0, 0, 0], kptopt=1).points

    flow = flowtk.Flow(options.workdir, manager=options.manager)
    work0 = flow.register_scf_task(gs_inp)

    ph_work = flowtk.PhononWork.from_scf_task(work0[0], qpoints)
    flow.register_work(ph_work)

    eph_work = flow.register_work(flowtk.Work())
    eph_deps = {work0[0]: "WFK", ph_work: ["DDB", "DVDB"]}

    for eph_ngqpt_fine in [(8,8,6), (16,16,12)]:
        # Build input file for E-PH run.
        eph_inp = gs_inp.new_with_vars(
            optdriver=7,
            ddb_ngqpt=ddb_ngqpt,           # q-mesh used to produce the DDB file (must be consistent with DDB data)
            eph_intmeth=2,                 # Tetra method
            eph_fsewin="0.8 eV",           # Energy window around Ef
            eph_mustar=0.12,               # mustar parameter
            eph_ngqpt_fine=eph_ngqpt_fine, # Interpolate DFPT potentials if != ddb_ngqpt
        )

        # Set q-path for phonons and phonon linewidths.
        eph_inp.set_qpath(20)

        # TODO: Define wstep and smear
        # Set q-mesh for phonons DOS and a2F(w)
        eph_inp.set_phdos_qmesh(nqsmall=16, method="tetra")
        eph_work.register_eph_task(eph_inp, deps=eph_deps)

    flow.allocate(use_smartio=True)

    return flow


@flowtk.flow_main
def main(options):
    """
    This is our main function that will be invoked by the script.
    flow_main is a decorator implementing the command line interface.
    Command line args are stored in `options`.
    """
    return build_flow(options)


if __name__ == "__main__":
    sys.exit(main())

