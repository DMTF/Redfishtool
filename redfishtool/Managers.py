# Copyright Notice:
# Copyright 2016 DMTF. All rights reserved.
# License: BSD 3-Clause License. For full text see link: https://github.com/DMTF/Redfishtool/blob/master/LICENSE.md

# redfishtool: Managers.py
#
# contains Managers related subCommands and access functions
#
# Class RfManagersMain
#  - functions init, displayUsage, displayHelp, displayOperations,
#  - runOperation - Managers command table, dispatch of operation eg get, reset
#  - ManagersMain - called from redfishMain, enforce legal option combinations,
#    and call runOperation to run Managers operation (sub-sub-command)
#
# Class RfManagersOperations
#  All of the Managers sub-command operations eg: Managers reset, setTime etc
#  - hello - test cmd
#  - getCollection - return the Managers collection
#  - get - get a member of a collection -or property of the member
#  - list - show of list of collection members and key idetifying properties
#      (Id, UUID, UriPath)
#  - patch - raw subcommand to patch a Managers Member, with etag support
#  - reset --reset a system instance
#  - setDateTime -- set the manager dataTime setting
#  - setTimeOffset -- set the local time offset w/o changing time
#  - getNetworkProtocol - get Network Protocol sub-resource
#  - getEnetInterfaces - get Ethernet collection, instance, all
#  - getSerialInterfaces - get SerialInterfaces collection, instance, all
#  - getLogService - get LogService collection, instance, all
#  - clearLog -- clears a specified log (not implemented yet)
#  - examples --prints some example apis
#
from   .redfishtoolTransport  import RfTransport
import requests
import json
import getopt
import re
import sys
from    .ServiceRoot import RfServiceRoot
from   urllib.parse import urljoin

