
# Change Log

## [0.9.2] - 2016-12-05
- modified "raw" subcommand so that it does not execute /redfish or /redfish/v1 before executing the raw api
- changed default behavior to NOT always send a /redfish query and verify that the remote service supports the specified redfishProtocol before executing the API
- added a new -C option to invoke the "Check remote RedfishProtocol Version" before executing function.  If -R "Latest" is set by the user, then the -C flat is auto-set since "Latest" means use the latest mutually supported version
- changed the default -R <redfishVersion> from "Latest" to "v1" since Latest will require the check and add an additional Get /Redfish query
- added elapsed execution time output if -ss or -sss is specified
- updated usage for the above changes

## [0.9.1] - 2016-09-06
- Initial Public Release -- supports most Redfish 1.0 features
