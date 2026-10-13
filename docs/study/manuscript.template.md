---
title: "Flux, streak and placement fidelity of DIRSIG5 renders of orbital targets against a dark background"
author: "Kevin Kearney"
abstract: |
  We compare {{c:n_dirsig}} DIRSIG5 renders of flat Lambertian plates and Lambertian spheres seen from an orbiting sensor with closed-form expectations for integrated flux, footprint, streak length and solar-phase dependence, and {{c:n_satsim}} renders of the same geometries by SatSim, a renderer without per-pixel ray sampling, as a control. Targets span {{c:size_min|.3f}} to {{c:size_max|.1f}} pixels across. A still or singly moving target of {{c:within_min_px|.0f}} pixels or more keeps its integrated flux within {{c:within_max|pct:.1f}} % ({{c:n_within}} renders). The fitted streak length of a resolved or hyperresolved plate under platform or target motion is {{c:streak_hi|def:.1f}} to {{c:streak_lo|def:.1f}} % short of the closed form at DIRSIG's default sampling and {{d:fixed1000_both_25km_5ms|def:.2f}} to {{d:fixed1000_target_100km_20ms|def:.2f}} % short at a fixed path count per pixel; SatSim's renders of the same streaks read {{c:satsim_streak_lo|.4f}} to {{c:satsim_streak_hi|.4f}} of it. A labelled sub-pixel plate centred on a pixel corner and seen {{c:corner_look_lo|.0f}} to {{c:corner_look_hi|.0f}} degrees off its normal reads {{c:corner_hi|def:.1f}} to {{c:corner_lo|def:.1f}} % below the closed form, and holds it when moved off the corner. A labelled sub-pixel plate moving across the field loses {{r:s2s-unresolved-r12p5km-v1000mps-e5ms-l0-z0-d0-w64|def:.1f}} % ({{c:size_moving_big|.2f}} px) and {{r:s2s-unresolved-r25km-v1000mps-e5ms-l0-z0-d0-w64|def:.1f}} % ({{c:size_moving_small|.2f}} px) of its flux; SatSim keeps a moving point's flux to {{c:satsim_flux_max|sci}}. Under combined platform and target motion the flux deficit grows as the target shrinks ({{c:both_trend}} % at {{c:both_sizes}} px). The deficits that SatSim does not show go with DIRSIG's adaptive per-pixel sampling. With one rendering thread a DIRSIG render repeats bit for bit; at the default thread count {{c:det_td_px_lo}} to {{c:det_td_px_hi}} of {{c:det_lit|thou}} lit pixels of a test frame draw other samples and differ by up to {{c:det_td_maxrel|pct:.1f}} % of a value.
---

# Introduction {#sec:intro}

A sensor in orbit imaging an orbital target sees it against space or against the Earth, at a range and relative velocity set by the two orbits, with the Sun at a phase angle set by the three positions. The image of the target depends on its angular size against the pixel footprint. An unresolved target, under one pixel across, is a point whose flux the optics spread and the pixel grid divides according to its sub-pixel position. A resolved target, {{c:resolved_px|.0f}} to {{c:hyper_px|.0f}} pixels across, is mostly edge pixels. A hyperresolved target, over {{c:hyper_px|.0f}} pixels across, is mostly interior pixels. Relative motion during the exposure draws the target into a streak whose length is the relative angular speed times the exposure: platform motion streaks the target and the background together, and target motion streaks the target alone. The look angle off a flat target's normal foreshortens it, and the solar phase angle sets the brightness of a curved one.

A rendered image of such a scene serves algorithm development and sensor trade studies to the extent that its integrated flux, footprint, streak length and phase dependence are those of the geometry. We measure them for DIRSIG5, a Monte Carlo path tracer with adaptive per-pixel sampling (DIRSIG5 documentation, release {{c:dirsig_version}}), against closed forms, in scenes built so that each observable has one. SatSim {{c:satsim_version}} renders the same geometries by depositing a point or a sprite of stated flux, with no per-pixel ray sampling; a deficit that DIRSIG shows and SatSim does not is a property of DIRSIG's sampling rather than of the geometry or the closed form.

