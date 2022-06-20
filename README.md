Copyright 2016-2018 DMTF. All rights reserved.

# redfishtool

## About

***redfishtool*** is a commandline tool that implements the client side of the Redfish RESTful API for Data Center Hardware Management.

**Redfish** is the new RESTful API for hardware management defined by the DMTF Scalable Platform Management Forum (SPMF).  It provides a modern, secure, multi-node, extendable interface for doing hardware management.  The initial release included hardware inventory, server power-on/off/reset, reading power draw, setting power limits, reading sensors such as fans, read/write of ID LEDs, asset tags, and went beyond IPMI in functionality to include inventory of processors, storage, Ethernet controllers, and total memory.  New Redfish extensions have now been added to the spec and include firmware update, BIOS config, memory inventory, direct attached storage control, and the list grows.

***redfishtool*** makes it simple to use the Redfish API from a BASH script or interactively from a client command shell.

While other generic HTTP clients such as Linux curl can send and receive Redfish requests, ***redfishtool*** goes well beyond these generic HTTP clients by automatically handling many of the hypermedia and Redfish-specific protocol aspects of the Redfish API that require a client to often execute multiple queries to a redfish service to walk the hypermedia links from the redfish root down to the detailed URI of a specific resource (eg Processor-2 of Blade-4 in a computer blade system).  Specifically, redfishtool provides the following functions over curl:

* implements Redfish Session Authentication as well as HTTP Basic Auth
* walks the Redfish schema following strict interoperpbility processors...] to find find the targeted instance based on Id, UUID, URL or other attributes
* handles GETs for collections that are returned in multiple pieces--requiring client to read in a loop until the full collection is returned
* handles ETag and If-Match headers when PATCHing a resource to write properties
* implements many common set or action operations with simple commandline syntax (eg server reset, setting LEDs, assetTag, powerLimits, etc)
* negotiates the latest redfish protocol version between client and service (demonstrating the proper way to do this)
* can read specific properties of a resource, or expand collections to include all members of the collection expanded
* supports adding and deleting users, and common Redfish account service operations
* For debug, provides multiple levels of verbose output to add descriptive headers, and show what HTTP requests are being executed
* For debug, includes multiple levels of status display showing HTTP status codes and headers returned and sent 
* For easy parsing, outputs all responses in JSON format unless verbose or status debug options were specified 


## Why redfishtool?

1. ***redfishtool*** was originally written during the development of the Redfish specification to help find ambiguities in the spec.
1. ***redfishtool*** is now also being used to test interoperability between redfish service implementations.
1. In addition, ***redfishtool*** provides an example implementation for how a client can execute common server management functions like inventory; power-on/off/reset; setting power limits, indicator LEDs, and AssetTags, and searching a multi-node redfish service to find a specific node (with specific UUID, redfish Id, etc).  redfishtool follows strict rules of interoperability.  To support this goal, liberal comments are added throughout code to explain why each step is being executed.
1. As described above, it makes it easy to use the Redfish API from a BASH script, or as an easy-to-use interactive CLI -- but WITHOUIT creating a 'new API'.   All (rather most) of the responses from ***redfishtool*** are Redfish-defined responses.  The properties and resources are defined in the redfish spec.   ***redfishtool*** is just a tool to access the Redfish API-not a new interface itself.
    * The exception is that a 'list' operation was added for all collections to display the key properties for each of the members--rather than just the URIs to the members.


