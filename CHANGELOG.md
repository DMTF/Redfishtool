# Change Log

## [1.1.4] - 2020-07-24
- Renamed the package to not conflict with the name of the script
- Added additional redfishtool.py script for Windows compatibility

## [1.1.3] - 2020-05-01
- Added inventory and sensor options

## [1.1.2] - 2020-04-10
- Made fix to collection listing to show members when optional properties are not present

## [1.1.1] - 2020-01-10
- Made fixes to properly format IPv6 URLs

## [1.1.0] - 2019-08-09
- Added support for getting Power and Thermal resources with a specified chassis, or leaving it unspecified if there is exactly one chassis

## [1.0.9] - 2019-07-12
- Added the ability to get credentials from the config file rather than specifying them on the command line

## [1.0.8] - 2018-11-30
- Made the "One" option enabled by default for Systems, Managers, and Chassis collections

## [1.0.7] - 2018-10-19
- Made fix to allow for 202 responses on operations

## [1.0.6] - 2018-10-12
- Fixed help output for the raw command

## [1.0.5] - 2018-09-21
- Fixed bug with nextLink handling
- Fixed parsing of `@odata.type` properties when they use an unversioned namespace

## [1.0.4] - 2018-02-02
- Fixed parsing of match argument when there are colons in the match data

## [1.0.3] - 2018-01-02
- Added support for PUT with raw commands
- Added support for getting log entries via the -E argument

## [1.0.2] - 2017-10-27
- Added support for leveraging the `@Redfish.ActionInfo` annotation if `@Redfish.AllowableValues` for Reset actions
- Added support for `--all` option to Systems and Chassis commands that perform update operations
- Fixed handling of the `setTimeOffset` argument

## [1.0.1] - 2017-06-15
- Created a script called `redfishtool` to be installed via `pip install redfishtool`

## [1.0.0] - 2017-06-01
- Added AccountService setusername operation to modify the UserName property in an existing account

## [0.9.3] - 2017-04-27
- Updated spelling in various usage print statements
- Forrected usage statement for SessionService login and logout subcommands
- Fixed error in collection list subcommand to show the path correctly
- Fixed password update so that it won't fail if using basicAuth to change user's own password.  It was failing if using basic auth of self user since the final get used the old credentials.
- Changed elapsed time calculation to measure execution time around request lib instead of using the internal request r.elapsed property.   0.9.2 was measuring exec time short in some cases as the internal elapsed prop measures execution time until 1st header is returned--not until all data is returned.

## [0.9.2] - 2016-12-05
- Modified "raw" subcommand so that it does not execute /redfish or /redfish/v1 before executing the raw api
- Changed default behavior to NOT always send a /redfish query and verify that the remote service supports the specified redfishProtocol before executing the API
- Added a new -C option to invoke the "Check remote RedfishProtocol Version" before executing function.  If -R "Latest" is set by the user, then the -C flat is auto-set since "Latest" means use the latest mutually supported version
- Changed the default -R <redfishVersion> from "Latest" to "v1" since Latest will require the check and add an additional Get /Redfish query
- Added elapsed execution time output if -ss or -sss is specified
- Updated usage for the above changes

## [0.9.1] - 2016-09-06
- Initial Public Release; supports most Redfish 1.0 features