The axes exercised are the target's size in pixels, platform motion, target motion and both together, the shutter time, the look angle off nadir, the solar zenith and phase angle, the target's sub-pixel position, and DIRSIG's `::IMPORTANT::` label, which raises the path count of the pixels holding the labelled object. Every target has a black backstop behind it: a surface of zero reflectance which, in a band where no emission is evaluated, renders exactly as empty space would. An Earth background is not exercised.

# Method {#sec:method}

## Run specifications and scenes

Each case is a `run-spec/1` document generated from stated numbers by `scripts/s2s_scenarios.py`: {{c:n_specs_dirsig}} DIRSIG specifications in three families, of which {{c:n_dirsig}} are rendered and recorded, and {{c:n_specs_satsim_ctl}} SatSim control configurations. Appendix A lists them by family and group with the values of each axis.

Family I places square Lambertian plates of reflectance {{c:rho}} in an otherwise empty scene: a plate {{c:plate_hyper|.0f}} m on a side, and plates {{c:plate_small|.1f}} m on a side with and without the label, two of them moving at {{c:speed_lo|.0f}} and {{c:speed_hi|.0f}} m/s. The platform is static at a stated range, look angle and sub-pixel offset. Family II moves the scene rather than the platform. The {{c:plate_hyper|.0f}} m plate stands in front of a black plate carrying bars of reflectance {{c:bar_rho}} with a period of {{c:bar_period_m|.0f}} m; platform motion translates target and background together, target motion translates the plates alone, and both translates them in opposite directions, so the three are separately stated. Family II also holds a look sweep against the barred background, and a pair of renders from a platform propagated with SGP4 from a two-line element set whose line of sight stays on the plate. Family III replaces the plates by DIRSIG's analytic sphere primitive, of radius {{c:sphere_hyper|.0f}} m and {{c:sphere_small|.2f}} m, under a Sun at a stated zenith and azimuth.

The sensor has a single near-infrared channel, an aperture of {{c:aperture_mm|.0f}} mm, a focal length of {{c:focal_mm|.0f}} mm ($N = {{c:fnumber}}$), an in-band throughput of {{c:tau}} and a pixel pitch of {{c:pitch_um|.0f}} µm. The atmosphere is uniform, with no extinction and no path radiance: all-direct irradiance of {{c:irradiance}} $\mathrm{W\,cm^{-2}\,\mu m^{-1}}$, spectrally constant. The window is the template's native array of {{c:native_window}} × {{c:native_window}} pixels ({{c:n_native}} renders) or a region of interest of {{c:small_window}} × {{c:small_window}} pixels centred on the target ({{c:n_small}} renders).

## Execution

Every specification states one rendering thread and seed {{c:seed}}. Each render runs alone through the SDK's layered job (`Simulation.run`), with a per-run home directory so that DIRSIG's material caches stay with the run, and is reduced by `scripts/s2s_measure.py`. The harness writes one record per specification to `docs/data/s2s_results.jsonl`: the specification and run identifier, the sha256 of each product, the full-pixel signal and the measurements below. A SatSim control runs through the same harness and the SatSim adapter. The products are not kept; the section on determinism states why a record can be regenerated from its specification.

## Closed forms

A pixel wholly on a plate of reflectance $\rho$ facing a Sun at zenith angle $\theta_s$ collects, over an exposure $t$,
$$S = \frac{\rho\,E\cos\theta_s}{\pi}\;\frac{\tau\,\pi D^2}{4 f^2}\;\frac{1}{1 + 1/(4N^2)}\;t\int s(\lambda)\,d\lambda$$
photo-electrons per unit area of focal plane, with $E$ the irradiance, $D$ the aperture diameter, $f$ the focal length, $\tau$ the throughput and $s(\lambda)$ the channel's relative response times its quantum efficiency. The factor $1/(1 + 1/(4N^2)) = {{c:cone|.6f}}$ is the exact aperture cone; DIRSIG applies it and a paraxial chain does not. The full-pixel signal $S_\mathrm{full}$ is $S$ for $\rho = {{c:rho}}$ and $\theta_s = 0$: {{c:full_pixel_5ms|sci2}} $\mathrm{e^-\,m^{-2}}$ in {{c:exp_baseline_ms|.0f}} ms. Every closed form below is a number of full pixels.

