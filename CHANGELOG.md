# Change Log

## [1.0.2] - 2017-10-27
- added support for leveraging the `@Redfish.ActionInfo` annotation if `@Redfish.AllowableValues` for Reset actions
- added support for `--all` option to Systems and Chassis commands that perform update operations
- fixed handling of the `setTimeOffset` argument

## [1.0.1] - 2017-6-15
- created a script called `redfishtool` to be installed via `pip install redfishtool`

## [1.0.0] - 2017-6-1
- added AccountService setusername operation to modify the UserName property in an existing account

## [0.9.3] - 2017-4-27
- updated spelling in various usage print statements
- corrected usage statement for SessionService login and logout subcommands
- fixed error in collection list subcommand to show the path correctly
- fixed password update so that it won't fail if using basicAuth to change user's own password.  It was failing if using basic auth of self user since the final get used the old credentials.
- changed elapsed time calculation to measure execution time around request lib instead of using the internal request r.elapsed property.   0.9.2 was measuring exec time short in some cases as the internal elapsed prop measures execution time until 1st header is returned--not until all data is returned.

## [0.9.2] - 2016-12-05
- modified "raw" subcommand so that it does not execute /redfish or /redfish/v1 before executing the raw api
- changed default behavior to NOT always send a /redfish query and verify that the remote service supports the specified redfishProtocol before executing the API
- added a new -C option to invoke the "Check remote RedfishProtocol Version" before executing function.  If -R "Latest" is set by the user, then the -C flat is auto-set since "Latest" means use the latest mutually supported version
- changed the default -R <redfishVersion> from "Latest" to "v1" since Latest will require the check and add an additional Get /Redfish query
- added elapsed execution time output if -ss or -sss is specified
- updated usage for the above changes

## [0.9.1] - 2016-09-06
- Initial Public Release -- supports most Redfish 1.0 features
