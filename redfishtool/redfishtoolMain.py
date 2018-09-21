# Copyright Notice:
# Copyright 2016 DMTF. All rights reserved.
# License: BSD 3-Clause License. For full text see link: https://github.com/DMTF/Redfishtool/blob/master/LICENSE.md

# redfishtool:  redfishtool.py  Main
#
# contains:
#  - functions called for usage:
#     -- displayUsage, displayOptions, listSubcommands, displayHelp
#  - Main routine, with argc/argv option parsing, and valid argument/option checking
#    after parsing options, runs cmd with runSubCmd function, outputs result, cleansup sessions created
#  - runSubCmd -- Main subcommand command table and subcommand execution
#  - hello subcommand for testing
#  - help  subcommand
#  - about subcommand for info about this version of redfishtool
#
import sys
import getopt
import re
import json
from .redfishtoolTransport   import RfTransport
from .ServiceRoot import RfServiceRoot
from .Systems import RfSystemsMain
from .Chassis import RfChassisMain
from .Managers import RfManagersMain
from .SessionService import RfSessionServiceMain
from .AccountService import RfAccountServiceMain
from .raw import RfRawMain

def displayUsage(rft,*argv,**kwargs):
        rft.printErr("  Usage:",noprog=True)
        rft.printErr("   {} [OPTIONS]  <SubCommand> <operation> [<args>]... ",prepend="  ")
        rft.printErr("   {} [OPTIONS]  hmraw  <method> <hmUrl> [<data>]",     prepend="  ")
              
def displayOptions(rft):
        print("")
        print("  Common OPTIONS:")
        print("   -V,          --version           -- show {} version, and exit".format(rft.program))
        print("   -h,          --help              -- show Usage, Options, and list of subCommands, and exit".format(rft.program))
        print("   -v,          --verbose           -- verbose level, can repeat up to 5 times for more verbose output")
        print("                              -v(header), -vv(+addl info), -vvv(Request trace), -vvvv(+subCmd dbg), -vvvvv(max dbg)")
        print("   -s,          --status            -- status level, can repeat up to 5 times for more status output")
        print("                               -s(http_status), ")
        print("                               -ss(+r.url, +r.elapsed executionTime ), ")
        print("                               -sss(+request hdrs,data,authType, +response status_code, +response executionTime, ")
        print("                                    +login auth token/sessId/sessUri)")
        print("                               -ssss(+response headers), -sssss(+response data")
        print("   -u <user>,   --user=<usernm>     -- username used for remote redfish authentication")
        print("   -p <passwd>, --password=<passwd> -- password used for remote redfish authentication")
        print("   -r <rhost>,  --rhost=<rhost>     -- remote redfish service hostname or IP:port")
        print("   -t <token>,  --token=<token>     -- redfish auth session token-for sessions across multiple calls")
        print("   -q,          --quiet             -- quiet mode--suppress error, warning, and diagnostic messages")
        print("   -c <cfgFile>,--config=<cfgFile>  -- read options (including credentials) from file <cfgFile>")
        print("   -T <timeout>,--Timeout=<timeout> -- timeout in seconds for each http request.  Default=10")
        print("")
        print("   -P <property>, --Prop=<property> -- return only the specified property. Applies only to all \"get\" operations")
        print("   -E, --Entries                    -- Fetch the Logs entries. Applies to Logs sub-command of Systems, Chassis and Managers")
        print("")
        print("  Options used by \"raw\" subcommand:")
        print("   -d <data>    --data=<data>       -- the http request \"data\" to send on PATCH,POST,or PUT requests")
        print("")
        print("  Options to specify top-level collection members: eg: Systems -I <sysId>")
        print("   -I <Id>, --Id=<Id>               -- Use <Id> to specify the collection member")
        print("   -M <prop>:<val> --Match=<prop>:<val>-- Use <prop>=<val> search to find the collection member")
        print("   -F,  --First                     -- Use the 1st link returned in the collection or 1st \"matching\" link if used with -M")
        print("   -1,  --One                       -- Use the single link returned in the collection. Return error if more than one member exists")
        print("   -a,  --all                       -- Returns all members if the operation is a Get on a top-level collection like Systems")
        print("   -L <Link>,  --Link=<Link>        -- Use <Link> (eg /redfish/v1/Systems/1) to reference the collection member. ")
        print("                                    --   If <Link> is not one of the links in the collection, and error is returned.")
        print("  Options to specify 2nd-level collection members: eg: Systems -I<sysId> Processors -i<procId>")
        print("   -i <id>, --id=<id>               -- use <id> to specify the 2nd-level collection member")
        print("   -m <prop>:<val> --match=<prop>:val>--use <prop>=<val> search of 2nd-level collection to specify member")
        print("   -l <link>  --link=<link>         -- Use <link> (eg /redfish/v1/SYstems/1/Processors/1) to reference a 2nd level resource")
        print("                                    --   A -I|M|F|1|L option is still required to specify the link to the top-lvl collection")
        print("   -a,  --all                       -- Returns all members of the 2nd level collection if the operation is a Get on the ") 
        print("                                    --   2nd level collection (eg Processors). -I|M|F|1|L still specifies the top-lvl collection.")
        print("")
        print("  Additional OPTIONS:")
        print("   -W <num>:<connTimeout>,          -- Send up to <num> {GET /redfish} requests with <connTimeout> TCP connection timeout")
        print("         --Wait=<num>:<ConnTimeout> --   before sending subcommand to rhost.  Default is -W 1:3")
        print("   -A <Authn>,   --Auth <Authn>     -- Authentication type to use:  Authn={None|Basic|Session}  Default is Basic")
        print("   -S <Secure>,  --Secure=<Secure>  -- When to use https: (Note: doesn't stop rhost from redirect http to https)")
        print("                                       <Secure>={Always | IfSendingCredentials | IfLoginOrAuthenticatedApi(default) }")
        print("   -R <ver>,  --RedfishVersion=<ver>-- The Major Redfish Protocol version to use: ver={v1(dflt), v<n>, Latest}")
        print("   -C         --CheckRedfishVersion -- tells Redfishtool to execute GET /redfish to verify that the rhost supports")
        print("                                       the specified redfish protocol version before executing a sub-command. ")
        print("                                       The -C flag is auto-set if the -R Latest or -W ... options are selected")
        print("   -H <hdrs>, --Headers=<hdrs>      -- Specify the request header list--overrides defaults. Format \"{ A:B, C:D...}\" ")
        print("   -D <flag>,  --Debug=<flag>       -- Flag for dev debug. <flag> is a 32-bit uint: 0x<hex> or <dec> format")
        print("")
        