At range $R$ the pixel footprint is $g = R\,p/f$ for pitch $p$. A plate of area $A$ seen at angle $\theta_v$ off its normal holds
$$n_\mathrm{plate} = \frac{A\cos\theta_v\cos\theta_s}{g^2}.$$
A Lambertian sphere of radius $r$ at phase angle $a$ holds
$$n_\mathrm{sphere} = \frac{2\pi r^2}{3 g^2}\,\Phi(a), \qquad \Phi(a) = \frac{\sin a + (\pi - a)\cos a}{\pi},$$
with $a$ the look angle plus the solar zenith (the Sun opposite the sensor in the look plane). A target moving at relative speed $v$ across the line of sight sweeps
$$b = \frac{v\,t}{g}$$
pixels during the exposure, starting at the task time; its row profile is a boxcar of length $b$ convolved with the plate's width and the pixel. The bars of family II and III have the level $(\rho_\mathrm{bar}/\rho)\cos\theta_s$ and, seen at angle $\theta$ from a footprint $g_b$ at the background's slant range, the period $\Lambda\cos\theta/g_b$ pixels for a bar period $\Lambda$. The signal is linear in the exposure.

## Window and native size

The region of interest changes which pixels the adaptive sampler visits and the sequence of random draws each receives, so a small-window image is not a crop of the native one. Its image sum is {{c:window_hyper|.5f}}, {{c:window_resolved|.5f}} and {{c:window_unres|.5f}} of the native record's for the same {{c:wsize_hyper|.2f}}, {{c:wsize_resolved|.2f}} and {{c:wsize_unres|.2f}} px targets. A small-window measurement of an angle is therefore taken against the small window's own nadir record of the same target where one exists.

## Measurements

*Flux closure* is the image sum over $S_\mathrm{full}$, divided by the closed form. The sum is over the whole frame for the still targets of families I and III, whose backstops are black, over a box about the streak for the blur groups of family II, over the target's rows for the look group, and over a box of {{c:bg_box}} × {{c:bg_box}} pixels about the sphere in front of the barred background. The *half-level count* is the number of pixels at or above half of $S_\mathrm{full}$, divided by the closed form. The *streak length* is the length $b$ of the swept-plate model fitted by least squares, with start and length free, to the mean of the plate's interior rows, divided by the closed form; a plate under about six pixels across, which has no interior row, is fitted in its column sums divided by its width. A sweep shorter than {{c:min_sweep_px|.0f}} px is not compared with its closed form: a still plate fits a sweep of {{r:s2s2-blur-static-e5ms:streak_length:measured|.2f}} px at {{c:wsize_hyper|.2f}} px across and {{r:s2s2-blur-static-r200km-e20ms-w64:streak_length:measured|.2f}} px at {{c:size_static_small|.2f}} px across from the spread of DIRSIG's optics alone, which the boxcar model does not contain. The *centre offset* of a SatSim control is the distance of the target's mid-exposure centre from its intended position. The *deficit* of a measurement is one minus the measurement over its closed form; a negative deficit is an excess.

No record carries a tolerance. The regression test of the records (`tests/test_s2s_results.py`) holds each closed-form case to the largest residual its records show, rounded up in the third significant digit, so that a record moving further from its closed form fails (Table {{n:tolerances}}). These are measured residuals, not acceptance thresholds.

{{t:tolerances}}

Table: Regression tolerances of the closed-form cases and the residual each bounds.

# Results {#sec:results}

## Hyperresolved targets

