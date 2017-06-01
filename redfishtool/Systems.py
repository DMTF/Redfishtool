# Copyright Notice:
# Copyright 2016 Distributed Management Task Force, Inc. All rights reserved.
# License: BSD 3-Clause License. For full text see link: https://github.com/DMTF/Redfishtool/LICENSE.md

# redfishtool: Systems.py
#
# contains Systems related subCommands and access functions
#
# Class RfSystemsMain
#  - functions init, displayUsage, displayHelp, displayOperations,
#  - runOperation - Systems command table, dispatch of operation eg get, reset
#  - SystemsMain - called from redfishMain, enforce legal option combinations,
#    and call runOperation to run System operation (sub-sub-command)
#
# Class RfSystemsOperations
#  All of the Systems sub-command operations eg: Systems reset, setIndicatorLed, etc
#  - hello - test cmd
#  - getCollection - return the Systems collection
#  - get - get a member of a collection -or property of the member
#  - list - show of list of collection members and key idetifying properties
#      (Id, AssetTag, UriPath)
#  - patch - raw subcommand to patch a System Member, with etag support
#  - reset --reset a system instance
#  - setAssetTag -- patches the assetTag of system instance w/ etag support
#  - setIndicatorLed --sets id LED to a specified value w/ etag support
#  - setBootOverride -set boot override enable, and target to valid values
#    with proper checking for valid values...
#  - getProcessors - get Processors collection, processor instance, or all
#  - getEnetInterfaces - get Ethernet collection, instance, all
#  - getSimpleStorage - get SimpleStorage collection, instance, all
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

