# Changelog
All notable changes to this project will be documented in this file.

## [Unreleased]

### Added
- A new `array_signal_source` table that contains array-wide information about the
commanded signal source (one of "antenna", "load", "noise", "digital_same_seed", or
"digital_different_seed").
- A new `correlator_component_event_time` table that records when correlator components
had an event related to normal observing (f-engine sync, x-engine integration start,
catcher start, stop or stop identified via a timeout).

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