The {{c:plate_hyper|.0f}} m plate at nadir, from {{c:hyper_side_hi|.2f}} to {{c:hyper_side_lo|.2f}} px across, closes to between {{c:hyper_range_lo|.5f}} and {{c:hyper_range_hi|.5f}} (Table {{n:hyperresolved}}). Its peak pixel is $S_\mathrm{full}$ to {{c:hyper_peak_dev|sci}}. The half-level count is {{r:s2s-hyperresolved-r12p5km-v0mps-e5ms-l0-z0-d0:half_level_count|.4f}} of the closed form at the shortest range and {{r:s2s-hyperresolved-r25km-v0mps-e5ms-l0-z0-d0:half_level_count|.4f}} beyond: edge pixels partly on the plate fall below half level, and the count depends on how the edges fall on the pixel grid. The residual of the flux closure grows as the edge pixels become a larger share of the signal. Its sign is not systematic: at {{c:seed_range_lo|.0f}} and {{c:seed_range_hi|.0f}} km, seeds {{c:seed2}} and {{c:seed3}} give {{d:seed2_50km}} and {{d:seed3_50km}}, and {{d:seed2_100km}} and {{d:seed3_100km}}, against {{r:s2s-hyperresolved-r50km-v0mps-e5ms-l0-z0-d0|.5f}} and {{r:s2s-hyperresolved-r100km-v0mps-e5ms-l0-z0-d0|.5f}} for seed {{c:seed}} (scratch renders, Appendix B). The images at {{c:exp_lo_ms|.0f}} and {{c:exp_hi_ms|.0f}} ms are the {{c:exp_baseline_ms|.0f}} ms image scaled by the exposure to {{c:tol_TOL_EXPOSURE|sci}}.

{{t:hyperresolved}}

Table: The {{c:plate_hyper|.0f}} m plate at nadir, solar zenith zero, {{c:exp_baseline_ms|.0f}} ms, native window.

The cosine laws hold to the scatter of the sampling (Table {{n:angles}}). The plate seen off its normal follows $\cos\theta_v$ to {{c:tol_TOL_LOOK|sci}}, the Sun off the normal $\cos\theta_s$ to {{c:tol_TOL_SUN|sci}}, and both together, up to a phase angle of {{c:phase_plate_max|.0f}} degrees, $\cos\theta_v\cos\theta_s$ to {{c:tol_TOL_PLATE_LOOK_SUN|sci}}. Against the barred background the plate's rows follow $\cos\theta_v$ to {{c:tol_TOL_LOOK_BACKGROUND|sci}} up to {{c:look_bg_max|.0f}} degrees, and the bar period follows its closed form to {{c:tol_TOL_PERIOD|sci}}. At {{c:look_bg_limit|.0f}} degrees the line of sight through the plate passes beyond the background's edge, and the plate's flux falls to {{r:s2s2-look-l75|.4f}}: a pixel's sampling ends at its first path that reaches DIRSIG's earth core, an absorbing surface about {{d:core_depth_m}} m below the scene origin, so a target with nothing behind it is undersampled. The {{c:sphere_hyper|.0f}} m sphere follows $\Phi(a)$ from phase {{c:phase_lo|.0f}} to {{c:phase_hi|.0f}} degrees to between {{c:phase_hyper_lo|.4f}} and {{c:phase_hyper_hi|.4f}}, the residual growing as the lit crescent narrows to a few edge pixels; at a fixed path count the phase-{{c:phase_hi|.0f}} render reads {{d:sphere_fixed1000_a150}}. At phase {{c:split_phase|.0f}} degrees the three splits of the angle between the look and the Sun agree to {{c:split_spread|sci}}. The bars follow $\cos\theta_s$ to {{c:tol_TOL_BAR|sci}} up to a solar zenith of {{c:bar_zen_max|.0f}} degrees, in the same frames as the sphere.

{{t:angles}}

Table: Angle cases of hyperresolved targets. For a plate the closed form holds the cosine, and the last column divides by the record of the same target at nadir.

## Resolved targets

