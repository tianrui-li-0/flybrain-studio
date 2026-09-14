# Validation

## Official data migration — 2026-09-14

Direct official FlyWire GCS CSV downloads passed server MD5/length checks.
The converter verified SHA-256 and preserved exact string root IDs, positive
synapse counts and directed endpoints. Current data has 139,255 neurons,
2,700,513 aggregated directed edges, 3,869,878 source rows and 34,153,566
synapses represented by those rows. All neurons have annotation coordinates.

All 10 automated tests passed, including count conservation across neuropils,
rejection of altered input/nonofficial URLs, propagation and disconnected
controls, RGB/audio encoding and media seeking. Native Qt integration passed
with 180,655 exported events: video drag/drop, pause, seek, filters, picking,
camera reset, bilingual layout, point sizes, sampling collapse, sound decoding,
monitor playback and export. Counts below describe historical versions only.

These are software checks, not evidence of biological accuracy or improved
perception. Current executable directory: release-official.
The freshly packaged executable also passed a standalone launch/capture check:
exit code 0, 7.96 simulated seconds, RGB and audio input enabled, no engine
notice. Its 3D view and activity plots were visually inspected.

## Historical validation before the migration

Resizable/bilingual update: native integration verifies the left panel exceeds its former 355 px limit, layout reset returns it to 300 px, Chinese/English switching updates controls, and translated hemisphere/camera options still operate on stable indices without restarting the neural engine. Latest local executable is in release-bilingual.

Tested on this Windows 11 host with Python 3.14.6, PySide6 6.11.2 and the pinned requirements.

- Dataset: 139,255 distinct IDs; 2,698,236 indexed directed edges; all 139,255 IDs matched to real annotation coordinates; 11,153 annotated photoreceptors.
- Four automated model tests passed: directed one-step propagation and inhibitory response; reset and refractory behavior; full-graph dark / illuminated / disconnected controls; aspect-preserving portrait letterbox.
- Native Qt integration test passed: play/pause, local video drag/drop, seek and state reset, category filtering, ID search, 3D projected point picking, camera orbit, all-neuron spike export, rejection of an invalid video while retaining the prior source.
- Integration export contained 154,779 spike records with valid root IDs and simulation times inside the requested rolling window.
- Standalone executable loaded its bundled data and rendered the full 3D point cloud and running plots. A conda/Windows ICU name collision discovered during this check was fixed in the checked-in PyInstaller spec.
- `preview.png` is an actual screenshot produced by the standalone application.

This verifies software behavior on this host, not biological accuracy. The model is not fitted to electrophysiological measurements. See README.md for the exact data transformations, input approximation and display sampling.

## Color/audio update

Navigation update: verified clearing selection with the button and Escape empties the marker/connection geometry, polling continues with no selected neuron, and view reset restores centre, distance and field of view while stopping auto-rotation. Full desktop integration passed after these changes.

- Three additional sensory tests passed: RGB changes neural inputs and spikes; gray matches across channels; resolution selection; auditory-only activation with disconnected graph; silence and input-off controls; frequency-band selectivity of the engineering encoder; MP4/AAC decode with forward/backward seeking, silence and EOF recovery.
- Extended desktop integration passed: sampling collapse/expand, independent resting/firing sizes and restoration, RGB/gray switch, audio toggle and defaults, decoding an audiovisual MP4, and Qt original-audio playback state without decoder errors.
- The original four full-graph/model tests still pass.