class RfManagersMain():
    def __init__(self):
        # operation string and remaining args
        self.operation=None
        self.args=None
        self.argnum=0
        self.nonIdCommands=None

    def displayUsage(self,rft):
        if(rft.quiet): return(0)
        print("  Usage:")
        print("   {} [OPTNS]  Managers  <operation> [<args>]  -- perform <operation> on the Managers specified ".format(rft.program))

    def displayHelp(self,rft):
        self.displayUsage(rft)
        self.displayOperations(rft)
        print("")

    def displayOperations(self,rft):
        print("  <operations>:")
        print("     [collection]              -- get the main Managers collection. (Default operation if no member specified)")
        print("     [get]                     -- get the specified Manager object. (Default operation if collection member specified)")
        print("     list                      -- list information about the Managers collection members(\"Id\", URI, and UUID)")
        print("     patch {A: B,C: D,...}     -- patch the json-formatted {prop: value...} data to the object")
        print("     reset <resetType>         -- reset a Manager.  <resetType>= On,  GracefulShutdown, GracefulRestart, ")
        print("                                   ForceRestart, ForceOff, ForceOn, Nmi, PushPowerButton")
        print("     setDateTime <dateTimeString>--set the date and time")
        print("     setTimeOffset offset=<offsetString>  --set the time offset w/o changing time setting")
        print("                                            <offsetString> is of form \"[+/-]mm:ss\". Ex: \"-10:01\" ")
        print("     NetworkProtocol           -- get the \"NetworkProtocol\" resource under the specified manager.")
        print("     setIpAddress [-i<indx>]... -- set the Manager IP address -NOT IMPLEMENTED YET")
        print("")
        print("     EthernetInterfaces [list] -- get the managers \"EthernetInterfaces\" collection, or list \"id\",URI, Name of members.")
        print("      EthernetInterfaces [IDOPTN]--  get the member specified by IDOPTN: -i<id>, -m<prop>:<val>, -a #all")
        print("")
        print("     SerialInterfaces [list]   -- get the managers \"SerialInterfaces\" collection, or list \"id\",URI, Name of members.")
        print("      SerialInterfaces [IDOPTN]  --  get the member specified by IDOPTN: -i<id>, -m<prop>:<val>, -l<link>, -a #all")
        print("")
        print("     Logs [list]               -- get the Managers \"LogServices\" collection , or list \"id\",URI, Name of members.")
        print("      Logs [IDOPTN]              --  get the member specified by IDOPTN: -i<id>, -m<prop>:<val>, -l<link>, -a #all")
        print("     clearLog   <id>           -- clears the log defined by <id>")
        print("     examples                  -- example commands with syntax")
        print("     hello                     -- Systems hello -- debug command")
        return(0)


    def runOperation(self,rft):
        #  instantiate SystemsOperations class
        op=RfManagersOperations()
        
        #  dispatch table for each subcommand:   "cmdName": cmdClass.cmdFunction"
        operationTable = {
            "collection":                   op.getCollection,
            "get":                          op.get,
            "list":                         op.list,
            "patch":                        op.patch,
            "reset":                        op.reset,
            "setDateTime":                  op.setDateTime,
            "setTimeOffset":                op.setTimeOffset,
            "setIpAddress":                 op.setIpAddress,
            "NetworkProtocol":              op.getNetworkProtocol,
            "EthernetInterfaces":           op.getEnetInterfaces,
            "SerialInterfaces":             op.getSerialInterfaces,
            "Logs":                         op.getLogService,
            "clearLog":                     op.clearLog,
            "hello":                        op.hello,
            "examples":                     op.examples
        }

        rft.printVerbose(5,"Managers:runOperation: operation: {}".format(self.operation))
        rft.printVerbose(5,"Managers:runOperation: args:  {}".format(self.args))
            
        if self.operation in operationTable:
            rft.printVerbose(5,"Managers:runOperation: found Oper: {} in table. executing".format(rft.subcommand))
            rc,r,j,d=operationTable[self.operation](self, op, rft, cmdTop=True)
            return(rc,r,j,d)
        
        else: # invalid operation
            rft.printErr("Managers: Invalid operation: {}".format(self.operation))
            return(2,None,False,None)
        


    def ManagersMain(self,rft,cmdTop=False):
        rft.printVerbose(4,"ManagersMain:  subcommand: {}".format(rft.subcommand))
        
        if( rft.help ):
            self.displayHelp(rft)
            return(0,None,False,None)
        
        # we will validate usage of -P and -a in action processing
        # actually, if a non 'get' action is specified, -P and -a are just ignored :)

        args=rft.subcommandArgv[0:]
        
        #if no args, then if no member Id was specified (with -I|-M|-1|-F) then assume it is a "collection" operation
        #            if a -IM1F was specified, then assume it is a "get" operation for that member
        if(  len(args) < 2 ):
            if( rft.IdOptnCount==0 ):
                self.operation="collection"
            else:
                self.operation="get"
            self.args= None
        else:
            self.operation=args[1]
            self.args = args[1:]        # now args points to the 1st argument
            self.argnum =len(self.args)
            
        rft.printVerbose(5,"Managers: operation={}, args={}".format(self.operation,self.args))
                
        # check if the command requires a collection member target -I|-M|-L|-1|-F eg sysIdoptn
        nonIdCommands=["collection", "list", "examples", "hello"]
        if( ( not self.operation in nonIdCommands ) and (rft.IdOptnCount==0) ):
            rft.printErr("Managers: Syntax error: [-I|-M|-L|-F|-1] required for action that targets a specific Managers instance")
            return(0,None,False,None)
            
        # now execute the operation.
        rc,r,j,d = self.runOperation(rft)
                
        if(rc !=0 ):
            rft.printVerbose(5,"Managers: operation returned with error: rc={}".format(rc))
            return(rc,r,False,None)
        
        #else, if here, the subcommand executed without error.  Return with 0 exit code
        rft.printVerbose(5,"Managers: operation exited OK")
        return(rc,r,j,d)