def listSubcommands(rft):
        # print a list of Main subcommands in order to show them in lc subcommand
        print("  Subcommands:")
        print("     hello                 -- redfishtool hello world subcommand for dev testing")
        print("     about                 -- display version and other information about this version of {}".format(rft.program))
        print("     versions              -- get redfishProtocol versions supported by rhost: GET ^/redfish")
        print("     root   |  serviceRoot -- get serviceRoot resouce: GET ^/redfish/v1/")
        print("     Systems               -- operations on Computer Systems in the /Systems collection ")
        print("     Chassis               -- operations on Chassis in the /Chassis collection")
        print("     Managers              -- operations on Managers in the /Managers collection")
        print("     AccountService        -- operations on AccountService including user administration")
        print("     SessionService        -- operations on SessionService including Session login/logout")
        print("     odata                 -- get the Odata Service document: GET ^/redfish/v1/odata")
        print("     metadata              -- get the CSDL metadata document: GET ^/redfish/v1/$metadata")
        print("     raw                   -- subcommand to execute raw http methods(GET,PATCH,POST...) and URIs")

        return(0)

def displayHelp(rft):
        displayUsage(rft,file=sys.stdout)
        displayOptions(rft)
        listSubcommands(rft)
        print("")
        print("  For Subcommand usage, options, operations, help:")
        print("     {} <SubCommand> -h  -- usage and options for specific subCommand".format(rft.program))
        print("")

