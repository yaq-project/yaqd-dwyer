# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

## [2023.5.0]

### Added
- 16b: temperature regulation value now exposed via properties

### Fixed
- 16b: added forgotten dictionarys converting parameters from config into minimalmodbus
- 16b: broken ramping

## [2023.3.0]

### Added
- 16b: extra properties for PID settings
- 16b: now forces usage of PID profile 0 only

## [2023.1.0]

### Changed
- now ramps are parametrized using time delay, not rate

### Fixed
- various fixes from production involving infrequent error conditions

## [2022.7.0]

### Added
- initial release

[Unreleased]: https://github.com/yaq-project/yaqd-dwyer/compare/v2023.5.0...main
[2023.5.0]: https://github.com/yaq-project/yaqd-dwyer/compare/v2023.3.0...2023.5.0
[2023.3.0]: https://github.com/yaq-project/yaqd-dwyer/compare/v2023.1.0...2023.3.0
[2023.1.0]: https://github.com/yaq-project/yaqd-dwyer/compare/v2022.7.0...2023.1.0
[2022.7.0]: https://gihub.com/yaq-project/yaqd-dwyer/tags/v2022.7.0
