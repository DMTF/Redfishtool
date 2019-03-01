# Copyright Notice:
# Copyright 2019 DMTF. All rights reserved.
# License: BSD 3-Clause License. For full text see link: https://github.com/DMTF/Redfishtool/blob/master/LICENSE.md

# redfishtool: UpdateService.py
#
# contains UpdateService related subCommands and access functions
#
# Class RfUpdateServiceMain
#  - functions init, displayUsage, displayHelp, displayOperations,
#  - runOperation - UpdateService command table, dispatch of operation eg get
#  - UpdateServiceMain - called from redfishMain, enforce legal option combinations,
#    and call runOperation to run UpdateService operation (sub-sub-command)
#
# Class RfUpdateServiceOperations
#  All of the UpdateService sub-command operations eg:  get UpdateService
#  - hello - test cmd
#  - get - get the UpdatService
#  - examples --prints some example apis

from   .redfishtoolTransport  import RfTransport
import requests
import json
import getopt
import re
import sys
from    .ServiceRoot import RfServiceRoot
from   urllib.parse import urljoin

class RfUpdateServiceMain():
    def __init__(self):
        # operation string and remaining args
        self.operation=None
        self.args=None
        self.argnum=0
        self.nonIdCommands=None

    def displayUsage(self,rft):
        if(rft.quiet): return(0)
        print("  Usage:")
        print("   {} [OPTNS]  UpdateService  <operation> [<args>]  -- perform <operation> on the UpdateService  ".format(rft.program))

    def displayHelp(self,rft):
        self.displayUsage(rft)
        self.displayOperations(rft)
        print("")

    def displayOperations(self,rft):
        print("  <operations>:")
        print("     [get]                     -- get the UpdateService object. ")
        print("     examples                  -- example commands with syntax")
        print("     hello                     -- UpdateService hello -- debug command")
        return(0)

    def runOperation(self,rft):
        #  instantiate UpdatService class
        op=RfUpdateServiceOperations()

        #  dispatch table for each subcommand:   "cmdName": cmdClass.cmdFunction"
        operationTable = {
            "get":                          op.get,
            "hello":                        op.hello,
            "examples":                     op.examples
        }

        rft.printVerbose(5,"UpdateService:runOperation: operation: {}".format(self.operation))
        rft.printVerbose(5,"UpdateService:runOperation: args:  {}".format(self.args))

        if self.operation in operationTable:
            rft.printVerbose(5,"UpdateService:runOperation: found Oper: {} in table. executing".format(rft.subcommand))
            rc,r,j,d=operationTable[self.operation](self, op, rft, cmdTop=True)
            return(rc,r,j,d)

        else: # invalid operation
            rft.printErr("UpdateService: Invalid operation: {}".format(self.operation))
            return(2,None,False,None)



    def UpdateServiceMain(self,rft,cmdTop=False):
        rft.printVerbose(4,"UpdateServiceMain:  subcommand: {}".format(rft.subcommand))

        if( rft.help ):
            self.displayHelp(rft)
            return(0,None,False,None)

        args=rft.subcommandArgv[0:]

        #if no args, this is a getUpdateService command
        if(  len(args) < 2 ):
            self.operation="get"
            self.args= None
        else:
            self.operation=args[1]
            self.args = args[1:]        # now args points to the 1st argument
            self.argnum =len(self.args)

        rft.printVerbose(5,"UpdateService: operation={}, args={}".format(self.operation,self.args))

        # now execute the operation.
        rc,r,j,d = self.runOperation(rft)

        if(rc !=0 ):
            rft.printVerbose(5,"UpdateService: operation returned with error: rc={}".format(rc))
            return(rc,r,False,None)

        #else, if here, the subcommand executed without error.  Return with 0 exit code
        rft.printVerbose(5,"UpdateService: operation exited OK")
        return(rc,r,j,d)

#
# contains operations related to the UpdateService subCommand
#
class RfUpdateServiceOperations():
    def __init__(self):
        self.UpdateServicePath=None
        self.UpdateServiceCollectionDict=None


    def hello(self,sc,op,rft,cmdTop=False):
        rft.printVerbose(4,"in hello")
        rft.printVerbose(4,"   subcmd:{}, operation:{}, args:{}".format(rft.subcommand,sc.operation,sc.args))
        print("hello world from UpdateService")
        return(0,None,False,None)

    def get(self,sc,op,rft, cmdTop=False, prop=None):
        rft.printVerbose(4,"{}:{}: in operation".format(rft.subcommand,sc.operation))

        # 1st get serviceRoot
        svcRoot=RfServiceRoot()
        rc,r,j,d = svcRoot.getServiceRoot(rft)
        if( rc != 0 ):
            rft.printErr("get UpdateService: Error getting service root, aborting")
            return(rc,r,False,None)

        # get the link to the UpdateService
        # need to test we got good data
        if (("UpdateService" in d) and ("@odata.id" in d["UpdateService"])):
            UpdateServiceLink=d["UpdateService"]["@odata.id"]
        else:
            rft.printErr("Error:  root does not have a UpdateService link")
            return(4)

        rft.printVerbose(4,"UpdateService: get UpdateService: link is: {}".format(UpdateServiceLink))

        if cmdTop is True:   prop=rft.prop

        # do a GET to get the UpdateService, if -P show property, else show full response
        rc,r,j,d=rft.rftSendRecvRequest(rft.AUTHENTICATED_API, 'GET', r.url, relPath=UpdateServiceLink, prop=prop)

        if(rc==0):   rft.printVerbose(1," UpdateService Resource:",skip1=True, printV12=cmdTop)
        return(rc,r,j,d)

    def examples(self,sc,op,rft,cmdTop=False,prop=None):
        rft.printVerbose(4,"{}:{}: in operation".format(rft.subcommand,sc.operation))
        print(" {} -r<ip> UpdateService                          # gets the UpdateService".format(rft.program))
        return(0,None,False,None)