def main(argv):
    #instantiate transport object which initializes default options
    rft=RfTransport()

    try:
        opts, args = getopt.gnu_getopt(argv[1:],"Vhvsqu:p:r:t:c:T:P:d:EI:M:F1L:i:m:l:aW:A:S:R:H:D:C",
                        ["Version", "help", "verbose", "status", "quiet", 
                         "user=", "password=", "rhost=", "token=", "config=", "Timeout=",
                         "Prop=", "data=", "Entries", "Id=", "Match=", "First", "One", "Link=",
                         "id=", "match=", "link", "all",
                         "Wait=", "Auth=","Secure=", "RedfishVersion=", "Headers=", "Debug=",
                         "CheckRedfishVersion"  ])
    except getopt.GetoptError:
        rft.printErr("Error parsing options")
        displayUsage(rft)
        sys.exit(1)
        
    for opt, arg in opts:
        if opt in ("-h", "--help"):
            rft.help=True
        elif opt in ("-V", "--Version"):
            print("{} Version: {}".format(rft.program, rft.version))
            sys.exit(0)
        elif opt in ("-v", "--verbose"):
            rft.verbose = min((rft.verbose+1), 5)
        elif opt in ("-s", "--status"):
            rft.status = min((rft.status+1), 5)
        elif opt in ("-q", "--quiet"):
            rft.quiet=True
        elif opt in ("-u", "--user"):
            rft.user=arg
        elif opt in ("-p", "--password"):
            rft.password=arg
        elif opt in ("-r", "--rhost"):
            rft.rhost=arg
        elif opt in ("-t", "--token"):          #Redfish Session authentication token
            rft.token=arg
            rft.authToken=rft.token
        elif opt in ("-c", "--config"):         #read additional options from a file
            rft.configFile=arg
        elif opt in ("-T", "--Timeout"):        #Specify http timeout in  seconds
            timePattern="^([1-9][0-9]*)$"
            timeMatch=re.search(timePattern,arg)
            if( timeMatch ):
                rft.timeout=int(arg)
            else:
                rft.printErr("Invalid -Timeout value: {}".format(arg))
                rft.printErr("     Expect: -T <timeout> where <timeout> is a decimal int",noprog=True)
                sys.exit(1)                
        # options that reference a specific property for Get operations
        elif opt in ("-P", "--Prop"):       
            rft.prop=arg
            rft.gotPropOptn=True
        # options used by raw subcommand to specify http method (-X, --request) and request data (-d, --data)
        elif opt in ("-d", "--data"):
            rft.requestData=arg
        # options related to the Logs sub-command of Systems, Chassis and Managers
        elif opt in ("-E", "--Entries"):
            rft.gotEntriesOptn = True
        # options to find the Id or member of a collection in a subcommand
        elif opt in ("-I", "--Id"):
            rft.Id=arg
            rft.gotIdOptn=True
            rft.IdOptnCount+=1
        elif opt in ("-M", "--Match"):  
            # arg is of the form: "<prop>:<value>"
            pair = arg.split(':', 1)
            if len(pair) == 2:
                rft.matchProp = pair[0]
                rft.matchValue = pair[1]
                rft.IdOptnCount += 1
                rft.gotMatchOptn = True
            else:
                rft.printErr("Invalid --Match= option format: {}".format(arg))
                rft.printErr("     Expect --Match=<prop>:<value> Ex -M AssetTag:5555, -Match=AssetTag:5555",noprog=True)
                sys.exit(1)
        elif opt in ("-F", "--First"):        
            rft.firstOptn=True
            rft.IdOptnCount+=1
        elif opt in ("-1", "--One"):
            rft.oneOptn=True
            rft.IdOptnCount+=1
        elif opt in ("-L", "--Link"):       
            rft.Link=arg
            rft.gotIdOptn=True
            rft.IdOptnCount+=1
        elif opt in ("-i", "--id"):
            rft.IdLevel2=arg
            rft.gotIdLevel2Optn=True
            rft.IdLevel2OptnCount+=1
        elif opt in ("-m", "--match"):
            # arg is of the form: "<prop>:<value>"
            pair = arg.split(':', 1)
            if len(pair) == 2:
                rft.matchLevel2Prop = pair[0]
                rft.matchLevel2Value = pair[1]
                rft.IdLevel2OptnCount += 1
                rft.gotMatchLevel2Optn = True
            else:
                rft.printErr("Invalid level2 --match= option format: {}".format(arg))
                rft.printErr("     Expect --match=<prop>:<value> Ex -m ProcessorType:CPU, -match=ProcessorType:CPU",noprog=True)
                sys.exit(1)
        elif opt in ("-l", "--link"):       
            rft.linkLevel2=arg
            rft.gotIdLevel2Optn=True
            rft.IdLevel2OptnCount+=1
        elif opt in ("-a", "--all"):        
            rft.allOptn=True        # additional options
            rft.IdLevel2OptnCount+=1
        elif opt in ("-W", "--Wait"):           #specify how long to ping rhost before sending http requests 0=no ping
            # arg is of the form "<num>:<time>
            rft.checkProtocolVer=True           # if -W ..., set flag to force running GET /redfish first
            waitPattern="^([1-9][0-9]*):([1-9][0-9]*)$"
            waitMatch=re.search(waitPattern,arg)
            if( waitMatch ):
                rft.waitNum=int(waitMatch.group(1))
                rft.waitTime=int(waitMatch.group(2))
                print("num: {},  time: {}".format(rft.waitNum, rft.waitTime))
            else:
                rft.printErr("Invalid --Wait= option format: {}".format(arg))
                rft.printErr("     Expect --Wait=<num>:<time>  where num and time are decimals. Ex -W 10:5",noprog=True)
                sys.exit(1)
        elif opt in ("-A", "--Auth"):           # specify authentication type
            rft.auth=arg
            if not rft.auth in rft.authValidValues:
                rft.printErr("Invalid --Auth option: {}".format(rft.auth))
                rft.printErr("   Valid values: {}".format(rft.authValidValues),noprog=True)
                sys.exit(1)
        elif opt in ("-S", "--Secure"):         #Specify when to use HTTPS
            rft.secure=arg
            if not rft.secure in rft.secureValidValues:
                rft.printErr("Invalid --Secure option: {}".format(rft.secure))
                rft.printErr("     Valid values: {}".format(rft.secureValidValues),noprog=True)
                sys.exit(1)
        elif opt in ("-R", "--RedfishVersion"):     #specify redfish protocol version to use
            rft.protocolVer=arg
            if(rft.protocolVer=="Latest"):
                rft.checkProtocolVer=True           # if -R Latest, set flag to force running GET /redfish first
        elif opt in ("-H", "--Headers"):     #specify request headers -- overrides defaults
            try:
                rft.headers=json.loads(arg)
            except ValueError:
                rft.printErr("Invalid -H arg: invalid Json data format: {}".format(arg))
                sys.exit(1)
        elif opt in ("-D", "--Debug"):  # --Debug=0x3334   or --Debug=233  regex:(^(0[xX]([0-9a-fA-F]){1,8}$))|(^0$)|(^([1-9][0-9]*)$)
            dbgPattern="(^(0[xX]([0-9a-fA-F]){1,8}$))|(^0$)|(^([1-9][0-9]*)$)"   # --Flag=0x<hex> or <decimal>:  0x3334 or 33...
            dbgMatch=re.search(dbgPattern,arg)
            if( dbgMatch ):
                rft.dgbFlag=int(arg,0)
                rft.printVerbose(4,"Main: Flag=0x{:08x}".format(rft.dbgFlag))
            else:
                rft.printErr("Invalid -Flag value: {}".format(arg))
                rft.printErr("     Expect --Flag=<flag> where <flag> is a decimal int",noprog=True)
                sys.exit(1)
        elif opt in ("-C", "--CheckRedfishVersion"):
            rft.checkProtocolVer=True
        else:
            rft.printErr("Error: Unsupported option: {}".format(opt))
            displayUsage(rft)
            sys.exit(1)

    # if no subcommand, check if -h --help option was entered, and print help if so
    # if a subcommand was entered, then the subcommand will print the help
    if( rft.help ):
        if( not args ):
            displayHelp(rft)
            sys.exit(0)

    # if -t <token>  option was specified, the --Auth=<auth> must be Session (which is the default)
    if (rft.token is not None) and (rft.auth != "Session"):
        rft.printErr("Invalid mix of --Auth and --token options")
        rft.printErr("  if --token=<authToken> is specified, --Auth must be Session", noprog=True)
        sys.exit(1)

    # check for invalid option combinations
    if( rft.IdOptnCount > 1 ):
        if( not (rft.firstOptn and rft.gotMatchOptn )  ):
            rft.printErr("Syntax error: invalid combination of -I,-M,-1,-F options.")
            rft.printErr("    Valid combinations: -I  |  -M[F]  | -1  | -F ",noprog=True)
            displayUsage(rft)
            sys.exit(1)

    # if -I <Id>, convert to -M <prop>:<val>
    if( rft.gotIdOptn is True ):
        rft.matchProp="Id"
        rft.matchValue=rft.Id
        rft.gotMatchOptn=True
        rft.firstOptn=True

        
    # if -i <id>, convert to -m <prop>:<val>
    if( rft.gotIdLevel2Optn is True ):
        rft.matchLevel2Prop="Id"
        rft.matchLevel2Value=rft.IdLevel2
        rft.gotMatchLevel2Optn=True
        
    # check for invalid Level-2 collection member reference options
    # there are 3 ways to specify the level-2 colltion member:  -i<id>  | -m<prop>:<val>   |  -l<link> | -a
    # a command should only include one of these.  each time one if found during option processing, IdLevel2OptnCount is incremented
    if( rft.IdLevel2OptnCount > 1):
        rft.printErr("Syntax error: invalid mix of options -i,-m,-a used to specify a 2nd-level collection member.")
        rft.printErr("    Valid combinations: -i  |  -m  | -l | -a ",noprog=True)
        displayUsage(rft)
        sys.exit(1)    

    # -P, -a will be validated against the operation in the Subcommand processing
    # whether at least one -I|-M|-1|-F|-L or one -i|-m|-l|-a is required is validated in subcommand processing based on operation

    #after parsing options (GNU style) args should now be a list of arguments starting with the subcommand
    #if no subcommand at this point, it is a syntax error.
    #otherwise, save the subcommand and subcommand argv array for the subcommand to parse
    if( not args ):
        rft.printErr("Syntax error. No subcommand specified.")
        displayUsage(rft)
        sys.exit(1)
    else:
        rft.subcommand=args[0]
        rft.subcommandArgv=list(args)

    rft.printVerbose(5,"Main: subcmd: {}, subCmdArgs:{}".format(rft.subcommand,rft.subcommandArgv))
    rft.printVerbose(5,"Main: verbose={}, status={}, user={}, password={}, rhost={}".format(rft.verbose, rft.status,
                                                        rft.user,rft.password,rft.rhost))
    rft.printVerbose(5,"Main: token={}, RedfishVersion={}, Auth={}, Timeout={}".format(rft.token,
                                                        rft.protocolVer, rft.auth, rft.timeout))
    rft.printVerbose(5,"Main: prop={}, Id={}, Match={}:{}, First={}, -1={}, Link={}".format( rft.prop,
                        rft.Id, rft.matchProp,rft.matchValue, rft.firstOptn, rft.oneOptn, rft.Link))
    rft.printVerbose(5,"Main: gotIdOptn={}, IdOptnCount={}, gotPropOptn={}, gotMatchOptn={}, gotEntriesOptn={}".format(
                            rft.gotIdOptn, rft.IdOptnCount, rft.gotPropOptn, rft.gotMatchOptn, rft.gotEntriesOptn))
    rft.printVerbose(5,"Main: 2nd-Level Collection Member reference options: -i<id>={}, -m<match>={}:{}, -l<link>={} -all={}".format(
                            rft.IdLevel2, rft.matchLevel2Prop, rft.matchLevel2Value, rft.linkLevel2, rft.allOptn))
    rft.printVerbose(5,"Main: 2nd-level Collection Member parsing: gotIdLevel2Optn={}, gotMatchLevel2Optn={}, IdLevel2OptnCount={}".format(
                            rft.gotIdLevel2Optn, rft.gotMatchLevel2Optn, rft.IdLevel2OptnCount ))
    rft.printVerbose(5,"Main: configFile={}, Secure={}, waitNum:waitTime={}:{}, Degug={:08x}".format(
                                        rft.configFile,rft.secure, rft.waitNum,rft.waitTime,rft.dbgFlag))
    rft.printVerbose(5,"Main: Headers={}".format(rft.headers))

    rft.printVerbose(5,"Main: options parsed.  Now lookup subcommand and execute it")

    # instansiate the SubCmd object, and run the specified subcommand
    #rfCmds=RfSubCmds()   
    #rc=rfCmds.runSubCmd(rft)
    rc,r,j,d=runSubCmd(rft)
    if(rc !=0 ):
            rft.printVerbose(5,"#DB4:Main: subcommand returned with error: rc={}".format(rc))
            rft.printVerbose(1,"Main: Error: rc={}".format(rc))
            if r is not None:
                rft.printVerbose(5,"   Response status code:{}".format(r.status_code))
                rft.printVerbose(5,"   Response headers: {}".format(r.headers))
            #cleanup any sessions we opened
            rft.rfCleanup(rft)
            sys.exit(rc)

    rft.printVerbose(5,"Main: subcommand exited OK.")
    if( r is not None ):
        rft.printVerbose(5,"    Status code:{}".format(r.status_code))
        rft.printStatus(1,r=r)
        rft.printStatus(2,r=r)
        
    # print out result here.
    if( j is True and d is not None):
        output=json.dumps(d,indent=4)
        print(output)
    elif( j is False and d is not None):
        output=r.text
        print(output)
    else:
        pass

    #cleanup any sessions we opened on the remote service
    rft.rfCleanup(rft)

    rft.printVerbose(5,"Main: Done")
    #print("headers:{}".format(r.headers))
        
    sys.exit(0)