## Installation
`redfishtool` can be installed via [pip](https://pip.pypa.io/en/stable/).

```
pip install redfishtool
```


## Requirements

***redfishtool*** is based on Python 3 and the client system is required to have the Python framework installed before the tool can be installed and executed on the system.

If cloning the tool from Github, as opposed to performing the installation via pip, the following packages are required to be installed and accessible from the python environment:

* requests - [https://github.com/psf/requests]()
* python-dateutil - [https://github.com/dateutil/dateutil]()

You may install the required packages by running:

    pip install -r requirements.txt


## Usage

***python***  ***redfishtool*** [ ***Options*** ] [ ***SubCommands*** ] [ ***Operation*** ] [ ***OtherArgs*** ]

* ***redfishtool*** is a python3.4+ program.  It uses the python3 "requests" lib for sending HTTP requests, and a host of other standard libs in python3.4+
* The ***redfishtool*** option/optarg parsing strictly follows the well established linux/GNU getopt syntax where arguments and options can be specified in any order, and both short (eg -r <host>) or long (--rhost=<host>) syntax is supported.
* ***options*** are used to pass usernames, passwords, Host:port, authentication options, verbose/status flags, and also to specify how to search to find specific collection members (-I <Id>, -a (all), -M <prop>:<val> ).
* ***subCommands*** indicate the general area of the API (following ipmitool convention), and align with Redfish navigation property names like "Chassis", "Systems", "AccountService", etc.
* ***Operations*** are specify an action or operation you want to perform like S`ystems setBootOverride` ..., or `Systems reset`.
* ***OtherArgs*** are any other arguments after the Operation that are sometimes required--like:  `Systems <setBootOverride> <enableValue>` <targetValue>`

### Common OPTIONS:

    -V,          --version           -- show redfishtool version, and exit
    -h,          --help              -- show Usage, Options, and list of subCommands, and exit
    -v,          --verbose           -- verbose level, can repeat up to 5 times for more verbose output
                               -v(header), -vv(+addl info), -vvv(Request trace), -vvvv(+subCmd dbg), -vvvvv(max dbg)
    -s,          --status            -- status level, can repeat up to 5 times for more status output
                                -s(http_status), 
                                -ss(+r.url, +r.elapsed executionTime ), 
                                -sss(+request hdrs,data,authType, +response status_code, +response executionTime, 
                                     +login auth token/sessId/sessUri)
                                -ssss(+response headers), -sssss(+response data
    -u <user>,   --user=<usernm>     -- username used for remote redfish authentication
    -p <passwd>, --password=<passwd> -- password used for remote redfish authentication
    -r <rhost>,  --rhost=<rhost>     -- remote redfish service hostname or IP:port
    -t <token>,  --token=<token>     -- redfish auth session token-for sessions across multiple calls
    -q,          --quiet             -- quiet mode--suppress error, warning, and diagnostic messages
    -c <cfgFile>,--config=<cfgFile>  -- read options (including credentials) from file <cfgFile>
    -T <timeout>,--Timeout=<timeout> -- timeout in seconds for each http request.  Default=10

    -P <property>, --Prop=<property> -- return only the specified property. Applies only to all "get" operations
    -E, --Entries                    -- Fetch the Logs entries. Applies to Logs sub-command of Systems, Chassis and Managers


###### Options used by "raw" subcommand:

    -d <data>    --data=<data>       -- the http request "data" to send on PATCH,POST,or PUT requests


###### Options to specify top-level collection members: eg: `Systems -I <sysId>`
For `Systems`, `Managers`, and `Chassis` commands that require specifying a top-level collection member, if no option is specified the default is `--One`.

    -I <Id>, --Id=<Id>               -- Use <Id> to specify the collection member
    -M <prop>:<val> --Match=<prop>:<val>-- Use <prop>=<val> search to find the collection member
    -F,  --First                     -- Use the 1st link returned in the collection or 1st "matching" link if used with -M
    -1,  --One                       -- Use the single link returned in the collection. Return error if more than one member exists
    -a,  --all                       -- Returns all members if the operation is a Get on a top-level collection like Systems
    -L <Link>,  --Link=<Link>        -- Use <Link> (eg /redfish/v1/Systems/1) to reference the collection member. 
                                     --   If <Link> is not one of the links in the collection, and error is returned.


###### Options to specify 2nd-level collection members: eg: `Systems -I<sysId> Processors -i<procId>`

    -i <id>, --id=<id>               -- use <id> to specify the 2nd-level collection member
    -m <prop>:<val> --match=<prop>:val>--use <prop>=<val> search of 2nd-level collection to specify member
    -l <link>  --link=<link>         -- Use <link> (eg /redfish/v1/SYstems/1/Processors/1) to reference a 2nd level resource
                                     --   A -I|M|F|1|L option is still required to specify the link to the top-lvl collection
    -a,  --all                       -- Returns all members of the 2nd level collection if the operation is a Get on the 
                                     --   2nd level collection (eg Processors). -I|M|F|1|L still specifies the top-lvl collection.


###### Additional OPTIONS:

    -W <num>:<connTimeout>,          -- Send up to <num> {GET /redfish} requests with <connTimeout> TCP connection timeout
          --Wait=<num>:<ConnTimeout> --   before sending subcommand to rhost.  Default is -W 1:3
    -A <Authn>,   --Auth <Authn>     -- Authentication type to use:  Authn={None|Basic|Session}  Default is Basic
    -S <Secure>,  --Secure=<Secure>  -- When to use https: (Note: doesn't stop rhost from redirect http to https)
                                        <Secure>={Always | IfSendingCredentials | IfLoginOrAuthenticatedApi(default) }
    -R <ver>,  --RedfishVersion=<ver>-- The Major Redfish Protocol version to use: ver={v1(dflt), v<n>, Latest}
    -C         --CheckRedfishVersion -- tells Redfishtool to execute GET /redfish to verify that the rhost supports
                                        the specified redfish protocol version before executing a sub-command. 
                                        The -C flag is auto-set if the -R Latest or -W ... options are selected
    -N,        --NonBlocking         -- Do not wait for asynchronous requests to complete.
    -n,        --no-proxy            -- Ignore any PROXY environment variables.
    -H <hdrs>, --Headers=<hdrs>      -- Specify the request header list--overrides defaults. Format "{ A:B, C:D...}" 
    -D <flag>,  --Debug=<flag>       -- Flag for dev debug. <flag> is a 32-bit uint: 0x<hex> or <dec> format


### Subcommands:

    hello                 -- redfishtool hello world subcommand for dev testing
    about                 -- display version and other information about this version of redfishtool
    versions              -- get redfishProtocol versions supported by rhost: GET ^/redfish
    root   |  serviceRoot -- get serviceRoot resource: GET ^/redfish/v1/
    Systems               -- operations on Computer Systems in the /Systems collection 
    Chassis               -- operations on Chassis in the /Chassis collection
    Managers              -- operations on Managers in the /Managers collection
    AccountService        -- operations on AccountService including user administration
    SessionService        -- operations on SessionService including Session login/logout
    odata                 -- get the Odata Service document: GET ^/redfish/v1/odata
    metadata              -- get the CSDL metadata document: GET ^/redfish/v1/$metadata
    raw                   -- subcommand to execute raw http methods(GET,PATCH,POST...) and URIs

For Subcommand usage, including subcommand Operations and OtherArgs, execute:

    redfishtool <SubCommand> -h  -- usage and options for specific subCommand

### Subcommand Operations and Addl Args

###### Systems Operations

    python redfishtool.py -r <rhost> -u <username> -p <password> Systems -h
    Usage:
     redfishtool [OPTNS]  Systems  <operation> [<args>]  -- perform <operation> on the system specified
    <operations>:
       [collection]              -- get the main Systems collection. (Default operation if no member specified)
       [get]                     -- get the computerSystem object. (Default operation if collection member specified)
       list                      -- list information about the Systems collection members("Id", URI, and AssetTag)
       patch {A: B,C: D,...}     -- patch the json-formatted {prop: value...} data to the object
       reset <resetType>         -- reset a system.  <resetType>= On,  GracefulShutdown, GracefulRestart, 
                                     ForceRestart, ForceOff, ForceOn, Nmi, PushPowerButton, PowerCycle
       setAssetTag <assetTag>    -- set the system's asset tag 
       setIndicatorLed  <state>  -- set the indicator LED.  <state>=redfish defined values: Off, Lit, Blinking
       setBootOverride <enabledVal> <targetVal> -- set Boot Override properties. <enabledVal>=Disabled|Once|Continuous
                                 -- <targetVal> =None|Pxe|Floppy|Cd|Usb|Hdd|BiosSetup|Utilities|Diags|UefiTarget|
       Processors [list]         -- get the "Processors" collection, or list "id" and URI of members.
        Processors [IDOPTN]        --  get the  member specified by IDOPTN: -i<id>, -m<prop>:<val>, -l<link>, -a #all
       Inventory [list]          -- get the "Inventory" collection, or list "id" and URI of members.

       EthernetInterfaces [list] -- get the "EthernetInterfaces" collection, or list "id" and URI of members.
        EthernetInterfaces [IDOPTN]--  get the member specified by IDOPTN: -i<id>, -m<prop>:<val>, -l<link>, -a #all

       SimpleStorage [list]      -- get the ComputerSystem "SimpleStorage" collection, or list "id" and URI of members.
        SimpleStorage [IDOPTN]     --  get the member specified by IDOPTN: -i<id>, -m<prop>:<val>, -l<link>, -a #all

       Logs [list]               -- get the ComputerSystem "LogServices" collection , or list "id" and URI of members.
        Logs [IDOPTN]              --  get the member specified by IDOPTN: -i<id>, -m<prop>:<val>, -l<link>, -a #all
       clearLog   <id>           -- clears the log defined by <id>
       examples                  -- example commands with syntax
       hello                     -- Systems hello -- debug command


###### Chassis Operations

    python redfishtool.py -r <rhost> -u <username> -p <password> Chassis -h
    Usage:
     redfishtool [OPTNS]  Chassis  <operation> [<args>]  -- perform <operation> on the Chassis specified 
    <operations>:
       [collection]              -- get the main Chassis collection. (Default operation if no member specified)
       [get]                     -- get the Chassis object. (Default operation if collection member specified)
       list                      -- list information about the Chassis collection members("Id", URI, and AssetTag)
       patch {A: B,C: D,...}     -- patch the json-formatted {prop: value...} data to the object
       setAssetTag <assetTag>    -- set the Chassis's asset tag 
       setIndicatorLed  <state>  -- set the indicator LED.  <state>=redfish defined values: Off, Lit, Blinking
       Power                     -- get the full Power resource under a specified Chassis instance.
       Thermal                   -- get the full Thermal resource under a specified Chassis instance.
       Sensors                   -- get all sensors

       getPowerReading [-i<indx>] [consumed]-- get powerControl resource w/ power capacity, PowerConsumed, and power limits
                                    if "consumed" keyword is added, then only current usage of powerControl[indx] is returned
                                    <indx> is the powerControl array index. default is 0.  normally, 0 is the only entry
       setPowerLimit [-i<indx>] <limit> [<exception> [<correctionTime>]] -- set powerLimit control properties
                                 <limit>=null disables power limiting. <indx> is the powerControl array indx (dflt=0)

       Logs [list]               -- get the Chassis "LogServices" collection , or list "id" and URI of members.
        Logs [IDOPTN]              --  get the member specified by IDOPTN: -i<id>, -m<prop>:<val>, -l<link>, -a #all
       clearLog   <id>           -- clears the log defined by <id>
       examples                  -- example commands with syntax
       hello                     -- Chassis hello -- debug command


###### Managers Operations

    python redfishtool.py -r <rhost> -u <username> -p <password> Managers -h
    Usage:
     redfishtool [OPTNS]  Managers  <operation> [<args>]  -- perform <operation> on the Managers specified 
    <operations>:
       [collection]              -- get the main Managers collection. (Default operation if no member specified)
       [get]                     -- get the specified Manager object. (Default operation if collection member specified)
       list                      -- list information about the Managers collection members("Id", URI, and UUID)
       patch {A: B,C: D,...}     -- patch the json-formatted {prop: value...} data to the object
       reset <resetType>         -- reset a Manager.  <resetType>= On,  GracefulShutdown, GracefulRestart, 
                                     ForceRestart, ForceOff, ForceOn, Nmi, PushPowerButton, PowerCycle
       setDateTime <dateTimeString>--set the date and time
       setTimeOffset offset=<offsetString>  --set the time offset w/o changing time setting
                                              <offsetString> is of form "[+/-]mm:ss". Ex: "-10:01" 
       NetworkProtocol           -- get the "NetworkProtocol" resource under the specified manager.
       setIpAddress [-i<indx>]... -- set the Manager IP address -NOT IMPLEMENTED YET

       EthernetInterfaces [list] -- get the managers "EthernetInterfaces" collection, or list "id",URI, Name of members.
        EthernetInterfaces [IDOPTN]--  get the member specified by IDOPTN: -i<id>, -m<prop>:<val>, -a #all

       SerialInterfaces [list]   -- get the managers "SerialInterfaces" collection, or list "id",URI, Name of members.
        SerialInterfaces [IDOPTN]  --  get the member specified by IDOPTN: -i<id>, -m<prop>:<val>, -l<link>, -a #all

       Logs [list]               -- get the Managers "LogServices" collection , or list "id",URI, Name of members.
        Logs [IDOPTN]              --  get the member specified by IDOPTN: -i<id>, -m<prop>:<val>, -l<link>, -a #all
       clearLog   <id>           -- clears the log defined by <id>
       examples                  -- example commands with syntax
       hello                     -- Systems hello -- debug command


###### AccountService Operations

    python redfishtool.py -r <rhost> -u <username> -p <password> AccountService -h
    Usage:
     redfishtool [OPTNS]  AccountService  <operation> [<args>]  -- perform <operation> on the AccountService  
    <operations>:
       [get]                     -- get the AccountService object. 
       patch {A: B,C: D,...}     -- patch the AccountService w/ json-formatted {prop: value...} 
       Accounts [list]           -- get the "Accounts" collection, or list "Id", username, and Url 
         Accounts [IDOPTN]       --   get the member specified by IDOPTN: -i<Id>, -m<prop>:<val>, -l<link>, -a #all
       Roles [list]              -- get the "Roles" collection, or list "Id", IsPredefined, and Url 
         Roles [IDOPTN]          --   get the member specified by IDOPTN: -i<Id>, -m<prop>:<val>, -l<link>, -a #all
       adduser <usernm> <passwd> [<roleId>] -- add a new user to the Accounts collection
                                 -- <roleId>:{Administrator | Operator | ReadOnlyUser | <a custom roleId}, dflt=Operator
       deleteuser <usernm>       -- delete an existing user from Accouts collection
       setpassword  <usernm> <passwd>  -- set (change) the password of an existing user account
       useradmin <userName> [enable|disable|unlock|[setRoleId <roleId>]] -- enable|disable|unlock.. a user account
       setusername <id> <userName> -- set UserName for account with given Id
       examples                  -- example commands with syntax
       hello                     -- AccountService hello -- debug command


###### SessionService Operations

    python redfishtool.py -r <rhost> -u <username> -p <password> SessionService -h
    Usage:
     redfishtool [OPTNS]  SessionService  <operation> [<args>]  -- perform <operation> on the SessionService  
    <operations>:
       [get]                     -- get the sessionService object. 
       patch {A: B,C: D,...}     -- patch the sessionService w/ json-formatted {prop: value...} 
       setSessionTimeout <timeout> -- patches the SessionTimeout property w/ etag support 
       Sessions [list]           -- get the "Sessions" collection, or list "Id", username, and Url 
         Sessions [IDOPTN]       --   get the member specified by IDOPTN: -i<Id>, -m<prop>:<val>, -l<link>, -a #all
       login                     -- sessionLogin.  post to Sessions collection to create a session
                                     the user is -u<user>, password is -p<password>
       logout                    -- logout or delete the session by identified by -i<SessionId> or -l<link>
                                     where <link> is the session path returned in Location from login
       examples                  -- example commands with syntax
       hello                     -- Systems hello -- debug command


###### raw Operations

    python redfishtool.py -r <rhost> -u <username> -p <password> raw -h
    Usage:
     redfishtool [OPTNS] raw <method> <path> 

     redfishtool raw -h        # for help
     redfishtool raw examples  #for example commands

    <method> is one of:  GET, PATCH, POST, DELETE, HEAD, PUT
    <path> is full URI path to a redfish resource--the full path following <ipaddr:port>, starting with forward slash /

     Common OPTNS:
     -u <user>,   --user=<usernm>     -- username used for remote redfish authentication
     -p <passwd>, --password=<passwd> -- password used for remote redfish authentication
     -t <token>,  --token=<token>    - redfish auth session token-for sessions across multiple calls

     -r <rhost>,  --rhost=<rhost>     -- remote redfish service hostname or IP:port
     -X <method>  --request=<method>  -- the http method to use. <method>={GET,PATCH,POST,DELETE,HEAD,PUT}. Default=GET
     -d <data>    --data=<data>       -- the http request "data" to send on PATCH,POST,or PUT requests
     -H <hdrs>, --Headers=<hdrs>      -- Specify the request header list--overrides defaults. Format "{ A:B, C:D...}" 
     -S <Secure>,  --Secure=<Secure>  -- When to use https: (Note: doesn't stop rhost from redirect http to https)
    <operations / methods>:
       GET             -- HTTP GET method
       PATCH           -- HTTP PATCH method
       POST            -- HTTP POST method
       DELETE          -- HTTP DELETE method
       HEAD            -- HTTP HEAD method
       PUT             -- HTTP PUT method
     examples        -- example raw commands with syntax
     hello           -- raw hello -- debug command


# Example Usage

### System subcommand Examples

    $ python redfishtool.py -r <ip> -u <username> -p <password> Systems examples
     # Shows the Systems Collection
     redfishtool -r <ip> -u <username> -p <password> Systems

     # Lists Id, Uri, AssetTag for all systems
     redfishtool -r <ip> -u <username> -p <password> Systems list

     # Gets the system with Id=<d>
     redfishtool -r <ip> -u <username> -p <password> Systems -I <id>

     # Gets the system with AssetTag=12345
     redfishtool -r <ip> -u <username> -p <password> Systems -M AssetTag:12345

     # Gets the system at URI=<systemUrl>
     redfishtool -r <ip> -u <username> -p <password> Systems -L <systemUrl>

     # Gets the first system returned (for debug)
     redfishtool -r <ip> -u <username> -p <password> Systems -F

     # Gets the first system and verify that there is only one system
     redfishtool -r <ip> -u <username> -p <password> Systems -1

     # Patches the json-formated {prop: value...} data to the specified system
     redfishtool -r <ip> -u <username> -p <password> Systems -I <id> patch {A: B,C: D,...}

     # Patches the json-formated {prop: value...} data to all systems
     redfishtool -r <ip> -u <username> -p <password> Systems --all patch {A: B,C: D,...}

     # Resets a system.  <resetType>=the redfish-defined values: On, Off, gracefulOff...
     redfishtool -r <ip> -u <username> -p <password> Systems -I <id> reset <resetType>

     # Resets all systems.  <resetType>=the redfish-defined values: On, Off, gracefulOff...
     redfishtool -r <ip> -u <username> -p <password> Systems --all reset <resetType>

     # Sets the system's asset tag to <assetTag>
     redfishtool -r <ip> -u <username> -p <password> Systems -I <id> setAssetTag <assetTag>

     # Sets all system's asset tags to <assetTag>
     redfishtool -r <ip> -u <username> -p <password> Systems --all setAssetTag <assetTag>

     # Sets the indicator LED.  <state>=redfish defined values: Off, Lit, Blinking
     redfishtool -r <ip> -u <username> -p <password> Systems -I <id> setIndicatorLed <state>

     # Sets the indicator LED on all systems. <state>=redfish defined values: Off, Lit, Blinking
     redfishtool -r <ip> -u <username> -p <password> Systems --all setIndicatorLed <state>

     # Sets Boot Override properties.  <enabledVal>=Disabled|Once|Continuous
     redfishtool -r <ip> -u <username> -p <password> Systems -I <id> setBootOverride <enabledVal> <targetVal>

     # Sets Boot Override properties on all systems.  <enabledVal>=Disabled|Once|Continuous
     redfishtool -r <ip> -u <username> -p <password> Systems --all setBootOverride <enabledVal> <targetVal>

     # Gets the Processor Collection
     redfishtool -r <ip> -u <username> -p <password> Systems -I <Id> Processors

     # Lists Id, Uri, & Socket for all processors in system w/ Id=<Id>
     redfishtool -r <ip> -u <username> -p <password> Systems -I <Id> Processors list

     # Gets the processor with id=1 in system with Id=<Id>
     redfishtool -r <ip> -u <username> -p <password> Systems -I <Id> Processors -i 1

     # Gets processor with property Socket=CPU_1, on system at url <sysUrl>
     redfishtool -r <ip> -u <username> -p <password> Systems -L <sysUrl> Processors -m Socket:CPU_1

     # Gets log member with Id=SEL from the first System
     redfishtool -r <ip> -u <username> -p <password> Systems -1 Logs -i SEL

     # Gets log entries with Id=SEL from the first System
     redfishtool -r <ip> -u <username> -p <password> Systems -1 Logs -E -i SEL

     # Gets System inventory
     redfishtool -r <ip> -u <username> -p <password> Systems Inventory


### Chassis subcommand Examples

    $ python redfishtool.py -r <ip> -u <username> -p <password> Chassis examples
     # Shows the Chassis Collection
     redfishtool -r <ip> -u <username> -p <password> Chassis

     # Lists Id, Uri, AssetTag for all Chassis
     redfishtool -r <ip> -u <username> -p <password> Chassis list

     # Gets the Chassis with Id=<d>
     redfishtool -r <ip> -u <username> -p <password> Chassis -I <id>

     # Gets the Chassis with AssetTag=12345
     redfishtool -r <ip> -u <username> -p <password> Chassis -M AssetTag:12345

     # Gets the Chassis at URI=<chassisUrl>
     redfishtool -r <ip> -u <username> -p <password> Chassis -L <chassisUrl>

     # Gets the first Chassis returned (for debug)
     redfishtool -r <ip> -u <username> -p <password> Chassis -F

     # Gets the first Chassis and verify that there is only one system
     redfishtool -r <ip> -u <username> -p <password> Chassis -1

     # Patches the json-formated {prop: value...} data to the specified chassis
     redfishtool -r <ip> -u <username> -p <password> Chassis -I <id> patch {A: B,C: D,...}

     # Patches the json-formated {prop: value...} data to all chassis
     redfishtool -r <ip> -u <username> -p <password> Chassis --all patch {A: B,C: D,...}

     # Sets the chassis's asset tag
     redfishtool -r <ip> -u <username> -p <password> Chassis -I <id> setAssetTag <assetTag>

     # Sets all chassis's asset tags
     redfishtool -r <ip> -u <username> -p <password> Chassis --all setAssetTag <assetTag>

     # Sets the indicator LED.  <state>=redfish defined values: Off, Lit, Blinking
     redfishtool -r <ip> -u <username> -p <password> Chassis -I <id> setIndicatorLed <state>

     # Sets the indicator LED on all chassis.  <state>=redfish defined values: Off, Lit, Blinking
     redfishtool -r <ip> -u <username> -p <password> Chassis --all setIndicatorLed <state>

     # Gets the full chassis Power resource
     redfishtool -r <ip> -u <username> -p <password> Chassis -I <Id> Power

     # Gets the full chassis Thermal resource
     redfishtool -r <ip> -u <username> -p <password> Chassis -I <Id> Thermal

     # Gets chassis/Power powerControl[<indx>] resource if optional "consumed" arg, then return only the PowerConsumedWatts prop
     redfishtool -r <ip> -u <username> -p <password> Chassis -I <Id> getPowerReading[-i<indx> [consumed]

     # Sets the power limit
     redfishtool -r <ip> -u <username> -p <password> Chassis -L<Url> setPowerLimit [-i<indx>] <limit> [<exception> [<correctionTime>]]

     # Sets the power limit on all chassis
     redfishtool -r <ip> -u <username> -p <password> Chassis --all setPowerLimit [-i<indx>] <limit> [<exception> [<correctionTime>]]

     # Gets log member with Id=SEL from the first Chassis
     redfishtool -r <ip> -u <username> -p <password> Chassis -1 Logs -i SEL

     # Gets log entries with Id=SEL from the first Chassis
     redfishtool -r <ip> -u <username> -p <password> Chassis -1 Logs -E -i SEL

     # Gets all Sensors
     redfishtool -r <ip> -u <username> -p <password> Chassis Sensors


### Managers subcommand Examples

    $ python redfishtool.py -r <ip> -u <username> -p <password> Managers examples
     # Shows the Managers Collection
     redfishtool -r <ip> -u <username> -p <password>

     # Lists Id, Uri, AssetTag for all Managers
     redfishtool -r <ip> -u <username> -p <password> Managers list

     # Gets the Manager with Id=<d>
     redfishtool -r <ip> -u <username> -p <password> Managers -I <id>

     # Gets the Manager with AssetTag=12345
     redfishtool -r <ip> -u <username> -p <password> Managers -M AssetTag:12345

     # Gets the Manager at URI=<mgrUrl>
     redfishtool -r <ip> -u <username> -p <password> Managers -L <mgrUrl>

     # Gets the first Manager returned (for debug)
     redfishtool -r <ip> -u <username> -p <password> Managers -F

     # Gets the first Manager and verify that there is only one Manager
     redfishtool -r <ip> -u <username> -p <password> Managers -1

     # Patches the json-formated {prop: value...} data to the object
     redfishtool -r <ip> -u <username> -p <password> Managers -I <id> patch {A: B,C: D,...}

     # Resets a Manager.  <resetType>=the redfish-defined values: On, Off, gracefulOff...
     redfishtool -r <ip> -u <username> -p <password> Managers -I <id> reset <resetType>

     # Gets the NetworkProtocol resource under the specified manager
     redfishtool -r <ip> -u <username> -p <password> Managers -I <Id> NetworkProtocol

     # Lists Id, Uri, and Name for all of the NICs for Manager w/ Id=<Id>
     redfishtool -r <ip> -u <username> -p <password> Managers -I <Id> EthernetInterfaces list

     # Gets the NIC with id=1 in manager with Id=<Id>
     redfishtool -r <ip> -u <username> -p <password> Managers -I <Id> EthernetInterfaces -i 1

     # Gets the NIC with MAC AA:BB:CC:DD:EE:FF for manager at url <Url>
     redfishtool -r <ip> -u <username> -p <password> Managers -L <Url> EthernetInterfaces -m MACAddress:AA:BB:CC:DD:EE:FF

     # Gets log member with Id=SEL from the first Manager
     redfishtool -r <ip> -u <username> -p <password> Managers -1 Logs -i SEL

     # Gets log entries with Id=SEL from the first Manager
     redfishtool -r <ip> -u <username> -p <password> Managers -1 Logs -E -i SEL


### AccountService subcommand Examples

    $ python redfishtool.py -r <ip> -u <username> -p <password> AccountService examples
     # Gets the AccountService
     redfishtool -r <ip> -u <username> -p <password> AccountService

     # Sets the failed login lockout threshold
     redfishtool -r <ip> -u <username> -p <password> AccountService patch { "AccountLockoutThreshold": 5 } ]

     # Gets the Accounts collection
     redfishtool -r <ip> -u <username> -p <password> AccountService Accounts

     # List Accounts to get Id, username, url for each account
     redfishtool -r <ip> -u <username> -p <password> AccountService Accounts list

     # Gets the Accounts member with username: john
     redfishtool -r <ip> -u <username> -p <password> AccountService Accounts -m UserName:john

     # Lists the Roles collection to get RoleId, IsPredefined, & url for each role
     redfishtool -r <ip> -u <username> -p <password> AccountService Roles list

     # Gets the Roles member with RoleId=Admin
     redfishtool -r <ip> -u <username> -p <password> AccountService Roles -i Admin

     # Adds the new user (john) w/ passwd "12345" and role: Admin
     redfishtool -r <ip> -u <username> -p <password> AccountService adduser john 12345 Admin

     # Deletes the account with the username "john"
     redfishtool -r <ip> -u <username> -p <password> AccountService deleteuser john

     # Disables the account with the username "john"
     redfishtool -r <ip> -u <username> -p <password> AccountService useradmin john disable

     # Unlocks the account with the username "john"
     redfishtool -r <ip> -u <username> -p <password> AccountService useradmin john unlock

     # Sets the username for account with id=3 to "alice"
     redfishtool -r <ip> -u <username> -p <password> AccountService setusername 3 alice


### SessionService subcommand Examples

    $ python redfishtool.py -r <ip> -u <username> -p <password> SessionService examples
     # Gets the sessionService
     redfishtool -r <ip> -u <username> -p <password> SessionService

     # Sets the session timeout property
     redfishtool -r <ip> -u <username> -p <password> SessionService setSessionTimeout <timeout>

     # Gets Sessions collection
     redfishtool -r <ip> -u <username> -p <password> SessionService Sessions

     # Gets the session at URI=<sessUrl>
     redfishtool -r <ip> -u <username> -p <password> SessionService Sessions -l <sessUrl>

     # Gets the session with session Id <sessId>
     redfishtool -r <ip> -u <username> -p <password> SessionService Sessions -i <sessId>

     # Patches the json-formated {prop: value...} data to the sessionService object
     redfishtool -r <ip> -u <username> -p <password> SessionService patch {A: B,C: D,...}

     # Login (create session)
     redfishtool -r <ip> -u <username> -p <password> SessionService login -u <user> -p <password>

     # Logout (delete session <sessId>)
     redfishtool -r <ip> -u <username> -p <password> SessionService logout -i <sessionId>


## Running in Windows

In order for executables to resolve if using Windows, ensure both the "Python" and "Scripts" folder are included in the PATH environment variable.  For example, if Python is installed to "C:\Python", the PATH environment variable should include "C:\Python" and "C:\Python\scripts".


## Known Issues, and ToDo Enhancements

1. modifications to make PATCH commands work better with Windows cmd shell quoting 
2. support clearlog
3. add additional APIs that have been added to Redfish after 1.0---this version supports only 1.0 APIs
4. add custom role create and delete


## Release Process

1. Go to the "Actions" page
2. Select the "Release and Publish" workflow
3. Click "Run workflow"
4. Fill out the form
5. Click "Run workflow"