At {{c:wsize_resolved|.2f}} px across, the plate and the sphere follow the same closed forms with residuals a few times larger (Table {{n:resolved}}). The plate's image scales exactly with the exposure, and the Sun alone scales it by $\cos\theta_s$ to {{c:tol_TOL_RESOLVED_SUN_ALONE|sci}}. Look and Sun together at {{c:resolved_ls|.0f}} degrees each read {{c:resolved_ls_rel|.4f}} of the closed form against the window's nadir record. Seen {{c:resolved_look|.0f}} degrees off its normal with the Sun at the zenith, the plate reads {{c:resolved_look_corner|.4f}} on a pixel corner and {{c:resolved_look_off|.4f}} off it: deficits of {{c:resolved_look_corner|def:.1f}} and {{c:resolved_look_off|def:.1f}} % that do not depend on placement and are not isolated. The sphere follows $\Phi(a)$ to {{c:tol_TOL_RESOLVED_SPLIT|sci}} at {{c:split_phase|.0f}} degrees however the angle is split, and reads {{r:s2s3-phase-hyperresolved-a120-r100km-l60-z60-w64|.4f}} at {{c:phase_resolved_hi|.0f}} degrees, where the lit crescent is a pixel or two wide. The still {{c:size_static_small|.2f}} px plate reads {{r:s2s2-blur-static-r200km-e20ms-w64|.4f}}. A platform on its orbit with its line of sight on a {{c:size_orbit|.2f}} px plate holds it still over the exposure: the {{c:orbit_lo_ms}} ms and {{c:orbit_hi_ms|.0f}} ms renders both read {{r:s2s2-orbit-e20ms|.4f}}.

{{t:resolved}}

Table: Resolved targets, small window. The last column divides a plate's flux closure by the window's nadir record of the same plate.

## Unresolved targets

Without a surface behind it, a sub-pixel plate is lost: the first path of a pixel that misses it reaches the earth core and ends the pixel's sampling. With the backstop, the labelled plate's pixels take {{d:labelled_paths}} paths each, and its flux closes to {{r:s2s-unresolved-r12p5km-v0mps-e5ms-l0-z0-d0|.4f}} at {{c:unres_near_px_lo|.2f}} px across and {{r:s2s-unresolved-r25km-v0mps-e5ms-l0-z0-d0|.4f}} at {{c:unres_near_px_hi|.2f}} px (Table {{n:unresolved}}). From {{c:unres_far_px_hi|.2f}} px down the image is a count of a few tens of hits or fewer, and the closure scatters between {{c:unres_far_lo|.3f}} and {{c:unres_far_hi|.3f}}. Records of targets under {{c:min_px}} px across are excluded from the envelope below for that reason. Without the label a pixel takes at most {{d:unlabelled_paths}} paths: the unlabelled plate reads {{r:s2s-unresolvedplain-r12p5km-v0mps-e5ms-l0-z0-d0|.3f}} at {{c:unres_near_px_lo|.2f}} px and {{r:s2s-unresolvedplain-r25km-v0mps-e5ms-l0-z0-d0|.3f}} at {{c:unres_near_px_hi|.2f}} px, {{r:s2s-unresolvedplain-r50km-v0mps-e5ms-l0-z0-d0|.3f}} at {{c:unres_far_px_hi|.2f}} px, and nothing beyond.

The sub-pixel position moves the closure by a few percent where the plate fills a third of a pixel or more: at {{c:unres_near_px_hi|.2f}} px, offsets of a quarter, a half and three quarters of a pixel from the pixel corner read {{c:offsets_25km}}. Seen off its normal, the {{c:wsize_unres|.2f}} px plate centred on a pixel corner reads {{c:corner_hi|.4f}} to {{c:corner_lo|.4f}} of the closed form from {{c:corner_look_lo|.0f}} to {{c:corner_look_hi|.0f}} degrees, below it in every case, by {{d:corner_sigma_lo}} to {{d:corner_sigma_hi}} standard deviations of the hit count, and further below as the look grows. At {{c:corner_look_60|.0f}} degrees, moved a quarter and a half of a pixel off the corner, it reads {{r:s2s-unresolved-r25km-v0mps-e5ms-l60-z0-d0p25-w64|.4f}} and {{r:s2s-unresolved-r25km-v0mps-e5ms-l60-z0-d0p5-w64|.4f}}. The deficit is therefore a property of a target lying across pixel edges, not of the look angle; the unlabelled plate at the same geometry rests on too few hits ({{r:s2s-unresolvedplain-r25km-v0mps-e5ms-l60-z0-d0-w64|.3f}}) to separate an effect of the label.