# enter cmdClasses in other files here:


# lookup the function for the subcommand and execute it
# pass the transport class that includes argv/argc array and Main options
# returns tuple: rc(0=ok, >0=err), r (from request), dataType(0=none,1=dict,2=text) ,d (data)
# rc, r, dt, d=runSubCmd(rft)

def runSubCmd(rft):
        # instantiate all cmdClasses (note: helloCmd and listSubcommands are in this class)
        root=RfServiceRoot()
        systems=RfSystemsMain()
        chassis=RfChassisMain()
        managers=RfManagersMain()
        sessionService=RfSessionServiceMain()
        accountService=RfAccountServiceMain()
        raw=RfRawMain()

        #  dispatch table for each subcommand:   "cmdName": cmdClass.cmdFunction"
        subCmdTable = {
            "help":             helpSubcmd,
            "about":            aboutSubcmd,
            "versions":         rft.getVersions,
            "serviceRoot":      root.getServiceRoot,
            "root":             root.getServiceRoot, #alias for serviceRoot
            "odata":            root.getOdataServiceDocument,
            "metadata":         root.getOdataMetadataDocument,
            "Systems":          systems.SystemsMain,
            "Chassis":          chassis.ChassisMain,
            "Managers":         managers.ManagersMain,
            "AccountService":   accountService.AccountServiceMain,
            "SessionService":   sessionService.SessionServiceMain,
            "raw":              raw.RawMain,
            "hello":              helloSubcmd
        }

        rft.printVerbose(5,"runSubCmd: subcmd: {}".format(rft.subcommand))
        rft.printVerbose(5,"runSubCmd: argvs:  {}".format(rft.subcommandArgv))
            
        if rft.subcommand in subCmdTable:
            rft.printVerbose(5,"runSubCmd: found SubCmd: {} in table. executing".format(rft.subcommand))
            rc,r,j,d=subCmdTable[rft.subcommand](rft,cmdTop=True)
            return(rc,r,j,d)
        
        else: # invalit subcmd
            rft.printErr("Invalid SubCommand: {}".format(rft.subcommand))
            return(1,None,False,None)

    
