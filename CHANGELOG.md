# Changelog
All notable changes to this project will be documented in this file.

## [Unreleased]

### Added
- The new `correlator_file_queues` and `correlator_file_eod` tables to track the
internal file handling in the correlator and the handoff to RTP.
- A new `hera_auto_spectrum` table to hold the full autocorrelation spectra, rather than
just the median values that are currently recorded in `hera_autos` table.
- A new `correlator_catcher_file` table to track the files written by the catcher.
- A `tag` column to the `hera_obs` table.
- A new `snap_feng_init_status` table to track whether SNAPs worked properly, errored,
or were exluded because there were too many SNAPs during F-engine initialization.
- New columns `is_programmed`, `adc_is_configured`, `is_initialized`, `dest_is_configured`,
`version`, and `sample_rate`, to the `snap_status` table and added a new `snap_input`
table that breaks out the snap inputs (either "adc" or "noise-%d" where %d is the seed)
for each snap channel.
- A new `array_signal_source` table that contains array-wide information about the
commanded signal source (one of "antenna", "load", "noise", "digital_same_seed", or
"digital_different_seed").
- A new `correlator_component_event_time` table that records when correlator components
had an event related to normal observing (f-engine sync, x-engine integration start,
catcher start, stop or stop identified via a timeout).

### Changed
- Add compatibility with numpy 2.0
- Use psycopg3 (on pypi as `psycopg`) rather than psycopg2 to enable numpy 2.0
compatibility.
- Updated minimum dependency versions: cartopy>=0.21, numpy>=1.23, pyyaml>=5.4.1
sqlalchemy>=2.0, python>=3.10
- Updated minimum optional dependency versions: h5py>=3.4, pytest>=6.2.5
- Add compatibility with pyuvdata>=3.0
- Dropped support for python 3.7.
- The logic for time filtering in real time getter methods in mc_session to support
getting the most recent table entries at some point in the past (the last value before
the time of interest)

### Fixed
- Fixed incompatibilities with SQLAlchemy 2.0.

### Removed
- The following table bindings were removed (but the tables will not be deleted on site):
`correlator_control_state`, `correlator_control_command`,`correlator_take_data_arguments`,
`correlator_config_command`

## [3.0.0] - 2022-05-25

### Added
- Added `cm_active.get_active` as a courtesy function to return a single ActiveData
object without setting up an explicit session.  If one wants many, one should
setup a session using the context manager and use the ActiveData class directly.
- Added `cm_hookup.get_hookup` as a courtesy function to return a dictionary
of hookup dossiers without setting up an explicit session.  If one wants many,
one should setup a session using the context manager and use the Hookup class
directly.

### Changed
- The classes `cm_hookup.Hookup`, `cm_active.ActiveData`, and
`cm_handling.Handling` all now require an explicit session to be passed to them.
This changes the standard way these classes have been used and breaks the API.
For `cm_active` and `cm_hookup` see the new courtesy functions above --
generally you can call those once for the broad set of data you want.
- Functions and methods in the files `cm_revisions.py` and `cm_sysutils.py`
have generally been changed to require an explicit session to be passed,
however that is not necessarily uniform so if you import either you should
check the specific functions called.

## [2.0.1] - 2022-04-29

## [2.0.0] - 2022-04-25

## [1.0.0] - 2018-12-04
