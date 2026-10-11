# Round 17.5 state

- preflight: 2026-10-11T15:50:15-04:00
- deadline: 2026-10-11T19:50:15-04:00
- network: 2026-10-11T15:50:37-04:00 pip index/download satsim metadata (pypi.org, files.pythonhosted.org)
- network: 2026-10-11T15:50:52-04:00 conda create satsim python=3.11 pip from conda-forge (conda.anaconda.org)
- network: 2026-10-11T15:51:12-04:00 pip install satsim==0.26.1 and deps (pypi.org, files.pythonhosted.org)
- network: 2026-10-11T15:56:37-04:00 first satsim run downloaded de421.bsp (skyfield Loader, into the run's CWD) 
- network: 2026-10-11T15:57:53-04:00 isolation run without SATSIM_SKYFIELD_LOAD_DIR: expect de421.bsp re-download into the empty CWD
- network: 2026-10-11T15:58:21-04:00 astropy downloaded IERS/leap-second tables into $HOME/.astropy/cache (see findings)
- steps 1-4 done; docs written 2026-10-11T16:09:40-04:00
- gate: 1415 passed, 2 skipped, 256 s; checks 0; committing