def helloSubcmd(rft, cmdTop=False):
        rft.printVerbose(5,"Main: in hello subcommand")
        if(rft.help):
            print("# {} [OPTIONS] hello  ---prints hello world message for debug".format(rft.program))
            return(0,None,False,None)
        print("#\n# Hello World \n#")
        return(0,None,False,None)

def helpSubcmd(rft, cmdTop=False):
        rft.printVerbose(5,"Main: in help subcommand")
        displayHelp(rft)
        return(0,None,False,None)

def aboutSubcmd(rft, cmdTop=False):
        rft.printVerbose(5,"Main: in about subcommand")
        if(rft.help):
            print("# {} [OPTIONS] about  ---prints information about {}".format(rft.program,rft.program))
            return(0,None,False,None)
        print("#")
        print("# {} {}:".format(rft.program,rft.subcommand))
        print("#     Version: {}".format(rft.version))
        print("#     Supports Redfish Protocol Versions:  {}".format(rft.supportedVersions))
        print("#     Release date:  {}".format(rft.releaseDate))
        print("#     Download from: {}".format(rft.downloadFrom))
        print("#")
        return(0,None,False,None)


if __name__ == "__main__":
    main(sys.argv)


'''
TODO
1. implement -c cfgfile
2. implement -d <data>   -d @<file>  for raw subcommand POST or PATCH data
3.


'''