class RfSystemsMain():
    def __init__(self):
        # operation string and remaining args
        self.operation=None
        self.args=None
        self.argnum=0
        self.nonIdCommands=None

    def displayUsage(self,rft):
        if(rft.quiet): return(0)
        print("  Usage:")
        print("   {} [OPTNS]  Systems  <operation> [<args>]  -- perform <operation> on the system specified ".format(rft.program))

    def displayHelp(self,rft):
        self.displayUsage(rft)
        self.displayOperations(rft)
        print("")
        
    def displayOperations(self,rft):
        print("  <operations>:")
        print("     [collection]              -- get the main Systems collection. (Default operation if no member specified)")
        print("     [get]                     -- get the computerSystem object. (Default operation if collection member specified)")
        print("     list                      -- list information about the Systems collection members(\"Id\", URI, and AssetTag)")
        print("     patch {A: B,C: D,...}     -- patch the json-formatted {prop: value...} data to the object")
        print("     reset <resetType>         -- reset a system.  <resetType>= On,  GracefulShutdown, GracefulRestart, ")
        print("                                   ForceRestart, ForceOff, ForceOn, Nmi, PushPowerPutton")
        print("     setAssetTag <assetTag>    -- set the system's asset tag ")
        print("     setIndicatorLed  <state>  -- set the indicator LED.  <state>=redfish defined values: Off, Lit, Blinking")
        print("     setBootOverride <enabledVal> <targetVal> -- set Boot Override properties. <enabledVal>=Disabled|Once|Continuous")
        print("                               -- <targetVal> =None|Pxe|Floppy|Cd|Usb|Hdd|BiosSetup|Utilities|Diags|UefiTarget|")
        print("     Processors [list]         -- get the \"Processors\" collection, or list \"id\" and URI of members.")
        print("      Processors [IDOPTN]        --  get the  member specified by IDOPTN: -i<id>, -m<prop>:<val>, -l<link>, -a #all")
        print("")
        print("     EthernetInterfaces [list] -- get the \"EthernetInterfaces\" collection, or list \"id\" and URI of members.")
        print("      EthernetInterfaces [IDOPTN]--  get the member specified by IDOPTN: -i<id>, -m<prop>:<val>, -l<link>, -a #all")
        print("")
        print("     SimpleStorage [list]      -- get the ComputerSystem \"SimpleStorage\" collection, or list \"id\" and URI of members.")
        print("      SimpleStorage [IDOPTN]     --  get the member specified by IDOPTN: -i<id>, -m<prop>:<val>, -l<link>, -a #all")
        print("")
        print("     Logs [list]               -- get the ComputerSystem \"LogServices\" collection , or list \"id\" and URI of members.")
        print("      Logs [IDOPTN]              --  get the member specified by IDOPTN: -i<id>, -m<prop>:<val>, -l<link>, -a #all")
        print("     clearLog   <id>           -- clears the log defined by <id>")
        print("     examples                  -- example commands with syntax")
        print("     hello                     -- Systems hello -- debug command")
        return(0)



    def runOperation(self,rft):
        #  instantiate SystemsOperations class
        op=RfSystemsOperations()
        
        #  dispatch table for each subcommand:   "cmdName": cmdClass.cmdFunction"
        operationTable = {
            "collection":                   op.getCollection,
            "get":                          op.get,
            "list":                         op.list,
            "patch":                        op.patch,
            "reset":                        op.reset,
            "setAssetTag":                  op.setAssetTag,
            "setIndicatorLed":              op.setIndicatorLed,
            "setBootOverride":              op.setBootOverride,
            "Processors":                   op.getProcessors,
            "EthernetInterfaces":           op.getEnetInterfaces,
            "SimpleStorage":                op.getSimpleStorage,
            "Logs":                         op.getLogService,
            "-clearLog":                     op.clearLog,
            "hello":                        op.hello,
            "examples":                     op.examples
        }

        rft.printVerbose(5,"Systems:runOperation: operation: {}".format(self.operation))
        rft.printVerbose(5,"Systems:runOperation: args:  {}".format(self.args))
            
        if self.operation in operationTable:
            rft.printVerbose(5,"Systems:runOperation: found Oper: {} in table. executing".format(rft.subcommand))
            rc,r,j,d=operationTable[self.operation](self, op, rft, cmdTop=True)
            return(rc,r,j,d)
        
        else: # invalid operation
            rft.printErr("Systems: Invalid operation: {}".format(self.operation))
            return(2,None,False,None)
        


    def SystemsMain(self,rft,cmdTop=False):
        rft.printVerbose(4,"SystemsMain:  subcommand: {}".format(rft.subcommand))
        
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
            
        rft.printVerbose(5,"Systems: operation={}, args={}".format(self.operation,self.args))
                
        # check if the command requires a collection member target -I|-M|-L|-1|-F eg sysIdoptn
        nonIdCommands=["collection", "list", "examples", "hello"]
        if( ( not self.operation in nonIdCommands ) and (rft.IdOptnCount==0) ):
            rft.printErr("Systems: Syntax error: [-I|-M|-L|-F|-1] required for action that targets a specific system instance")
            return(0,None,False,None)
            
        # now execute the operation.
        rc,r,j,d = self.runOperation(rft)
                
        if(rc !=0 ):
            rft.printVerbose(5,"Systems: operation returned with error: rc={}".format(rc))
            return(rc,r,False,None)
        
        #else, if here, the subcommand executed without error.  Return with 0 exit code
        rft.printVerbose(5,"Systems: operation exited OK")
        return(rc,r,j,d)


