"""DIRSIG-bound modules (private, transitional): the dirfm job assembly (`simulation`, `registry`), the pass-through
runner (`passthrough`), the FlexMotion and tasks writer (`motion_tasks`), and the dirfm gap-fillers and DIRSIG scene
helpers. Round 18 moves them to a separate `manifold.engines.dirsig` distribution behind an engine adapter protocol;
nothing outside `manifold.sim` should import them.
"""
