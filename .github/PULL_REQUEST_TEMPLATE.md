<!--- Provide a general summary of your changes in the Title above -->

## Description
<!--- Describe your changes in detail -->

## Motivation and Context
<!--- Why is this change required? What problem does it solve? -->
<!--- If it fixes an open issue, please link to the issue here. If this PR closes an issue, put the word 'closes' before the issue link to auto-close the issue when the PR is merged. -->

## Types of changes
<!--- What types of changes does your code introduce? Put an `x` in all the boxes that apply: -->
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] Schema change (any change to the SQL tables)
- [ ] New feature without schema change (non-breaking change which adds functionality)
- [ ] Change associated with a change in redis structure
- [ ] Breaking change (fix or feature that would cause existing functionality to change)
- [ ] Version change
- [ ] Build or continuous integration change
- [ ] Other

## Checklist:
<!--- You shoud remove the checklists that don't apply to your change type(s) -->
<!--- Go over all the following points, and replace the space with an `x` in all the boxes that apply. -->
<!--- If you're unsure about any of these, don't hesitate to ask. We're here to help! -->

Bug fix checklist:
- [ ] My code follows the code style of this project.
- [ ] My fix includes a new test that breaks as a result of the bug (if possible).
- [ ] I understand the updates required onsite (detailed in the readme) and I will make those
changes when this is merged.
- [ ] Unit tests pass **on site** (This is a critical check, CI can differ from site).
- [ ] I have updated the [CHANGELOG](https://github.com/HERA-Team/hera_mc/blob/main/CHANGELOG.md).

Schema change:
- [ ] My code follows the code style of this project.
- [ ] I have added or updated the docstrings associated with my feature using the [numpy docstring format](https://numpydoc.readthedocs.io/en/latest/format.html).
- [ ] I have created an alembic version file to produce the schema change.
- [ ] I have tested looping upgrading and downgrading the alembic version and tests pass consistently.
- [ ] I have updated or created monitoring scripts and daemons so any new tables will be automatically populated (if appropriate).
- [ ] I understand the updates required onsite (detailed in the readme) and I will make those
changes when this is merged.
- [ ] I have updated the schema documentation document with my changes (under docs/mc_definition.tex)
- [ ] I have added tests to cover my new feature.
- [ ] Unit tests pass **on site** (This is a critical check, CI can differ from site).
- [ ] I have updated the [CHANGELOG](https://github.com/HERA-Team/hera_mc/blob/main/CHANGELOG.md).

New feature without schema change checklist:
- [ ] My code follows the code style of this project.
- [ ] I have added or updated the docstrings associated with my feature using the [numpy docstring format](https://numpydoc.readthedocs.io/en/latest/format.html).
- [ ] I understand the updates required onsite (detailed in the readme) and I will make those
changes when this is merged.
- [ ] I have added tests to cover my new feature.
- [ ] Unit tests pass **on site** (This is a critical check, CI can differ from site).
- [ ] I have updated the [CHANGELOG](https://github.com/HERA-Team/hera_mc/blob/main/CHANGELOG.md).

Change associated with a change in redis structure:
- [ ] My code follows the code style of this project.
- [ ] I have updated the redis dump in our test data to reflect the most recent structure onsite.
- [ ] I understand the updates required onsite (detailed in the readme) and I will make those
changes when this is merged.
- [ ] Unit tests pass **on site** (This is a critical check, CI can differ from site).
- [ ] I have updated the [CHANGELOG](https://github.com/HERA-Team/hera_mc/blob/main/CHANGELOG.md).

Breaking change checklist:
- [ ] My code follows the code style of this project.
- [ ] I have updated the docstrings associated with my change using the [numpy docstring format](https://numpydoc.readthedocs.io/en/latest/format.html).
- [ ] I have detailed any changes required to other HERA repos above and I will coordinate
implementing the changes across all the repos.
- [ ] I understand the updates required onsite (detailed in the readme) and I will make those
changes when this is merged.
- [ ] I have added tests to cover my changes.
- [ ] Unit tests pass **on site** (This is a critical check, CI can differ from site).
- [ ] I have updated the [CHANGELOG](https://github.com/HERA-Team/hera_mc/blob/main/CHANGELOG.md).

Version change checklist:
- [ ] I have updated the [CHANGELOG](https://github.com/HERA-Team/hera_mc/blob/main/CHANGELOG.md) to put all the unreleased changes under the new version (leaving the unreleased section empty).

Build or continuous integration change checklist:
- [ ] If required or optional dependencies have changed (including version numbers), I have updated the readme to reflect this.

Other:
- [ ] My code follows the code style of this project.
- [ ] I understand the updates required onsite (detailed in the readme) and I will make those
changes when this is merged.
- [ ] Unit tests pass **on site** (This is a critical check, CI can differ from site).
- [ ] I have updated the [CHANGELOG](https://github.com/HERA-Team/hera_mc/blob/main/CHANGELOG.md).