#
# contains operations related to the Systems subCommand
#
class RfSystemsOperations():
    def __init__(self):
        self.systemsPath=None
        self.systemsCollectionDict=None


    def hello(self,sc,op,rft,cmdTop=False):
        rft.printVerbose(4,"in hello")
        rft.printVerbose(4,"   subcmd:{}, operation:{}, args:{}".format(rft.subcommand,sc.operation,sc.args))
        print("hello world from Systems")
        return(0,None,False,None)
    
    def getCollection(self,sc,op,rft,cmdTop=False, prop=None):
        rft.printVerbose(4,"{}:{}: in getCollection".format(rft.subcommand,sc.operation))
        
        # 1st get serviceRoot
        svcRoot=RfServiceRoot()
        rc,r,j,d = svcRoot.getServiceRoot(rft)
        if( rc != 0 ):
            rft.printErr("getCollection: Error getting service root, aborting")
            return(rc,r,False,None)

        # get the link to the Systems collection
        # need to test we got good data
        if (("Systems" in d) and ("@odata.id" in d["Systems"])):
            systemsLink=d["Systems"]["@odata.id"]
        else:

            rft.printErr("Error: service root does not have a Systems link")
            return(4)
        
        rft.printVerbose(4,"Systems:getCollection: link is: {}".format(systemsLink))


        # if a -a option was entered with "Systems" or "Systems collection" operation,
        # then return all members of the Systems collection expanded
        if((cmdTop is True) and (rft.allOptn is True) ):
            collName="Systems"
            rft.printVerbose(4,"Expand Systems collection to return ALL Systems collection members fully expanded in response")
            rc,r,j,d=rft.getAllCollectionMembers(rft, r.url, relPath=systemsLink)
            if(rc==0):
                rft.printVerbose(1," Get ALL {} Collection Members".format(collName,skip1=True, printV12=cmdTop))

        # otherwise, just return the collection
        # now read the /Systems collection
        # use the returned url as the base url to read the systems collection
        else:
            if cmdTop is True:   prop=rft.prop
            rc,r,j,d=rft.rftSendRecvRequest(rft.AUTHENTICATED_API, 'GET', r.url, relPath=systemsLink, prop=prop)
            if(rc==0):
                rft.printVerbose(1," Systems Collection:",skip1=True, printV12=cmdTop)
                
        return(rc,r,j,d)


    def get(self,sc,op,rft, cmdTop=False, prop=None):
        rft.printVerbose(4,"{}:{}: in operation".format(rft.subcommand,sc.operation))
        
        # getCollection
        rc,r,j,d=op.getCollection(sc,op, rft)
        if( rc != 0):  return(rc,r,False,None)
        collUrl=r.url

        # search collection to find path to system
        sysPath,rc,r,j,d=rft.getPathBy(rft, r, d)
        if( rc !=0 ):    #if a path was not found, its an error
            return(rc,r,j,d)
        
        rft.printVerbose(4,"SystemsOperations:get: got a path, now get entries")
        
        if cmdTop is True:   prop=rft.prop

        #if here, rc=0
        #if sysPath returned a response but we need to extract the property do it here
        if( (r is not None) and (prop is not None) ):
            rc,r,j,d=rft.getPropFromDict(rft,r,d,prop)
                
        # otherwise, we need to do a GET to get the system, if -P show property, else show full response
        elif( r is None ):
            rc,r,j,d=rft.rftSendRecvRequest(rft.AUTHENTICATED_API, 'GET', collUrl, relPath=sysPath, prop=prop)

        if(rc==0):   rft.printVerbose(1," Systems Resource:",skip1=True, printV12=cmdTop)
        return(rc,r,j,d)


    def list(self,sc,op,rft, cmdTop=False, prop=None):
        rft.printVerbose(4,"{}:{}: in operation".format(rft.subcommand,sc.operation))
        
        # getCollection
        collName="Systems"
        rc,r,j,d=op.getCollection(sc,op, rft)
        if( rc != 0):  return(rc,r,False,None)
        #loop through the members and create the list sub-operation response
        rc,r,j,d=rft.listCollection(rft, r, d, prop="AssetTag")
        if(rc==0):
            rft.printVerbose(1," list {} Collection member info: Id, URI, AssetTag".format(collName,skip1=True, printV12=cmdTop))
        return(rc,r,j,d)

    
    def patch(self,sc,op,rft,cmdTop=False, prop=None, patchData=None, r=None):
        rft.printVerbose(4,"{}:{}: in operation".format(rft.subcommand,sc.operation))
        # verify we have got an argument which is the patch structure
        # its in form '{ "AssetTag": <val>, "IndicatorLed": <val> }'
        ##print("patchData: {}".format(patchData))
        if( len( sc.args) == 2):
            ##print("data:{}".format(sc.args[1]))
            try:
                patchData=json.loads(sc.args[1])
            except ValueError:
                rft.printErr("Patch: invalid Json input data:{}".format(sc.args[1]))
                return(5,None,False,None)
            ##print("patchData: {}".format(patchData))
        else:
            rft.printErr("Patch: error: invalid argument format")
            rft.printErr("     : args={}".format(sc.args))
            rft.printErr("     : expect: Systems patch \"{ <prop>: <value> }\"")
            return(4,None,False,None)

        # read the system resource
        # this is used by the generic rft.patchResource() function to see if there is an etag in the response
        # if an etag is in response hdr, then we must include the etag on the patch, so this get is required
        # note: the format of etag header for redfish is:  ETag: W/"<string>" or "<string"
        rc,r,j,d=op.get(sc,op,rft)
        if( rc != 0):
            return(rc,r,False,None)

        # now call the generic patch function to send the patch
        rc,r,j,d=rft.patchResource(rft, r, patchData)

        if(rc==0):   rft.printVerbose(1," Systems Patch:",skip1=True, printV12=cmdTop)
        return(rc,r,j,d)


    def reset(self,sc,op,rft,cmdTop=False, prop=None):
        # this operation has argument syntaxes below:
        #     ...reset <resetType>
        #   where <resetType> is a subset of Redfish defined redfish resetType values
        #   and will be validated against the allowable values read from the remote service
        rft.printVerbose(4,"{}:{}: in operation".format(rft.subcommand,sc.operation))
        
        # get the resetType from args
        validResetTypes=["On","ForceOff","GracefulShutdown","ForceRestart","Nmi","GracefulRestart",
                                    "ForceOn","PushPowerButton"]
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

        if( (j is True) and ("Actions" in d) and ("#ComputerSystem.Reset" in d["Actions"])):
            resetProps=d["Actions"]["#ComputerSystem.Reset"]
            if( "ResetType@Redfish.AllowableValues" in resetProps ):
                supportedResetTypes=resetProps["ResetType@Redfish.AllowableValues"]
                if not resetType in supportedResetTypes:
                    rft.printErr("Error, the resetType specified is not supported by the remote service")
                    return(8,None,False,None)
            else: # rhost didn't return any AllowableValues.  So this tool will not try to set it!
                rft.printErr("Error, the remote service doesnt have a resetType allowableValues prop")
                return(8,None,False,None)
        else:
            rft.printErr("Error, the remote service doesnt have an Actions: ComputerSystem.Reset property")
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
            rft.printVerbose(1," Systems reset: ", resetType, skip1=True, printV12=cmdTop)
            resetd=None
            return(rc,r,False,resetd)
        else: return(rc,r,False,None)


        
    def setAssetTag(self,sc,op,rft,cmdTop=False, prop=None):
        rft.printVerbose(4,"{}:{}: in operation".format(rft.subcommand,sc.operation))

        propName="AssetTag"
        
        # get the asset tag from args
        if(len(sc.args) < 2 ):
            rft.printErr("Error, no assetTag value specified")
            rft.printErr("Syntax:  {} [options] Systems setAssetTag \"string\" ".format(rft.program))
            return(8,None,False,None)
        assetTag=sc.args[1]
        patchData={propName: assetTag}
        
        # get the resource to verify it includes AssetTag,
        # the response will also be used by Patch() to check for etag 
        rc,r,j,d=op.get(sc,op,rft)
        if( rc != 0):  return(rc,r,False,None)
        if( not propName in d ):
            rft.printErr("System resource does not have a {} property.".format(propName))
            return(8,r,False,None)

        rc,r,j,d=rft.patchResource(rft, r, patchData)
        if(rc==0):
            rft.printVerbose(1," Systems setAssetTag:",skip1=True, printV12=cmdTop)
            assetTag={propName: d[propName]}
            return(rc,r,j,assetTag)         
        else: return(rc,r,False,None)


    def setIndicatorLed(self,sc,op,rft,cmdTop=False, prop=None):
        rft.printVerbose(4,"{}:{}: in operation".format(rft.subcommand,sc.operation))

        propName="IndicatorLED"
        
        # get the asset tag from args
        validLedStates=["Lit","Blinking","Off"]
        if(len(sc.args) < 2 ):
            rft.printErr("Error, no ledState value specified")
            rft.printErr("Syntax:  {} [options] Systems setIndicatorLed <Lit|Off|Blinking>".format(rft.program))
            return(8,None,False,None)
        targLedState=sc.args[1]
        if not targLedState in validLedStates:
            rft.printErr("Error, invalid LED state specified")
            return(8,None,False,None)
        patchData={propName: targLedState}
        
        # get the resource to verify it includes IndicatorLED,
        # the response will also be used by Patch() to check for etag 
        rc,r,j,d=op.get(sc,op,rft)
        if( rc != 0):  return(rc,r,False,None)
        if( not propName in d ):
            rft.PrintErr("System resource does not have a {} property.".format(propName))
            return(8,r,False,None)
        
        #ststststst   rc,r,j,d=op.patch(sc,op, rft, patchData=patchData, r=r)
        rc,r,j,d=rft.patchResource(rft, r, patchData)
        if(rc==0):
            rft.printVerbose(1," Systems setIndicatorLed:",skip1=True, printV12=cmdTop)
            ledState={"IndicatorLED": d["IndicatorLED"]}
            return(rc,r,j,ledState)
        else: return(rc,r,False,None)


    def setBootOverride(self,sc,op,rft,cmdTop=False, prop=None):
        # this operation has argument syntaxes below:
        #     ...setBootOverride <enabledVal> [<targetVal>]
        #       where <targetVal> is not required if enabledVal==Disabled
        #          ...setBootOverride Once       <targetVal>
        #          ...setBootOverride Continuous <targetVal>
        #          ...setBootOverride Disabled
        #   where TargetValue is subset of Redfish defined targets supported by rhost
        rft.printVerbose(4,"{}:{}: in operation".format(rft.subcommand,sc.operation))
        
        # get the next boot value from args
        validTargetVals=("None","Pxe","Floppy","Cd","Usb","Hdd",
                                    "BiosSetup","Utilities","Diags","UefiTarget")
        validEnabledVals=("Once","Disabled","Continuous")
        if(len(sc.args) < 2 ):
            rft.printErr("Error,  no bootSourceOverrideEnabled value specified")
            rft.printErr("Syntax: {} [options] Systems setBootOverride <enableVal> [<targetVal>]".format(rft.program))
            rft.printErr("        <enableVal>=Disabled|Once|Continuous, <targetVal>=None,Pxe,BiosSetup...")
            return(8,None,False,None)

        enabledVal=sc.args[1]
        if not enabledVal in  validEnabledVals:
            rft.printErr("Error, Invalid <Enabled> value specified: {}".format(enabledVal))
            rft.printErr("Syntax: {} [options] Systems setBootOverride <enableVal> [<targetVal>]".format(rft.program))
            rft.printErr("        <enableVal>=Disabled|Once|Continuous, <targetVal>=None,Pxe,BiosSetup...")
            return(8,None,False,None)
        
        #now read target,
        # we will need to check that the properteis we are patching are there, and chk for etag hdr
        #  and to see if the value specified is one of the allowable values for this rhost
        rc,r,j,d=op.get(sc,op,rft,prop="Boot")
        if(rc != 0):
            print("Error, cant read boot properties from remote service")
            return(8,None,False,None)
        
        # verify that they have a BootSourceOverrideEnabled  prop
        bootRes=d["Boot"]
        if( not "BootSourceOverrideEnabled" in bootRes ):
            rft.printErr("Error, the service does not have BootSourceOverrideEnabled property")
            return(8,None,False,None)

        if( enabledVal=="Disabled"):
            #just patch rhost to set OverrideEnabled=Disabled
            patchData={"Boot": {"BootSourceOverrideEnabled": enabledVal} }
            rc,r,j,d=rft.patchResource(rft, r, patchData)

        else:  # we are enabling bootOverride and also need to set the target
            if(len(sc.args) < 3):
                rft.printErr("Error, no bootSourceOverrideTarget specified")
                return(8,None,False,None)
            targetVal=sc.args[2]
            if not targetVal in validTargetVals:
                rft.printErr("Error, invalid BootSourceOverrideTarget value specified: {}".format(targetVal))
                rft.printErr("Syntax: {} [options] Systems setBootOverride <enableVal> [<targetVal>]".format(rft.program))
                rft.printErr("        <enableVal>=Disabled|Once|Continuous, <targetVal>=None,Pxe,BiosSetup...")
                return(8,None,False,None)

            if( (j is True) and ("Boot" in d) and ("BootSourceOverrideTarget@Redfish.AllowableValues" in d["Boot"])):
                rhostSupportedTargets=d["Boot"]["BootSourceOverrideTarget@Redfish.AllowableValues"]
                if not targetVal in rhostSupportedTargets:
                    rft.printErr("Error, the boot target specified is not supported by the remote service")
                    return(8,None,False,None)
            else: # rhost didn't return any AllowableValues.  So this tool will not try to set it!
                    rft.printErr("Error, the remote service doesnt have a Boot: BootSourceOverrideTarget allowableValues prop")
                    return(8,None,False,None)
                
            # verify that they have a BootSourceOverrideEnabled and BootSourceOverrideTarget prop
            if(  not "BootSourceOverrideTarget" in bootRes ):
                rft.printErr("Error, the service does not have oneOf BootSourceOverride..Enabled or ..Target property")
                return(8,None,False,None)
            
            #form the patch data
            patchData={"Boot": {"BootSourceOverrideEnabled": enabledVal, "BootSourceOverrideTarget": targetVal } }

            #call the generic patch command to send the patch.  This takes care of etag support
            rc,r,j,d=rft.patchResource(rft, r, patchData)
            
           
        if(rc==0):
            rft.printVerbose(1," Systems setBootOverride:",skip1=True, printV12=cmdTop)
            bootd={"Boot": d["Boot"]}
            return(rc,r,j,bootd)
        
        else: return(rc,r,False,None)


    def getProcessors(self,sc,op, rft, cmdTop=False, prop=None):
        rft.printVerbose(4,"{}:{}: in operation: getProcessorColl".format(rft.subcommand,sc.operation))

        # get the system resource
        rc,r,j,d=op.get(sc,op, rft)     
        if( rc != 0):  return(rc,r,False,None)
        
        collName="Processors"
        # get the link to the Processors collection
        if ((collName in d) and ("@odata.id" in d[collName])):
            procsLink=d[collName]["@odata.id"]
        else:
            rft.printErr("Error: computer system resource does not have a {} link".format(collName))
            return(6,None,False,None)
        
        if cmdTop is True:   prop=rft.prop

        # check if there is a list arg for the operation
        if( sc.argnum > 1 and sc.args[1] == 'list' ):
            #get the collection
            rc,r,j,d=rft.rftSendRecvRequest(rft.AUTHENTICATED_API, 'GET', r.url, relPath=procsLink)
            #loop through the members and create the list sub-operation response
            rc,r,j,d=rft.listCollection(rft, r, d, prop="Socket")
            if(rc==0):
                rft.printVerbose(1," list {} Collection member info: Id, URI, Socket".format(collName,skip1=True, printV12=cmdTop))

        # else: check if no proc was specified.  If not, return the collection
        elif(rft.IdLevel2OptnCount==0):
            rc,r,j,d=rft.rftSendRecvRequest(rft.AUTHENTICATED_API, 'GET', r.url, relPath=procsLink, prop=prop)
            if(rc==0):
                rft.printVerbose(1," {} Collection ".format(collName,skip1=True, printV12=cmdTop))

        # else:  check if the -a (all) option is set. If not, return the proc specific by -i or -m
        # search collection to find path using getPath2 
        elif( rft.allOptn is not True ):
            # get the processor collection
            rc,r,j,d=rft.rftSendRecvRequest(rft.AUTHENTICATED_API, 'GET', r.url, relPath=procsLink, prop=prop)
            collUrl=r.url

            # now search for 2nd level resource and return
            path2,rc,r,j,d=rft.getLevel2ResourceById(rft,r,d)
            if(rc!=0):
                return(rc,r,j,d)
            # so rc=0
            #if sysPath returned a response but we need to extract the property do it here
            if( (r is not None) and (prop is not None) ):
                rc,r,j,d=rft.getPropFromDict(rft,r,d,prop)

            # otherwise, we need to do a GET to get the processor, if -P show property, else show full response
            elif( r is None ):
                rc,r,j,d=rft.rftSendRecvRequest(rft.AUTHENTICATED_API, 'GET', collUrl, relPath=path2, prop=prop)
                if(rc==0):
                    rft.printVerbose(1," {} Collection Member ".format(collName,skip1=True, printV12=cmdTop))

        # else, return ALL of the processor members
        else:
            rft.printVerbose(4,"getting expanded Processor Collection")
            rc,r,j,d=rft.getAllCollectionMembers(rft, r.url, relPath=procsLink)
            if(rc==0):
                rft.printVerbose(1," Get ALL {} Collection Members".format(collName,skip1=True, printV12=cmdTop))
        
        return(rc,r,j,d)


    
    def getEnetInterfaces(self,sc,op,rft,cmdTop=False, prop=None):
        rft.printVerbose(4,"{}:{}: in operation".format(rft.subcommand,sc.operation))

        # get the system resource
        rc,r,j,d=op.get(sc,op, rft)     
        if( rc != 0):  return(rc,r,False,None)
        
        collName="EthernetInterfaces"
        # get the link to the EthernetInterfaces collection
        if ((collName in d) and ("@odata.id" in d[collName])):
            nicLink=d[collName]["@odata.id"]
        else:
            rft.printErr("Error: EthernetInterfaces resource does not have a {} link".format(collName))
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



    def getSimpleStorage(self,sc,op,rft,cmdTop=False, prop=None):
        rft.printVerbose(4,"{}:{}: in operation".format(rft.subcommand,sc.operation))

        # get the system resource
        rc,r,j,d=op.get(sc,op, rft)     
        if( rc != 0):  return(rc,r,False,None)
        
        collName="SimpleStorage"
        # get the link to the SimpleStorage collection
        if ((collName in d) and ("@odata.id" in d[collName])):
            cntlrLink=d[collName]["@odata.id"]
        else:
            rft.printErr("Error: computer system resource does not have a {} link".format(collName))
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

        # else: check if no SimpleStorage controller was specified.  If not, return the collection
        elif(rft.IdLevel2OptnCount==0):
            rc,r,j,d=rft.rftSendRecvRequest(rft.AUTHENTICATED_API, 'GET', r.url, relPath=cntlrLink, prop=prop)
            if(rc==0):
                rft.printVerbose(1," {} Collection ".format(collName,skip1=True, printV12=cmdTop))

        # else:  check if the -a (all) option is set. If not, return the proc specific by -i or -m
        # search collection to find path using getPath2 
        elif( rft.allOptn is not True ):
            # get the SimpleStorage collection
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

            # otherwise, we need to do a GET to get the SimpleStorage, if -P show property, else show full response
            elif( r is None ):
                rc,r,j,d=rft.rftSendRecvRequest(rft.AUTHENTICATED_API, 'GET', collUrl, relPath=path2, prop=prop)
                if(rc==0):
                    rft.printVerbose(1," {} Collection Member ".format(collName,skip1=True, printV12=cmdTop))

        # else, return ALL of the SimpleStorage members
        else:
            rft.printVerbose(4,"getting expanded SimpleStorage Collection")
            rc,r,j,d=rft.getAllCollectionMembers(rft, r.url, relPath=cntlrLink)
            if(rc==0):
                rft.printVerbose(1," Get ALL {} Collection Members".format(collName,skip1=True, printV12=cmdTop))
        
        return(rc,r,j,d)


    
    def getLogService(self,sc,op,rft,cmdTop=False, prop=None):
        rft.printVerbose(4,":{}:{}: in operation".format(rft.subcommand,sc.operation))

        # get the system resource
        rc,r,j,d=op.get(sc,op, rft)     
        if( rc != 0):  return(rc,r,False,None)
        
        collName="LogServices"
        # get the link to the LogServices collection
        if ((collName in d) and ("@odata.id" in d[collName])):
            logLink=d[collName]["@odata.id"]
        else:
            rft.printErr("Error: computer system resource does not have a {} link".format(collName))
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

        # else, client specified the -a option requesting ALL of the LogServices members
        # for logs, we will not support this.  Its too much data.
        else:
            rft.printErr("Error: -a option not supported for LogServices")
            return(6,None,False,None)
        
        return(rc,r,j,d)

    
    def clearLog(self,sc,op,rft,cmdTop=False, prop=None):
        rft.printVerbose(4,"{}:{}: in operation".format(rft.subcommand,sc.operation))
        return(8,None,False,None)

      
    def examples(self,sc,op,rft,cmdTop=False,prop=None):
        rft.printVerbose(4,"{}:{}: in operation".format(rft.subcommand,sc.operation))
        print(" {} -r<ip> Systems                          # shows the systems collection".format(rft.program))
        print(" {} -r<ip> Systems list                     # lists Id, Uri, AssetTag for all systems".format(rft.program))
        print(" {} -r<ip> Systems -I <id>                  # gets the system with Id=<d>".format(rft.program))
        print(" {} -r<ip> Systems -M AssetTag:12345        # gets the system with AssetTag=12345".format(rft.program))
        print(" {} -r<ip> Systems -L <sysUrl>              # gets the system at URI=<systemUrl".format(rft.program))
        print(" {} -r<ip> Systems -F                       # get the First system returned (for debug)".format(rft.program))
        print(" {} -r<ip> Systems -1                       # get the first system and verify that there is only one system".format(rft.program))
        print(" {} -r<ip> Systems -I <id> patch {{A: B,C: D,...}}     # patch the json-formatted {{prop: value...}} data to the object".format(rft.program))
        print(" {} -r<ip> Systems -I <id> reset <resetType>         # reset a system.  <resetType>=the redfish-defined values: On, Off, gracefulOff...".format(rft.program))
        print(" {} -r<ip> Systems -I <id> setAssetTag <assetTag>    # set the system's asset tag ".format(rft.program))
        print(" {} -r<ip> Systems -I <id> setIndicatorLed  <state>  # set the indicator LED.  <state>=redfish defined values: Off, Lit, Blinking".format(rft.program))
        print(" {} -r<ip> Systems -I <id> setBootOverride <enabledVal> <targetVal> #-- set Boot Override properties. <enabledVal>=Disabled|Once|Continuous".format(rft.program))
        print(" {} -r<ip> Systems -I<Id> Processors        # get the processors Collection".format(rft.program))
        print(" {} -r<ip> Systems -I<Id> Processors list   # lists Id, Uri, and Socket for all processors in system with Id=<Id>".format(rft.program))
        print(" {} -r<ip> Systems -I<Id> Processors -i 1   # get the processor with id=1 in system with Id=<Id>".format(rft.program))
        print(" {} -r<ip> Systems -L <sysUrl> Processors -m Socket:CPU_1  # get processor with property Socket=CPU_1, on system at url <sysUrl>".format(rft.program))
        return(0,None,False,None)



    
'''
TODO:
1. clearlog not implemented
2. handling segmented response to collections not tested (but code is there)

'''

    


