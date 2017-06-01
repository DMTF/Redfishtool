# Copyright Notice:
# Copyright 2016 Distributed Management Task Force, Inc. All rights reserved.
# License: BSD 3-Clause License. For full text see link: https://github.com/DMTF/Redfishtool/LICENSE.md

# redfishtool: Chassis.py
#
# contains Chassis subCommands and access functions
#
# Class RfSystemsMain
#  - functions init, displayUsage, displayHelp, displayOperations,
#  - runOperation - Chassis command table, dispatch of operation eg get, reset
#  - ChassisMain - called from redfishMain, enforce legal option combinations,
#    and call runOperation to run Chassis operations (sub-sub-command)
#
# Class RfChassisOperations
#  All of the Chassis sub-command operations eg: get, setIndicatorLed, etc
#  - hello - test cmd
#  - getCollection - return the Chassis collection
#  - get - get a member of a collection -or property of the member
#  - list - show of list of collection members and key idetifying properties
#      (Id, AssetTag, UriPath)
#  - patch - raw subcommand to patch a Chassis Member, with etag support
#  - setAssetTag -- patches the assetTag of Chassis instance w/ etag support
#  - setIndicatorLed --sets id LED to a specified value w/ etag support
#  - getPower - get Processors collection, processor instance, or all
#  - getThermal - get Ethernet collection, instance, all
#  - setPowerLimit - Set the PowerLimit for a member of the powerControl array
#  - getPowerReading [consumed] - get the powerControl array, or ConsumedWatts from pwrCntl[0]
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

class RfChassisMain():
    def __init__(self):
        # operation string and remaining args
        self.operation=None
        self.args=None
        self.argnum=0
        self.nonIdCommands=None

    def displayUsage(self,rft):
        if(rft.quiet): return(0)
        print("  Usage:")
        print("   {} [OPTNS]  Chassis  <operation> [<args>]  -- perform <operation> on the Chassis specified ".format(rft.program))

    def displayHelp(self,rft):
        self.displayUsage(rft)
        self.displayOperations(rft)
        print(" ")

    def displayOperations(self,rft):
        print("  <operations>:")
        print("     [collection]              -- get the main Chassis collection. (Default operation if no member specified)")
        print("     [get]                     -- get the Chassis object. (Default operation if collection member specified)")
        print("     list                      -- list information about the Chassis collection members(\"Id\", URI, and AssetTag)")
        print("     patch {A: B,C: D,...}     -- patch the json-formatted {prop: value...} data to the object")
        print("     setAssetTag <assetTag>    -- set the Chassis's asset tag ")
        print("     setIndicatorLed  <state>  -- set the indicator LED.  <state>=redfish defined values: Off, Lit, Blinking")
        print("     Power                     -- get the full Power resource under a specified Chassis instance.")
        print("     Thermal                   -- get the full Thermal resource under a specified Chassis instance.")
        print("")
        print("     getPowerReading [-i<indx>] [consumed]-- get powerControl resource w/ power capacity, PowerConsumed, and power limits")
        print("                                  if \"consumed\" keyword is added, then only current usage of powerControl[indx] is returned")
        print("                                  <indx> is the powerControl array index. default is 0.  normally, 0 is the only entry")
        print("     setPowerLimit [-i<indx>] <limit> [<exception> [<correctionTime>]] -- set powerLimit control properties")
        print("                               <limit>=null disables power limiting. <indx> is the powerControl array indx (dflt=0)")
        print("")
        print("     Logs [list]               -- get the Chassis \"LogServices\" collection , or list \"id\" and URI of members.")
        print("      Logs [IDOPTN]              --  get the member specified by IDOPTN: -i<id>, -m<prop>:<val>, -l<link>, -a #all")
        print("     clearLog   <id>           -- clears the log defined by <id>")
        print("     examples                  -- example commands with syntax")
        print("     hello                     -- Chassis hello -- debug command")
        return(0)



    def runOperation(self,rft):
        #  instantiate ChassisOperations class
        op=RfChassisOperations()
        
        #  dispatch table for each subcommand:   "cmdName": cmdClass.cmdFunction"
        operationTable = {
            "collection":                   op.getCollection,
            "get":                          op.get,
            "list":                         op.clist,
            "patch":                        op.patch,
            "setAssetTag":                  op.setAssetTag,
            "setIndicatorLed":              op.setIndicatorLed,
            "Power":                        op.getPower,
            "Thermal":                      op.getThermal,
            "setPowerLimit":                op.setPowerLimit,
            "getPowerReading":              op.getPowerReading,
            "Logs":                         op.getLogService,
            "-clearLog":                     op.clearLog,
            "hello":                        op.hello,
            "examples":                     op.examples
        }

        rft.printVerbose(5,"Chassis:runOperation: operation: {}".format(self.operation))
        rft.printVerbose(5,"Chassis:runOperation: args:  {}".format(self.args))
            
        if self.operation in operationTable:
            rft.printVerbose(5,"Chassis:runOperation: found Oper: {} in table. executing".format(rft.subcommand))
            rc,r,j,d=operationTable[self.operation](self, op, rft, cmdTop=True)
            return(rc,r,j,d)
        
        else: # invalid operation
            rft.printErr("Chassis: Invalid operation: {}".format(self.operation))
            return(2,None,False,None)
        


    def ChassisMain(self,rft,cmdTop=False):
        rft.printVerbose(4,"ChassisMain:  subcommand: {}".format(rft.subcommand))
        
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
            
        rft.printVerbose(5,"Chassis: operation={}, args={}".format(self.operation,self.args))
                
        # check if the command requires a collection member target -I|-M|-L|-1|-F eg sysIdoptn
        nonIdCommands=["collection", "list", "examples", "hello"]
        if( ( not self.operation in nonIdCommands ) and (rft.IdOptnCount==0) ):
            rft.printErr("Chassis: Syntax error: [-I|-M|-L|-F|-1] required for action that targets a specific Chassis instance")
            return(0,None,False,None)
            
        # now execute the operation.
        rc,r,j,d = self.runOperation(rft)
                
        if(rc !=0 ):
            rft.printVerbose(5,"Chassis: operation returned with error: rc={}".format(rc))
            return(rc,r,False,None)
        
        #else, if here, the subcommand executed without error.  Return with 0 exit code
        rft.printVerbose(5,"Chassis: operation exited OK")
        return(rc,r,j,d)