#
# contains operations related to the Managers subCommand
#
class RfManagersOperations():
    def __init__(self):
        self.managersPath=None
        self.managersollectionDict=None


    def hello(self,sc,op,rft,cmdTop=False):
        rft.printVerbose(4,"in hello")
        rft.printVerbose(4,"   subcmd:{}, operation:{}, args:{}".format(rft.subcommand,sc.operation,sc.args))
        print("hello world from Managers")
        return(0,None,False,None)

    def getCollection(self,sc,op,rft,cmdTop=False, prop=None):
        rft.printVerbose(4,"{}:{}: in getCollection".format(rft.subcommand,sc.operation))
        
        # 1st get serviceRoot
        svcRoot=RfServiceRoot()
        rc,r,j,d = svcRoot.getServiceRoot(rft)
        if( rc != 0 ):
            rft.printErr("getCollection: Error getting service root, aborting")
            return(rc,r,False,None)

        # get the link to the Managers collection
        # need to test we got good data
        if (("Managers" in d) and ("@odata.id" in d["Managers"])):
            systemsLink=d["Managers"]["@odata.id"]
        else:
            rft.printErr("Error: service root does not have a Managers link")
            return(4)
        
        rft.printVerbose(4,"Managers:getCollection: link is: {}".format(systemsLink))


        # if a -a option was entered with "Managers" or "Managers collection" operation,
        # then return all members of the Managers collection expanded
        if((cmdTop is True) and (rft.allOptn is True) ):
            collName="Managers"
            rft.printVerbose(4,"Expand Managers collection to return ALL Managers collection members fully expanded in response")
            rc,r,j,d=rft.getAllCollectionMembers(rft, r.url, relPath=systemsLink)
            if(rc==0):
                rft.printVerbose(1," Get ALL {} Collection Members".format(collName,skip1=True, printV12=cmdTop))

        # otherwise, just return the collection
        # now read the /Managers collection
        # use the returned url as the base url to read the Managers collection
        else:
            if cmdTop is True:   prop=rft.prop
            rc,r,j,d=rft.rftSendRecvRequest(rft.AUTHENTICATED_API, 'GET', r.url, relPath=systemsLink, prop=prop)
            if(rc==0):
                rft.printVerbose(1," Managers Collection:",skip1=True, printV12=cmdTop)
                
        return(rc,r,j,d)


    def get(self,sc,op,rft, cmdTop=False, prop=None):
        rft.printVerbose(4,"{}:{}: in operation".format(rft.subcommand,sc.operation))
        
        # getCollection
        rc,r,j,d=op.getCollection(sc,op, rft)
        if( rc != 0):  return(rc,r,False,None)
        collUrl=r.url

        # search collection to find path to the Manager
        sysPath,rc,r,j,d=rft.getPathBy(rft, r, d)
        if( rc !=0 ):    #if a path was not found, its an error
            return(rc,r,j,d)
        
        rft.printVerbose(4,"ManagersOperations:get: got a path, now get entries")
        
        if cmdTop is True:   prop=rft.prop

        #if here, rc=0
        #if sysPath returned a response but we need to extract the property do it here
        if( (r is not None) and (prop is not None) ):
            rc,r,j,d=rft.getPropFromDict(rft,r,d,prop)
                
        # otherwise, we need to do a GET to get the Manager, if -P show property, else show full response
        elif( r is None ):
            rc,r,j,d=rft.rftSendRecvRequest(rft.AUTHENTICATED_API, 'GET', collUrl, relPath=sysPath, prop=prop)

        if(rc==0):   rft.printVerbose(1," Managers Resource:",skip1=True, printV12=cmdTop)
        return(rc,r,j,d)


    def list(self,sc,op,rft, cmdTop=False, prop=None):
        rft.printVerbose(4,"{}:{}: in operation".format(rft.subcommand,sc.operation))
        
        # getCollection
        collName="Managers"
        rc,r,j,d=op.getCollection(sc,op, rft)
        if( rc != 0):  return(rc,r,False,None)
        #loop through the members and create the list sub-operation response
        rc,r,j,d=rft.listCollection(rft, r, d, prop="UUID")
        if(rc==0):
            rft.printVerbose(1," list {} Collection member info: Id, URI, UUID".format(collName,skip1=True, printV12=cmdTop))
        return(rc,r,j,d)


    def patch(self,sc,op,rft,cmdTop=False, prop=None, patchData=None, r=None):
        rft.printVerbose(4,"{}:{}: in operation".format(rft.subcommand,sc.operation))
        # verify we have got an argument which is the patch structure
        # its in form '{ "AssetTag": <val>, "IndicatorLed": <val> }'
        ##print("patchData: {}".format(patchData))
        if( len( sc.args) == 2):
            try:
                patchData=json.loads(sc.args[1])
            except ValueError:
                rft.printErr("Patch: invalid Json input data:{}".format(sc.args[1]))
                return(5,None,False,None)
        else:
            rft.printErr("Patch: error: invalid argument format")
            rft.printErr("     : args={}".format(sc.args))
            rft.printErr("     : expect: Systems patch \"{ <prop>: <value> }\"")
            return(4,None,False,None)

        # read the Managers resource
        # this is used by the generic rft.patchResource() function to see if there is an etag in the response
        # if an etag is in response hdr, then we must include the etag on the patch, so this get is required
        # note: the format of etag header for redfish is:  ETag: W/"<string>" or "<string"
        rc,r,j,d=op.get(sc,op,rft)
        if( rc != 0):
            return(rc,r,False,None)

        # now call the generic patch function to send the patch
        rc,r,j,d=rft.patchResource(rft, r, patchData)

        if(rc==0):   rft.printVerbose(1," Managers Patch:",skip1=True, printV12=cmdTop)
        return(rc,r,j,d)


    def reset(self,sc,op,rft,cmdTop=False, prop=None):
        # this operation has argument syntaxes below:
        #     ...reset <resetType>
        #   where <resetType> is a subset of Redfish defined redfish resetType values
        #   and will be validated against the allowable values read from the remote service
        rft.printVerbose(4,"{}:{}: in operation".format(rft.subcommand,sc.operation))
        
        # get the resetType from args
        validResetTypes=["On","ForceOff","GracefulShutdown","ForceRestart","Nmi","GracefulRestart",
                                    "ForceOn","PushPowerButton","PowerCycle"]
        if(len(sc.args) < 2 ):
            rft.printErr("Error, no resetType value specified")
            return(8,None,False,None)

        resetType=sc.args[1]
        if not resetType in  validResetTypes:
            rft.printErr("Error, Invalid <resetType> value specified: {}".format(resetType))
            return(8,None,False,None)
     
        #now read remote service to find out if specified resetType is one of the allowable values for this rhost
        rc,r,j,d=op.get(sc,op,rft,prop="Actions")
        if(rc != 0):
            print("Error, cant read Actions properties from remote service")
            return(8,None,False,None)

        if( (j is True) and ("Actions" in d) and ("#Manager.Reset" in d["Actions"])):
            resetProps=d["Actions"]["#Manager.Reset"]
            if( "ResetType@Redfish.AllowableValues" in resetProps ):
                supportedResetTypes=resetProps["ResetType@Redfish.AllowableValues"]
                if not resetType in supportedResetTypes:
                    rft.printErr("Error, the resetType specified is not supported by the remote service (via @Redfish.AllowableValues)")
                    return(8,None,False,None)
            elif "@Redfish.ActionInfo" in resetProps:
                action_info_path = resetProps["@Redfish.ActionInfo"]
                supportedResetTypes = rft.getActionInfoAllowableValues(rft, r, action_info_path, "ResetType")
                if supportedResetTypes is not None and resetType not in supportedResetTypes:
                    rft.printErr("Error, the resetType specified is not supported by the remote service (via @Redfish.ActionInfo)")
                    return(8,None,False,None)
            else: # rhost didn't return any AllowableValues, but it isn't required, so allow the action
                rft.printVerbose(2, "The remote service does not have a ResetType@Redfish.AllowableValues or @Redfish.ActionInfo prop")
        else:
            rft.printErr("Error, the remote service does not have an Actions: Manager.Reset property")
            return(8,None,False,None)
        
        # now get the target URI from the remote host
        if( not "target" in resetProps ):
                rft.printErr("Error, the remote service doesnt have a Reset Target property (the reset path)")
                return(8,None,False,None)
        resetPath=resetProps["target"]
        
        resetData={"ResetType": resetType }

        #since we already did a get, we have the path and can just execute the post directly.
        #output the post data in json to send over the network   
        reqPostData=json.dumps(resetData)           
        # send post to rhost.  Use the resetPath as the relative path
        rc,r,j,d=rft.rftSendRecvRequest(rft.AUTHENTICATED_API, 'POST', r.url, relPath=resetPath,
                                         reqData=reqPostData)
                   
        if(rc==0):
            rft.printVerbose(1," Managers reset: ", resetType, skip1=True, printV12=cmdTop)
            resetd=None
            return(rc,r,False,resetd)
        else: return(rc,r,False,None)


    # setDateTime -- command to set the Managers time--and timezone
    def setDateTime(self,sc,op,rft,cmdTop=False, prop=None):
        rft.printVerbose(4,"{}:{}: in operation".format(rft.subcommand,sc.operation))

        propName="DateTime"
        # get the target dateTime from args
        if(len(sc.args) < 2 ):
            rft.printErr("Error, no dateTime argument specified")
            rft.printErr("Syntax:  {} [options] Managers setDateTime <dateTimeString>".format(rft.program))
            rft.printErr("   <dateTimeString> in form: \"YYYY-MM-DDThh:mm:ss[+/-]hh:ss\"")
            return(8,None,False,None)
        else: #we have an arg[1]
            datePattern="(^[2][0]\d{2}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[-+][0-1][0-9]:[0-5][0-9]$)"   #  YYYY-MM-DDTHH:mm:ss[+/-]hh:ss
            dateMatch=re.search(datePattern,sc.args[1])  # sc.args[1]=<dateTimeString>
            if( dateMatch ):
                dateTimeString=(sc.args[1])  # keep it a string
                rft.printVerbose(4,"setDateTime: dateTime={}".format(dateTimeString))
            else:
                rft.printErr("Error:   setDateTime: invalid <dateTime> value specified: {}".format(sc.args[1]))
                rft.printErr("Managers setDateTime <dateTimeString> # eg: YYYY-MM-DDThh:mm:ss[+/-]hh:ss")
                return(8,None,False,None)

        patchData={propName: dateTimeString}                       
        
        # get the resource to verify it includes dateTime property,
        # the response will also be used by Patch() to check for etag 
        rc,r,j,d=op.get(sc,op,rft)
        if( rc != 0):  return(rc,r,False,None)
        if( not propName in d ):
            rft.printErr("Managers resource does not have a {} property.".format(propName))
            return(8,r,False,None)

        rc,r,j,d=rft.patchResource(rft, r, patchData)
        if(rc==0):
            rft.printVerbose(1," setDateTime:",skip1=True, printV12=cmdTop)
            dateTimeReturned={propName: d[propName]}
            return(rc,r,j,dateTimeReturned)         
        else: return(rc,r,False,None)



    # setTimeOffset  -- command to change the Managers timezone offset (w/o changing time)
    def setTimeOffset(self,sc,op, rft, cmdTop=False, prop=None):
        rft.printVerbose(4,"{}:{}: in operation".format(rft.subcommand,sc.operation))

        propName="DateTimeLocalOffset"
        # get the target offset from args
        if(len(sc.args) < 2 ):
            rft.printErr("Error, no timeOffset argument specified")
            rft.printErr("Syntax:  {} [options] Managers setTimeOffset offset=<timeOffsetString>".format(rft.program))
            rft.printErr("   where <timeOffsetString> in form: \"[+/-]hh:ss\",  ex:  -06:00 ")
            return(8,None,False,None)
        else: #we have an arg[1]
            datePattern="^offset=([-+][0-1][0-9]:[0-5][0-9])$"   #  [+/-]hh:ss
            dateMatch=re.search(datePattern,sc.args[1])  # sc.args[1]=<timeOffset>
            if( dateMatch ):
                timeOffsetString=dateMatch.group(1) # keep it a string. <timeOffsetString>
                rft.printVerbose(4,"setDateTime: timeOffset={}".format(timeOffsetString))
            else:
                rft.printErr("Error:   setTimeOffset: invalid <timeOffset> value specified: {}".format(sc.args[1]))
                rft.printErr("Managers setTimeOffset offset=<timeOffset> # eg: where <timeOffset>=[+/-]hh:ss")
                return(8,None,False,None)

        patchData={propName: timeOffsetString}                       
        
        # get the resource to verify it includes DateTimeLocalOffset property,
        # the response will also be used by Patch() to check for etag 
        rc,r,j,d=op.get(sc,op,rft)
        if( rc != 0):  return(rc,r,False,None)
        if( not propName in d ):
            rft.printErr("Managers resource does not have a {} property.".format(propName))
            return(8,r,False,None)

        rc,r,j,d=rft.patchResource(rft, r, patchData)
        if(rc==0):
            rft.printVerbose(1," setTimeOffset:",skip1=True, printV12=cmdTop)
            timeOffsetReturned={propName: d[propName]}
            return(rc,r,j,timeOffsetReturned)         
        else: return(rc,r,False,None)


    def getNetworkProtocol(self,sc,op, rft, cmdTop=False, prop=None):
        rft.printVerbose(4,"{}:{}: in operation".format(rft.subcommand,sc.operation))

        # get the Manager resource first
        rc,r,j,d=op.get(sc,op, rft)     
        if( rc != 0):  return(rc,r,False,None)
        
        resName="NetworkProtocol"
        # get the link to the NetworkProtocol resource under Manager
        if ((resName in d) and ("@odata.id" in d[resName])):
            resLink=d[resName]["@odata.id"]
        else:
            rft.printErr("Error: Manager resource does not have a {} link".format(resName))
            return(6,None,False,None)
        
        if cmdTop is True:   prop=rft.prop

        rc,r,j,d=rft.rftSendRecvRequest(rft.AUTHENTICATED_API, 'GET', r.url, relPath=resLink, prop=prop)
        if(rc==0):
            rft.printVerbose(1," {} Resource ".format(resName,skip1=True, printV12=cmdTop))

        return(rc,r,j,d)


    # setIpAddress  -- command to set the IP address of the MC
    def setIpAddress(self,sc,op, rft, cmdTop=False, prop=None):
        rft.printVerbose(4,"{}:{}: in operation".format(rft.subcommand,sc.operation))
        print("Not Implemented Yet")
        return(6,None,False,None)

    
    def getEnetInterfaces(self,sc,op,rft,cmdTop=False, prop=None):
        rft.printVerbose(4,"{}:{}: in operation".format(rft.subcommand,sc.operation))

        # get the Manager resource
        rc,r,j,d=op.get(sc,op, rft)     
        if( rc != 0):  return(rc,r,False,None)
        
        collName="EthernetInterfaces"
        # get the link to the EthernetInterfaces collection
        if ((collName in d) and ("@odata.id" in d[collName])):
            nicLink=d[collName]["@odata.id"]
        else:
            rft.printErr("Error: Manager resource does not have a {} link".format(collName))
            return(6,None,False,None)
        
        if cmdTop is True:   prop=rft.prop
        
        # check if there is a list arg for the operation
        if( sc.argnum > 1 and sc.args[1] == 'list' ):
            #get the collection
            rc,r,j,d=rft.rftSendRecvRequest(rft.AUTHENTICATED_API, 'GET', r.url, relPath=nicLink)
            #loop through the members and create the list sub-operation response
            rc,r,j,d=rft.listCollection(rft, r, d, prop="Name")
            if(rc==0):
                rft.printVerbose(1," list {} Collection member info: Id, URI, Name".format(collName,skip1=True, printV12=cmdTop))

        # else: check if no NIC was specified.  If not, return the collection
        elif(rft.IdLevel2OptnCount==0):
            rc,r,j,d=rft.rftSendRecvRequest(rft.AUTHENTICATED_API, 'GET', r.url, relPath=nicLink, prop=prop)
            if(rc==0):
                rft.printVerbose(1," {} Collection ".format(collName,skip1=True, printV12=cmdTop))

        # else:  check if the -a (all) option is set. If not, return the proc specific by -i or -m
        # search collection to find path using getPath2 
        elif( rft.allOptn is not True ):
            # get the EthernetInterfaces collection
            rc,r,j,d=rft.rftSendRecvRequest(rft.AUTHENTICATED_API, 'GET', r.url, relPath=nicLink, prop=prop)
            collUrl=r.url

            # now search for 2nd level resource and return
            path2,rc,r,j,d=rft.getLevel2ResourceById(rft,r,d)
            if(rc!=0):
                return(rc,r,j,d)
            # so rc=0
            #if sysPath returned a response but we need to extract the property do it here
            if( (r is not None) and (prop is not None) ):
                rc,r,j,d=rft.getPropFromDict(rft,r,d,prop)

            # otherwise, we need to do a GET to get the EthernetInterfaces, if -P show property, else show full response
            elif( r is None ):
                rc,r,j,d=rft.rftSendRecvRequest(rft.AUTHENTICATED_API, 'GET', collUrl, relPath=path2, prop=prop)
                if(rc==0):
                    rft.printVerbose(1," {} Collection Member ".format(collName,skip1=True, printV12=cmdTop))

        # else, return ALL of the EthernetInterfaces members
        else:
            rft.printVerbose(4,"getting expanded EthernetInterfaces Collection")
            rc,r,j,d=rft.getAllCollectionMembers(rft, r.url, relPath=nicLink)
            if(rc==0):
                rft.printVerbose(1," Get ALL {} Collection Members".format(collName,skip1=True, printV12=cmdTop))
        
        return(rc,r,j,d)



    def getSerialInterfaces(self,sc,op,rft,cmdTop=False, prop=None):
        rft.printVerbose(4,"{}:{}: in operation".format(rft.subcommand,sc.operation))

        # get the Manager resource
        rc,r,j,d=op.get(sc,op, rft)     
        if( rc != 0):  return(rc,r,False,None)
        
        collName="SerialInterfaces"
        # get the link to the SerialInterfaces collection
        if ((collName in d) and ("@odata.id" in d[collName])):
            cntlrLink=d[collName]["@odata.id"]
        else:
            rft.printErr("Error: Manager resource does not have a {} link".format(collName))
            return(6,None,False,None)

        if cmdTop is True:   prop=rft.prop

        # check if there is a list arg for the operation
        if( sc.argnum > 1 and sc.args[1] == 'list' ):
            #get the collection
            rc,r,j,d=rft.rftSendRecvRequest(rft.AUTHENTICATED_API, 'GET', r.url, relPath=cntlrLink)
            #loop through the members and create the list sub-operation response
            rc,r,j,d=rft.listCollection(rft, r, d, prop="Name" )
            if(rc==0):
                rft.printVerbose(1," list {} Collection member info: Id, URI, Name".format(collName,skip1=True, printV12=cmdTop))

        # else: check if no SerialInterfaces controller was specified.  If not, return the collection
        elif(rft.IdLevel2OptnCount==0):
            rc,r,j,d=rft.rftSendRecvRequest(rft.AUTHENTICATED_API, 'GET', r.url, relPath=cntlrLink, prop=prop)
            if(rc==0):
                rft.printVerbose(1," {} Collection ".format(collName,skip1=True, printV12=cmdTop))

        # else:  check if the -a (all) option is set. If not, return the proc specific by -i or -m
        # search collection to find path using getPath2 
        elif( rft.allOptn is not True ):
            # get the SerialInterfaces collection
            rc,r,j,d=rft.rftSendRecvRequest(rft.AUTHENTICATED_API, 'GET', r.url, relPath=cntlrLink, prop=prop)
            collUrl=r.url

            # now search for 2nd level resource and return
            path2,rc,r,j,d=rft.getLevel2ResourceById(rft,r,d)
            if(rc!=0):
                return(rc,r,j,d)
            # so rc=0
            #if sysPath returned a response but we need to extract the property do it here
            if( (r is not None) and (prop is not None) ):
                rc,r,j,d=rft.getPropFromDict(rft,r,d,prop)

            # otherwise, we need to do a GET to get the SerialInterfaces, if -P show property, else show full response
            elif( r is None ):
                rc,r,j,d=rft.rftSendRecvRequest(rft.AUTHENTICATED_API, 'GET', collUrl, relPath=path2, prop=prop)
                if(rc==0):
                    rft.printVerbose(1," {} Collection Member ".format(collName,skip1=True, printV12=cmdTop))

        # else, return ALL of the SerialInterfaces members
        else:
            rft.printVerbose(4,"getting expanded SerialInterfaces Collection")
            rc,r,j,d=rft.getAllCollectionMembers(rft, r.url, relPath=cntlrLink)
            if(rc==0):
                rft.printVerbose(1," Get ALL {} Collection Members".format(collName,skip1=True, printV12=cmdTop))
        
        return(rc,r,j,d)


    
    def getLogService(self,sc,op,rft,cmdTop=False, prop=None):
        rft.printVerbose(4,":{}:{}: in operation".format(rft.subcommand,sc.operation))

        # get the Manager resource
        rc,r,j,d=op.get(sc,op, rft)     
        if( rc != 0):  return(rc,r,False,None)
        
        collName="LogServices"
        # get the link to the LogServices collection
        if ((collName in d) and ("@odata.id" in d[collName])):
            logLink=d[collName]["@odata.id"]
        else:
            rft.printErr("Error: Manager resource does not have a {} link".format(collName))
            return(6,None,False,None)

        if cmdTop is True:   prop=rft.prop

        # check if there is a list arg for the operation
        if( sc.argnum > 1 and sc.args[1] == 'list' ):
            #get the collection
            rc,r,j,d=rft.rftSendRecvRequest(rft.AUTHENTICATED_API, 'GET', r.url, relPath=logLink)
            #loop through the members and create the list sub-operation response
            rc,r,j,d=rft.listCollection(rft, r, d, prop="Name")
            if(rc==0):
                rft.printVerbose(1," list {} Collection member info: Id, URI, Name".format(collName,skip1=True, printV12=cmdTop))

        # else: check if no Log was specified.  If not, return the collection
        elif(rft.IdLevel2OptnCount==0):
            rc,r,j,d=rft.rftSendRecvRequest(rft.AUTHENTICATED_API, 'GET', r.url, relPath=logLink, prop=prop)
            if(rc==0):
                rft.printVerbose(1," {} Collection ".format(collName,skip1=True, printV12=cmdTop))

        # else:  check if the -a (all) option is set. If not, return the proc specific by -i or -m
        # search collection to find path using getPath2 
        elif( rft.allOptn is not True ):
            # get the LogServices collection
            rc,r,j,d=rft.rftSendRecvRequest(rft.AUTHENTICATED_API, 'GET', r.url, relPath=logLink, prop=prop)
            collUrl=r.url

            # now search for 2nd level resource and return
            path2,rc,r,j,d=rft.getLevel2ResourceById(rft,r,d)
            if(rc!=0):
                return(rc,r,j,d)
            # so rc=0
            #if sysPath returned a response but we need to extract the property do it here
            if( (r is not None) and (prop is not None) ):
                rc,r,j,d=rft.getPropFromDict(rft,r,d,prop)

            # otherwise, we need to do a GET to get the LogServices, if -P show property, else show full response
            elif( r is None ):
                rc,r,j,d=rft.rftSendRecvRequest(rft.AUTHENTICATED_API, 'GET', collUrl, relPath=path2, prop=prop)
                if(rc==0):
                    rft.printVerbose(1," {} Collection Member ".format(collName,skip1=True, printV12=cmdTop))

            # If '--Entries' specified, get "Entries" nav link and read it
            if rc == 0 and rft.gotEntriesOptn:
                if r is not None and j and isinstance(d, dict):
                    rft.printVerbose(1, 'getLogService: attempting to get Entries for Logs')
                    entries = d.get('Entries')
                    if entries is not None and isinstance(entries, dict):
                        entries_uri = entries.get('@odata.id')
                        if entries_uri is not None:
                            rc, r, j, d = rft.rftSendRecvRequest(rft.AUTHENTICATED_API, 'GET', r.url,
                                                                 relPath=entries_uri, prop=prop)
                        else:
                            rft.printErr('getLogService: @odata.id not found in "Entries" property')
                    else:
                        rft.printErr('getLogService: "Entries" property not found in JSON payload')
                else:
                    rft.printErr(
                        'Unable to fetch Entries property from previous response: response = {}, is_json = {}, type(json) = {}'
                        .format(r, j, type(d)))

        # else, client specified the -a option requesting ALL of the LogServices members
        # for logs, we will not support this.  Its too much data.
        else:
            rft.printErr("Error: -a option not supported for LogServices")
            return(6,None,False,None)
        
        return(rc,r,j,d)

    
    def clearLog(self,sc,op,rft,cmdTop=False, prop=None):
        rft.printVerbose(4,"{}:{}: in operation".format(rft.subcommand,sc.operation))
        print("NOT IMPLEMENTED YET")
        return(8,None,False,None)

      
    def examples(self,sc,op,rft,cmdTop=False,prop=None):
        rft.printVerbose(4,"{}:{}: in operation".format(rft.subcommand,sc.operation))
        print(" {} -r<ip>                           # shows the Managers collection".format(rft.program))
        print(" {} -r<ip> Managers list                     # lists Id, Uri, AssetTag for all Managers".format(rft.program))
        print(" {} -r<ip> Managers -I <id>                  # gets the Manager with Id=<d>".format(rft.program))
        print(" {} -r<ip> Managers -M AssetTag:12345        # gets the Manager with AssetTag=12345".format(rft.program))
        print(" {} -r<ip> Managers -L <mgrUrl>              # gets the Manager at URI=<mgrUrl".format(rft.program))
        print(" {} -r<ip> Managers -F                       # get the First Manager returned (for debug)".format(rft.program))
        print(" {} -r<ip> Managers -1                       # get the first Manager and verify that there is only one Manager".format(rft.program))
        print(" {} -r<ip> Managers -I <id> patch {{A: B,C: D,...}}# patch the json-formatted {{prop: value...}} data to the object".format(rft.program))
        print(" {} -r<ip> Managers -I <id> reset <resetType>      # reset a Manager.  <resetType>=the redfish-defined values: On, Off, gracefulOff...".format(rft.program))
        print(" {} -r<ip> Managers -I<Id> NetworkProtocol         # get the NetworkProtocol resource under the specified manager".format(rft.program))
        print(" {} -r<ip> Managers -I<Id> EthernetInterfaces list # lists Id, Uri, and Name for all of the NICs for Manager w/ Id=<Id>".format(rft.program))
        print(" {} -r<ip> Managers -I<Id> EthernetInterfaces -i 1 # get the NIC with id=1 in manager with Id=<Id>".format(rft.program))
        print(" {} -r<ip> Managers -L <Url> EthernetInterfaces -m MACAddress:AA:BB:CC:DD:EE:FF # get NIC with MAC AA:BB... for manager at url <Url>".format(rft.program))
        return(0,None,False,None)


    
'''
TODO:
1. clearlog not implemented
2. setIpAddress not implemented

'''

    