{{t:unresolved}}

Table: The {{c:plate_small|.1f}} m plate. Range and offset cases are native renders at nadir; look cases use the small window.

The labelled {{c:sphere_small|.2f}} m sphere ({{c:wsize_unres|.2f}} px across) follows $\Phi(a)$ within its hit count (Table {{n:spheres}}): {{c:phase_unres_lo|.3f}} to {{c:phase_unres_hi|.3f}} of the closed form, with the excess at large phase where the lit part of the disc is a few percent of it. Over seeds at reduced size its closure has a standard deviation of {{d:sphere_seed_sigma_a0}} at phase {{c:phase_lo|.0f}} and {{d:sphere_seed_sigma_a150}} at phase {{c:phase_hi|.0f}}; with the path count of the focal plane fixed, the phase-{{c:phase_hi|.0f}} render reads {{d:sphere_200k_a150}}.

{{t:spheres}}

Table: The {{c:sphere_small|.2f}} m sphere at {{c:sphere_range_km|.0f}} km, native window.

## Motion and shutter blur

Platform motion and target motion conserve the hyperresolved plate's flux to between {{c:blur_flux_lo|.4f}} and {{c:blur_flux_hi|.4f}} over exposures that sweep {{c:sweep_lo|.2f}} to {{c:sweep_hi|.2f}} px (Table {{n:streaks}}). The two motions give the same ratios to four digits at every size, and the background streaks only under platform motion. The fitted streak reads {{c:streak_lo|.4f}} to {{c:streak_hi|.4f}} of $v\,t/g$ for sweeps of {{c:sweep_short_lo|.2f}} to {{c:sweep_short_hi|.2f}} px and plates of {{c:streak_size_lo|.2f}} to {{c:streak_size_hi|.2f}} px, independent of the plate's width. DIRSIG5 spreads ray times uniformly over the exposure and does not use the platform's temporal sample count: at {{c:n2_samples}} samples instead of {{c:integration_samples}} the image is {{c:n2_identical}}.

Combined motion conserves the flux of the {{c:wsize_hyper|.2f}} px plate ({{r:s2s2-blur-both-e5ms-w64|.4f}}) but not of smaller ones: {{r:s2s2-blur-both-r100km-e20ms-w64|.4f}} at {{c:wsize_resolved|.2f}} px and {{r:s2s2-blur-both-r200km-e20ms-w64|.4f}} at {{c:size_static_small|.2f}} px, where platform and target motion alone hold it to {{c:single_small_dev|pct:.1f}} %. The cause is not isolated.

A labelled sub-pixel plate moving across the field loses flux: {{r:s2s-unresolved-r12p5km-v1000mps-e5ms-l0-z0-d0-w64|.4f}} at {{c:size_moving_big|.2f}} px sweeping {{c:sweep_moving_big|.2f}} px, and {{r:s2s-unresolved-r25km-v1000mps-e5ms-l0-z0-d0-w64|.4f}} at {{c:size_moving_small|.2f}} px sweeping {{c:sweep_moving_small|.2f}} px. The label raises the path count of the pixels holding the object at about the task time only. The other streak pixels start at the adaptive minimum of {{d:min_paths}} paths and stop there when no path hits the plate; in a truth render of a longer streak about {{d:streak_hit_fraction}} % of them were hit at all.

{{t:streaks}}

Table: Family II streaks and their SatSim controls. The closed-form sweep is $v\,t/g$; a sweep under {{c:min_sweep_px|.0f}} px reads long by the optics' spread.