#
# contains operations related to the Chassis subCommand
#
class RfChassisOperations():
    def __init__(self):
        self.chassisPath=None
        self.chassisCollectionDict=None


    def hello(self,sc,op,rft,cmdTop=False):
        rft.printVerbose(4,"in hello")
        rft.printVerbose(4,"   subcmd:{}, operation:{}, args:{}".format(rft.subcommand,sc.operation,sc.args))
        print("hello world from Chassis")
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
        if (("Chassis" in d) and ("@odata.id" in d["Chassis"])):
            systemsLink=d["Chassis"]["@odata.id"]
        else:
            rft.printErr("Error: service root does not have a Chassis link")
            return(4)
        
        rft.printVerbose(4,"Chassis:getCollection: link is: {}".format(systemsLink))


        # if a -a option was entered with "Chassis" or "Chassis collection" operation,
        # then return all members of the Chassis collection expanded
        if((cmdTop is True) and (rft.allOptn is True) ):
            collName="Chassis"
            rft.printVerbose(4,"Expand Chassis collection to return ALL Chassis collection members fully expanded in response")
            rc,r,j,d=rft.getAllCollectionMembers(rft, r.url, relPath=systemsLink)
            if(rc==0):
                rft.printVerbose(1," Get ALL {} Collection Members".format(collName,skip1=True, printV12=cmdTop))

        # otherwise, just return the collection
        # now read the /Chassis collection
        # use the returned url as the base url to read the Chassis collection
        else:
            if cmdTop is True:   prop=rft.prop
            rc,r,j,d=rft.rftSendRecvRequest(rft.AUTHENTICATED_API, 'GET', r.url, relPath=systemsLink, prop=prop)
            if(rc==0):
                rft.printVerbose(1," Chassis Collection:",skip1=True, printV12=cmdTop)
                
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
        
        rft.printVerbose(4,"ChassisOperations:get: got a path, now get entries")
        
        if cmdTop is True:   prop=rft.prop

        #if here, rc=0
        #if sysPath returned a response but we need to extract the property do it here
        if( (r is not None) and (prop is not None) ):
            rc,r,j,d=rft.getPropFromDict(rft,r,d,prop)
                
        # otherwise, we need to do a GET to get the Chassis, if -P show property, else show full response
        elif( r is None ):
            rc,r,j,d=rft.rftSendRecvRequest(rft.AUTHENTICATED_API, 'GET', collUrl, relPath=sysPath, prop=prop)

        if(rc==0):   rft.printVerbose(1," Chassis Resource:",skip1=True, printV12=cmdTop)
        return(rc,r,j,d)


    def clist(self,sc,op,rft, cmdTop=False, prop=None):
        rft.printVerbose(4,"{}:{}: in operation".format(rft.subcommand,sc.operation))
        
        # getCollection
        collName="Chassis"
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

        # read the Chassis resource
        # this is used by the generic rft.patchResource() function to see if there is an etag in the response
        # if an etag is in response hdr, then we must include the etag on the patch, so this get is required
        # note: the format of etag header for redfish is:  ETag: W/"<string>" or "<string"
        rc,r,j,d=op.get(sc,op,rft)
        if( rc != 0):
            return(rc,r,False,None)

        # now call the generic patch function to send the patch
        rc,r,j,d=rft.patchResource(rft, r, patchData)

        if(rc==0):   rft.printVerbose(1," Chassis Patch:",skip1=True, printV12=cmdTop)
        return(rc,r,j,d)


        
    def setAssetTag(self,sc,op,rft,cmdTop=False, prop=None):
        rft.printVerbose(4,"{}:{}: in operation".format(rft.subcommand,sc.operation))

        propName="AssetTag"
        
        # get the asset tag from args
        if(len(sc.args) < 2 ):
            rft.printErr("Error, no assetTag value specified")
            rft.printErr("Syntax:  {} [options] Chassis setAssetTag \"string\" ".format(rft.program))
            return(8,None,False,None)
        assetTag=sc.args[1]
        patchData={propName: assetTag}
        
        # get the resource to verify it includes AssetTag,
        # the response will also be used by Patch() to check for etag 
        rc,r,j,d=op.get(sc,op,rft)
        if( rc != 0):  return(rc,r,False,None)
        if( not propName in d ):
            rft.printErr("Chassis resource does not have a {} property.".format(propName))
            return(8,r,False,None)

        rc,r,j,d=rft.patchResource(rft, r, patchData)
        if(rc==0):
            rft.printVerbose(1," Chassis setAssetTag:",skip1=True, printV12=cmdTop)
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
            rft.printErr("Syntax:  {} [options] Chassis setIndicatorLed <Lit|Off|Blinking>".format(rft.program))
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
        
        rc,r,j,d=rft.patchResource(rft, r, patchData)
        if(rc==0):
            rft.printVerbose(1," Chassis setIndicatorLed:",skip1=True, printV12=cmdTop)
            ledState={"IndicatorLED": d["IndicatorLED"]}
            return(rc,r,j,ledState)
        else: return(rc,r,False,None)



    def getPower(self,sc,op, rft, cmdTop=False, prop=None):
        rft.printVerbose(4,"{}:{}: in operation".format(rft.subcommand,sc.operation))

        # get the Chassis resource first
        rc,r,j,d=op.get(sc,op, rft)     
        if( rc != 0):  return(rc,r,False,None)
        
        resName="Power"
        # get the link to the Power resource under Chassis
        if ((resName in d) and ("@odata.id" in d[resName])):
            resLink=d[resName]["@odata.id"]
        else:
            rft.printErr("Error: Chassis resource does not have a {} link".format(resName))
            return(6,None,False,None)
        
        if cmdTop is True:   prop=rft.prop

        rc,r,j,d=rft.rftSendRecvRequest(rft.AUTHENTICATED_API, 'GET', r.url, relPath=resLink, prop=prop)
        if(rc==0):
            rft.printVerbose(1," {} Resource ".format(resName,skip1=True, printV12=cmdTop))

        return(rc,r,j,d)



    def getThermal(self,sc,op,rft,cmdTop=False, prop=None):
        rft.printVerbose(4,"{}:{}: in operation".format(rft.subcommand,sc.operation))

        # get the Chassis resource first
        rc,r,j,d=op.get(sc,op, rft)     
        if( rc != 0):  return(rc,r,False,None)
        
        resName="Thermal"
        # get the link to the Thermal resource under Chassis
        if ((resName in d) and ("@odata.id" in d[resName])):
            resLink=d[resName]["@odata.id"]
        else:
            rft.printErr("Error: Chassis resource does not have a {} link".format(resName))
            return(6,None,False,None)
        
        if cmdTop is True:   prop=rft.prop
        
        rc,r,j,d=rft.rftSendRecvRequest(rft.AUTHENTICATED_API, 'GET', r.url, relPath=resLink, prop=prop)
        if(rc==0):
            rft.printVerbose(1," {} Resource ".format(resName,skip1=True, printV12=cmdTop))
            
        return(rc,r,j,d)



    def getPowerReading(self,sc,op,rft,cmdTop=False, prop=None):
        rft.printVerbose(4,"{}:{}: in operation".format(rft.subcommand,sc.operation))
                         
        if cmdTop is True:  prop=rft.prop

        # check if there is an arg for the operation
        if( sc.argnum > 1 ):
            if( sc.args[1] == 'consumed' ):
                prop="PowerConsumedWatts"
            else:
                rft.printErr("Error:  getPowerReading: invalid argument: {}".format(sc.args[1]))
                rft.printErr("Syntax: getPowerReading [-i<indx>] [consumed]")
                return(4,None,False,None)
            
        # get the Chassis Power resource
        rc,r,j,d=op.getPower(sc,op, rft)     
        if( rc != 0):  return(rc,r,False,None)
        
        # get the Power Control Object
        if ("PowerControl" in d ):
            powerControl=d["PowerControl"]
            powerControlMembers=len(powerControl)
        else:
            rft.printErr("Error: Chassis resource does not have a PowerControl resource")
            return(4,None,False,None)
        if(powerControlMembers == 0 ):
            rft.printErr("Error: Chassis PowerControl array is empty")
            return(4,None,False,None)

        # get the powerControl array index
        if( rft.IdLevel2 is None ):
            indx=0
        else:
            indxPattern="(^0$)|(^([1-9][0-9]{,2})$)"   #  <decimal>: 33...
            indxMatch=re.search(indxPattern,rft.IdLevel2)
            if( indxMatch ):
                indx=int(rft.IdLevel2)  # convert base10 to integer
                rft.printVerbose(4,"getPowerReading: Indx={}".format(indx))
            else:
                rft.printErr("Error: getPowerReading: invalid PowerControl index value: {}".format(rft.IdLevel2))
                rft.printErr("Chassis getPowerReading [current] [-i<indx>] --<indx> is integer 0 - 99 (default is 0)")
                         
            if( (indx+1) > powerControlMembers ):
                rft.printErr("Error: specified PowerControl index does not exist: indx={}, members={}".format(indx,powerControlMembers))
                return(4,None,False,None)
                        
        #if here, we have a valid indx
        if(prop is not None):
            if( prop in powerControl[indx] ):
                respDataVal=powerControl[indx][prop]
                respData={prop: respDataVal}
                rft.printVerbose(1," Get Current Power consumption (PowerConsumedWatts) of PowerControl[{}] resource".format(indx,skip1=True, printV12=cmdTop))
            else:
                rft.printErr("Error: Property {} not not returned in PowerControl[{}] resource".format(prop,indx))
                return(4,r,j,d)
        else:
            respData=powerControl[indx]  #return the full powerControl array
            rft.printVerbose(1," Chassis PowerControl[{}] array:".format(indx,skip1=True, printV12=cmdTop))
        
        return(rc,r,j,respData)




    #setPowerLimit [-i<indx>] <limit> [<exception> [<correctionTime>]] -- set powerLimit control properties")
    def setPowerLimit(self,sc,op,rft,cmdTop=False, prop=None):
        rft.printVerbose(4,"{}:{}: in operation".format(rft.subcommand,sc.operation))
                         
        if cmdTop is True:  prop=rft.prop

        # check if there is a required 2nd arg <limit> 
        if( sc.argnum > 1 ):
            limitPattern="(^null$)|(^0$)|(^([1-9][0-9]{,5})$)"   #  null | 0 | 8 | 33 |344 | 34333
            limitMatch=re.search(limitPattern,sc.args[1])  # sc.args[1]=<limit>
            if( limitMatch ):
                if(sc.args[1] == "null"):
                    limit=None
                else:
                    limit=int(sc.args[1])  # keep it a string
                rft.printVerbose(4,"setPowerLimit: limit={}".format(limit))
                powerLimitData={"LimitInWatts": limit }
            else:
                rft.printErr("Error: setPowerLimit: invalid <limit> value specified: {}".format(sc.args[1]))
                rft.printErr("Chassis setPowerLimit [-i<indx>] <limit> [<exception> [<correctionTime>]] --limit=null | 0-99999")
                return(8,None,False,None)
        else:
            rft.printErr("Error: setPowerLimit: no <limit> value specified: {}")
            rft.printErr("Chassis setPowerLimit [-i<indx>] <limit> [<exception> [<correctionTime>]] --limit=null | 0-99999")
            return(8,None,False,None)
        # check if there is an optional 3rd arg <exception>
        includeException=False
        validExceptionVals=("NoAction", "HardPowerOff", "LogEventOnly", "Oem")
        if (sc.argnum > 2 ):
            exceptionVal=sc.args[2] # sc.args[2]=<exceptionEnum>
            if( not exceptionVal in validExceptionVals ):
                rft.printErr("Error: setPowerLimit: invalid <limit> value specified: {}".format(sc.args[2]))
                rft.printErr("Chassis setPowerLimit [-i<indx>] <limit> [<exception> [<correctionTime>]] --limit=null | 0-99999")
                return(8,None,False,None)
            else:
                rft.printVerbose(4,"setPowerLimit: exception={}".format(exceptionVal))
                powerLimitData["LimitException"]=exceptionVal
                includeException=True
                         
        # check if there is an optional 4th arg <correctionTime> in miliseconds
        includeCorrectionTime=False
        if (sc.argnum > 3 ):
            correctionPattern="(^([1-9][0-9]{,6})$)"   #  1-999999 ms
            correctionMatch=re.search(correctionPattern,sc.args[3])  # sc.args[3]=<correctionInMs>
            if( correctionMatch ):
                correctionTime=int(sc.args[3])  # keep it a string
                rft.printVerbose(4,"setPowerLimit: correctionInMs={}".format(correctionTime))
                powerLimitData["CorrectionInMs"]=correctionTime 
                includeCorrectionTime=True
            else:
                rft.printErr("Error: setPowerLimit: invalid <correctionTime> value specified: {}".format(sc.args[3]))
                rft.printErr("Chassis setPowerLimit [-i<indx>] <limit> [<exception> [<correctionTime>]] --correctionTime=1-999999 ms")
                return(8,None,False,None)
                         
        # get the Chassis Power resource
        rc,r,j,d=op.getPower(sc,op, rft)     
        if( rc != 0):  return(rc,r,False,None)

        # get the Power Control Object
        if ("PowerControl" in d ):
            powerControl=d["PowerControl"]
            powerControlMembers=len(powerControl)
        else:
            rft.printErr("Error: Chassis resource does not have a PowerControl resource")
            return(4,None,False,None)
        if(powerControlMembers == 0 ):
            rft.printErr("Error: Chassis PowerControl array is empty")
            return(4,None,False,None)

        # get the powerControl array index
        if( rft.IdLevel2 is None ):
            indx=0
        else:
            indxPattern="(^0$)|(^([1-9][0-9]*)$)"   #  <decimal>: 33...
            indxMatch=re.search(indxPattern,rft.IdLevel2)
            if( indxMatch ):
                indx=int(rft.IdLevel2)  # convert base10 to integer
                rft.printVerbose(4,"setPowerLimit: Indx={}".format(indx))
            else:
                rft.printErr("Error: setPowerLimit: invalid PowerControl index: {}".format(rft.IdLevel2))
                rft.printErr("Chassis setPowerLimit [current] [-i<indx>] --<indx> is integer 0 - 99 (default is 0)")
                return(8,None,False,None)

            if( (indx+1) > powerControlMembers ):
                rft.printErr("Error: specified PowerControl index does not exist: indx={}, members={}".format(indx,powerControlMembers))
                return(8,None,False,None)

        # check that this PowerControl index member has the properties
        if( not "LimitInWatts" in powerControl[indx]["PowerLimit"] ):
            rft.printErr("Error: setPowerLimit: LimitInWatts property is not in rhost PowerControl[{}]".format(indx))
            return(8,None,False,None)
        if( ( includeException is True ) and ( not "LimitException" in powerControl[indx]["PowerLimit"] ) ):
            rft.printErr("Error: setPowerLimit: LimitException property is not in rhost PowerControl[{}]".format(indx))
            return(8,None,False,None)
        if( ( includeCorrectionTime is True ) and ( not "CorrectionInMs" in powerControl[indx]["PowerLimit"] ) ):
            rft.printErr("Error: setPowerLimit: CorrectionInMs property is not in rhost PowerControl[{}]".format(indx))
            return(8,None,False,None)

        # now build the final full patch data
        #patchData={"PowerControl"[indx]: { "PowerLimit":  powerLimitData } }
        powerLimitRes={ "PowerLimit": powerLimitData }
        patchData={ "PowerControl": [ {} ] }
        empty={}
        powerControlArray=list()
        for i in range (0,powerControlMembers):
            powerControlArray.append(empty)
        powerControlArray[indx]=powerLimitRes
        patchData["PowerControl"]=powerControlArray
        
        rft.printVerbose(4,"setPowerLimit: patchData: {}".format(json.dumps(patchData)))

        #call the generic patch command to send the patch.  This takes care of etag support
        rc,r,j,d=rft.patchResource(rft, r, patchData)

        if(rc==0):
            rft.printVerbose(1,"  SetPowerLimit [{}]:",indx, skip1=True, printV12=cmdTop)
            powerLimit={"PowerLimit": d["PowerControl"][indx]["PowerLimit"]}
            return(rc,r,j,powerLimit)
            
        else: return(rc,r,False,None)



    
    def getLogService(self,sc,op,rft,cmdTop=False, prop=None):
        rft.printVerbose(4,":{}:{}: in operation".format(rft.subcommand,sc.operation))

        # get the Chassis resource
        rc,r,j,d=op.get(sc,op, rft)     
        if( rc != 0):  return(rc,r,False,None)
        
        collName="LogServices"
        # get the link to the LogServices collection
        if ((collName in d) and ("@odata.id" in d[collName])):
            logLink=d[collName]["@odata.id"]
        else:
            rft.printErr("Error: Chassis resource does not have a {} link".format(collName))
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
        print(" {} -r<ip> Chassis                          # shows the Chassis collection".format(rft.program))
        print(" {} -r<ip> Chassis list                     # lists Id, Uri, AssetTag for all Chassis".format(rft.program))
        print(" {} -r<ip> Chassis -I <id>                  # gets the Chassis with Id=<d>".format(rft.program))
        print(" {} -r<ip> Chassis -M AssetTag:12345        # gets the Chassis with AssetTag=12345".format(rft.program))
        print(" {} -r<ip> Chassis -L <sysUrl>              # gets the Chassis at URI=<systemUrl".format(rft.program))
        print(" {} -r<ip> Chassis -F                       # get the First Chassis returned (for debug)".format(rft.program))
        print(" {} -r<ip> Chassis -1                       # get the first Chassis and verify that there is only one system".format(rft.program))
        print(" {} -r<ip> Chassis -I <id> patch {{A: B,C: D,...}}     # patch the json-formatted {{prop: value...}} data to the object".format(rft.program))
        print(" {} -r<ip> Chassis -I <id> setAssetTag <assetTag>    # set the system's asset tag ".format(rft.program))
        print(" {} -r<ip> Chassis -I <id> setIndicatorLed  <state>  # set the indicator LED.  <state>=redfish defined values: Off, Lit, Blinking".format(rft.program))
        print(" {} -r<ip> Chassis -I<Id> Power             # get the full chassis Power resource".format(rft.program))
        print(" {} -r<ip> Chassis -I<Id> Thermal           # get the full chassis Thermal resource".format(rft.program))
        print(" {} -r<ip> Chassis -I<Id> getPowerReading[-i<indx> [consumed]   # get chassis/Power powerControl[<indx>] resource".format(rft.program))
        print("                                             # if optional \"consumed\" arg, then return only the PowerConsumedWatts prop")
        print(" {} -r<ip> Chassis -L<Url> setPowerLimit [-i<indx>] <limit> [<exception> [<correctionTime>]] # set power limit".format(rft.program))
        return(0,None,False,None)



    
'''
TODO:
1. clearlog not implemented

'''

    