## The sampling-effect envelope

Table {{n:envelope}} groups the {{c:n_envelope}} DIRSIG records of targets at least {{c:min_px}} px across by size, motion and label, with the range of their deficits and the SatSim controls of the same geometries. {{c:n_excluded}} records are outside it: targets under {{c:min_px}} px, the look at {{c:look_bg_limit|.0f}} degrees, and the orbit point whose range is the element set's. Of its {{c:n_env_rows}} rows, {{c:n_env_quiet}} hold every deficit within {{c:quiet|pct:.0f}} %.

{{t:envelope}}

Table: Deficits against the closed forms by target size in pixels, motion and label.

# The SatSim control and the attribution of the deficits {#sec:satsim}

SatSim models a target as a point (a Lambertian sphere of any diameter) or as a sprite carrying a stated flux, deposits it on a frame oversampled {{d:satsim_osf}} times, and has no per-pixel ray sampling. {{c:n_satsim_words}} controls image the geometries of DIRSIG's deficits at the same window, with no optical spread (DIRSIG's specifications state none), with the target's flux from SatSim's sphere model or set by construction for a sprite (Table {{n:satsim}}). Every control holds its flux to {{c:satsim_flux_max|sci}}, the floor SatSim applies to each pixel's count, and places the target within {{c:satsim_centre_max|.3f}} px of its intended position.

{{t:satsim}}

Table: SatSim controls and their DIRSIG counterparts.

The pixel-corner deficit is absent in SatSim: a point on the corner divides into four equal pixels and keeps its flux, and so does the {{c:corner_look_60|.0f}} degree plate's rectangle across the four pixels' edges. DIRSIG's own plate moved off the corner holds the closed form. The deficit at the corner is therefore DIRSIG's sampling of a sub-pixel object lying across pixel edges; its mechanism inside the hypersampled sampling is not isolated.

The streak shortfall is absent in SatSim, which reads {{c:satsim_streak_lo|.4f}} to {{c:satsim_streak_hi|.4f}} of the closed form through the same fit where DIRSIG reads {{c:dirsig_ctl_streak_lo|.4f}} to {{c:dirsig_ctl_streak_hi|.4f}}. Controls outside the run-spec vocabulary, in which the assembled job's platform file fixes DIRSIG's path count per pixel, isolate the cause (Appendix B). At a fixed {{d:fixed_paths_hi}} paths per pixel the sweep reads {{d:fixed1000_both_25km_5ms}} and {{d:fixed1000_target_100km_20ms}} at the two geometries. At a fixed {{d:fixed_paths_lo}} paths it reads {{d:fixed20_seed1}} and {{d:fixed20_seed2}} for two seeds, not the $(n-1)/n$ of a sweep sampled at $n$ instants. The shortfall goes with DIRSIG's adaptive stop, which ends a pixel's sampling between {{d:min_paths}} and {{d:unlabelled_paths}} paths; how it shortens the share of the ramp pixels is not isolated.

The flux lost by a moving sub-pixel object is absent in SatSim: the moving sprite and sphere at {{c:size_moving_big|.2f}} px keep {{r:s2s-satsim-ctl-plate-r12p5km-v1000mps-e5ms-l0-d0-w64|.6f}} and {{r:s2s-satsim-ctl-sphere-r12p5km-v1000mps-e5ms-l0-d0-w64|.6f}} of it where DIRSIG keeps {{r:s2s-unresolved-r12p5km-v1000mps-e5ms-l0-z0-d0-w64|.4f}}. No control exists at {{c:size_moving_small|.2f}} px. Three deficits have no attribution in the records: combined motion at a resolved size, the moving plate at {{c:size_moving_small|.2f}} px, and the resolved plate's look alone. Each needs a fixed path count, which no run-spec member states.

# Determinism and reproducibility {#sec:determinism}

With one rendering thread and a stated seed, DIRSIG5 repeats a render bit for bit. All {{d:rerender_total}} family I and II images rendered again on a later day carry the digest first recorded ({{d:rerender_same}} of {{d:rerender_total}}). {{c:n_home_words}} jobs, each rendered under a fresh home directory, the same one again and the user's, give equal products in {{c:home_equal}} of {{c:n_home}} cases with {{c:home_writes}} writes to the home directory. Batches of up to {{c:conc_max_n}} concurrent one-thread jobs give the single job's image in {{c:conc_equal}} of {{c:n_conc}} batches. Two full one-thread renders of the install's LightCurve1 demonstration are identical in all {{d:lc_outputs}} outputs.

At more than one thread the result depends on the work's division (Table {{n:determinism}}). A frame of {{c:det_samples|thou}} values from the same demonstration, rendered at one, two, four and the default thread count, gives two patterns. At two and four threads, values differ by at most {{c:det_fo_maxrel|sci}} relative, a few single-precision roundings from the order of summation; two renders at two threads were identical, two at four were not. At the default count, {{c:det_td_px_lo}} to {{c:det_td_px_hi}} of the {{c:det_lit|thou}} lit pixels drew other random samples and differ in many bands by up to {{c:det_td_maxrel|pct:.1f}} % of a value; the frame's sum moves by at most {{c:det_td_sum|sci}} relative. In a sweep of the install's demonstrations at the default thread count, {{d:sweep_demos_differ}} of {{d:sweep_demos}} gave different digests on repeat. One thread costs {{d:thread_cost_lo}} to {{d:thread_cost_hi}} times the default wall time. A seed alone does not make repeats identical; the thread count must be one, and it is part of the specification and of its run identifier.

{{t:determinism}}

Table: Value-by-value comparison of one frame of LightCurve1 between renders at one (`t1`), two (`t2`), four (`t4`) and the default (`td`) number of threads.

# Limitations {#sec:limitations}

*Window.* The small window moves the image sum by up to {{c:window_unres|def:.1f}} % for a sub-pixel target. Small-window angle cases are referred to the window's own nadir record; a small-window record is not a substitute for a native one.

*Label.* At this template's multiplier a labelled pixel takes {{d:labelled_paths}} paths and an unlabelled one at most {{d:unlabelled_paths}}, so a labelled and an unlabelled sub-pixel target differ in hit-count scatter by a factor of about {{c:label_scatter_factor|.1f}}, and an effect of the label itself on a deficit of a few percent cannot be separated from that scatter.

*Unexpressible cases.* The run specification cannot state a fixed path count per pixel, the control that would test every unattributed deficit; it was applied here only by editing an assembled job. Every generated scene has one Lambertian material, so a specular facet is not exercised. A specification takes one scene, and no committed scene holds an Earth model, so the Earth's limb and albedo as a background are not exercised. One task window holds one capture. A surface more than about {{d:path_limit_km}} km along a ray inside the scene was not intersected, which bounds the depth of a scene's geometry.

*Optics.* The sensor specification has no point-spread function; DIRSIG applies an aperture-dependent spread of its own, fitted as a Gaussian of $\sigma = {{d:spread_sigma_px}}$ px, which no member changes.

*Scope.* One sensor, one band, black backgrounds and a uniform atmosphere; no comparison with a real sensor's images and no hardware validation.

# References {#sec:references}

DIRSIG5 documentation, Rochester Institute of Technology, release {{c:dirsig_version}} as installed.

SatSim {{c:satsim_version}} software and documentation, as installed.

Standard radiometry: the Lambertian sphere's phase function and the radiance of a Lambertian surface.

# Appendix A: case definitions {#sec:appendix-a}

{{t:cases}}

Table: Specifications by family and group: the number of specifications, the number recorded, and the values of each axis.

# Appendix B: controls outside the records {#sec:appendix-b}

The figures below are stated in the committed characterization and determinism documents and are not records: scratch renders in which the assembled job was edited (a fixed path count, another seed), truth renders, and counts. `docs/study/data/document_figures.csv` holds each with its document and the commit that added it.

{{t:controls}}

Table: Figures from committed documents used in the text.
