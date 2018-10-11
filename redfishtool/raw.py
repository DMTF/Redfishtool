# Copyright Notice:
# Copyright 2016 DMTF. All rights reserved.
# License: BSD 3-Clause License. For full text see link: https://github.com/DMTF/Redfishtool/blob/master/LICENSE.md

# redfishtool: rawMain.py
#
# contains raw subCommands and access functions
#
# Class RfRawMain
#  - functions init, displayUsage, displayHelp, displayOperations,
#  - runOperation - raw subcommand table, dispatch of operations: get, patch, post..
#  - RfRawMain - called from redfishMain, enforce legal option combinations,
#    and call runOperation to run System operation (sub-sub-command)
#
# Class RfRawOperations
#  All of the Systems sub-command operations eg: Systems reset, setIndicatorLed, etc
#  - hello - test cmd
#  - httpGet    -- send GET method 
#  - httpPatch  -- send GET method
#  - httpPost   -- send GET method
#  - httpDelete -- send GET method
#  - httpHead   -- send GET method
#  - httpPut    -- send GET method  (not implemented in 0.9)
#  - examples --prints some example apis
#
from   .redfishtoolTransport  import RfTransport
import requests
import json
import getopt
import re
import sys
#from    .ServiceRoot import RfServiceRoot
from   urllib.parse import urljoin, urlparse, urlunparse

class RfRawMain():
    def __init__(self):
        # operation string and remaining args
        self.operation=None
        self.args=None
        self.argnum=0
        self.nonIdCommands=None

    def displayUsage(self,rft):
        if(rft.quiet): return(0)
        print("  Usage:")
        print("   {} [OPTNS] raw <method> <path> ".format(rft.program))
        print("")
        print("   {} raw -h        # for help".format(rft.program))
        print("   {} raw examples  #for example commands".format(rft.program))
        print("")
        print("  <method> is one of:  GET, PATCH, POST, DELETE, HEAD, PUT")
        print("  <path> is full URI path to a redfish resource--the full path following <ipaddr:port>, starting with forward slash /")
        print("")
        print("   Common OPTNS:")
        print("   -u <user>,   --user=<usernm>     -- username used for remote redfish authentication")
        print("   -p <passwd>, --password=<passwd> -- password used for remote redfish authentication")
        print("   -t <token>,  --token=<token>    - redfish auth session token-for sessions across multiple calls")
        print("")
        print("   -r <rhost>,  --rhost=<rhost>     -- remote redfish service hostname or IP:port")
        print("   -X <method>  --request=<method>  -- the http method to use. <method>={GET,PATCH,POST,DELETE,HEAD,PUT}. Default=GET")
        print("   -d <data>    --data=<data>       -- the http request \"data\" to send on PATCH,POST,or PUT requests")
        print("   -H <hdrs>, --Headers=<hdrs>      -- Specify the request header list--overrides defaults. Format \"{ A:B, C:D...}\" ")
        print("   -S <Secure>,  --Secure=<Secure>  -- When to use https: (Note: doesn't stop rhost from redirect http to https)")

        
    def displayHelp(self,rft):
        self.displayUsage(rft)
        self.displayOperations(rft)
        print("")
        
    def displayOperations(self,rft):
        print("  <operations / methods>:")
        print("     GET             -- HTTP GET method")
        print("     PATCH           -- HTTP PATCH method")
        print("     POST            -- HTTP POST method")
        print("     DELETE          -- HTTP DELETE method")
        print("     HEAD            -- HTTP HEAD method")
        print("     PUT             -- HTTP PUT method")
        print("   examples        -- example raw commands with syntax")
        print("   hello           -- raw hello -- debug command")
        return(0)


    def runOperation(self,rft):
        #  instantiate SystemsOperations class
        op=RfRawOperations()
        
        #  dispatch table for each subcommand:   "cmdName": cmdClass.cmdFunction"
        operationTable = {
            "GET":                  op.httpGet,
            "PATCH":                op.httpPatch,
            "POST":                 op.httpPost,
            "DELETE":               op.httpDelete,
            "HEAD":                 op.httpHead,
            "PUT":                  op.httpPut,
            "hello":                op.hello,
            "examples":             op.examples
        }

        rft.printVerbose(5,"raw: runOperation: operation: {}".format(self.operation))
        rft.printVerbose(5,"raw:runOperation:  args:  {}".format(self.args))
            
        if self.operation in operationTable:
            rft.printVerbose(5,"raw:runOperation: found Oper: {} in table. executing".format(rft.subcommand))
            rc,r,j,d=operationTable[self.operation](self, op, rft, cmdTop=True)
            return(rc,r,j,d)
        
        else: # invalid operation
            rft.printErr("raw: Invalid operation: {}".format(self.operation))
            return(2,None,False,None)
        


    def RawMain(self,rft,cmdTop=False):
        rft.printVerbose(4,"RawMain:  subcommand: {}".format(rft.subcommand))
        
        if( rft.help ):
            self.displayHelp(rft)
            return(2,None,False,None)
        
        args=rft.subcommandArgv[0:]
        
        # if 2 args, only operations are: hello and examples
        nonMethodOperations=("hello","examples")
        if( len(args)==2):
            nonMethodOp=args[1]
            if( not nonMethodOp in nonMethodOperations):
                rft.printErr("Syntax error: \"raw\" subcommands require 2 arguments\n")
                rft.printErr("")
                self.displayHelp(rft)
                return(2,None,False,None)
        # else all operations require two args <method> <path>
        elif(  len(args) < 3 ):
                    rft.printErr("Syntax error: \"raw\" subcommands require 2 arguments\n")
                    self.displayHelp(rft)
                    return(2,None,False,None)
        
        self.operation=args[1]      # for raw subcommand, this is the http method (eg GET)
        self.args = args[1:]        # now args points to the 1st argument
        self.argnum =len(self.args)
            
        rft.printVerbose(5,"raw: operation={}, args={}".format(self.operation,self.args))
                
           
        # now execute the operation.
        rc,r,j,d = self.runOperation(rft)
                
        if(rc !=0 ):
            rft.printVerbose(5,"raw: operation returned with error: rc={}".format(rc))
            return(rc,r,False,None)
        
        #else, if here, the subcommand executed without error.  Return with 0 exit code
        rft.printVerbose(5,"raw: operation exited OK")
        return(rc,r,j,d)


#
# contains operations related to the Systems subCommand
#
class RfRawOperations():
    def __init__(self):
        self.systemsPath=None
        self.systemsCollectionDict=None

    # function to return API type: authenticated or unauthenticated
    # authenticated APIs require authentication
    # unauthenticated APIs are /redfish, /redfish/v1, /redfish/v1/odata, /redfish/v1/$metadata
    def getApiType(self,rft,uri):
        unauthenticatedAPIs=("/redfish", "/redfish/v1", "/redfish/v1/", "/redfish/v1/odata", "/redfish/v1/$metadata")
        if not uri in unauthenticatedAPIs:
            return( rft.AUTHENTICATED_API )
        else:
            return( rft.UNAUTHENTICATED_API )

                             
    def hello(self,sc,op,rft,cmdTop=False):
        rft.printVerbose(4,"in hello")
        rft.printVerbose(4,"   subcmd:{}, operation:{}, args:{}".format(rft.subcommand,sc.operation,sc.args))
        print("hello world from raw subcommand")
        return(0,None,False,None)

    
    def httpGet(self,sc,op,rft,cmdTop=False, prop=None):
        rft.printVerbose(4,"{}:{}: in raw".format(rft.subcommand,sc.operation))
        
        # we verified that we had two args in RawMain(), so we can just read the <uri> arg here
        path=sc.args[1]
        method="GET"
        rft.printVerbose(4,"raw: GET: method:{} path:{}".format(method,path))

        apiType=self.getApiType(rft,path)   # UNAUTHENTICATED API or Authenticated API

        # calculate rootUrl--with correct scheme, root path, and rhost IP (w/o querying rhost)
        scheme=rft.getApiScheme(apiType)
        scheme_tuple=[scheme, rft.rhost, "/redfish", "","",""]
        rootUrl=urlunparse(scheme_tuple)  # so rootUrl="http[s]://<rhost>[:<port>]/redfish"
        
        if cmdTop is True:   prop=rft.prop
        jsonData=True
        if (path=="/redfish/v1/$metadata"): jsonData=False
        rc,r,j,d=rft.rftSendRecvRequest(apiType, method, rootUrl, relPath=path, prop=prop,jsonData=jsonData)
        if(rc==0):
            rft.printVerbose(1," raw GET:",skip1=True, printV12=cmdTop)  
            return(rc,r,j,d)
        else:
            rft.printErr("raw: Error getting response")
            return(rc,r,False,None)

    def httpHead(self,sc,op,rft,cmdTop=False, prop=None):
        rft.printVerbose(4,"{}:{}: in raw".format(rft.subcommand,sc.operation))
        
        # we verified that we had two args in RawMain(), so we can just read the <uri> arg here
        path=sc.args[1]
        method="HEAD"
        rft.printVerbose(4,"raw: HEAD: method:{} path:{}".format(method,path))

        apiType=self.getApiType(rft,path)   # UNAUTHENTICATED API or Authenticated API
        
        # calculate rootUrl--with correct scheme, root path, and rhost IP (w/o querying rhost)
        scheme=rft.getApiScheme(apiType)
        scheme_tuple=[scheme, rft.rhost, "/redfish", "","",""]
        rootUrl=urlunparse(scheme_tuple)  # so rootUrl="http[s]://<rhost>[:<port>]/redfish"
        
        rc,r,j,d=rft.rftSendRecvRequest(apiType, method, rootUrl, relPath=path)
        if(rc==0):
            rft.printVerbose(1," raw HEAD:",skip1=True, printV12=cmdTop)  
            return(rc,r,False,None)
        else:
            rft.printErr("raw: Error getting response")
            return(rc,r,False,None)


    

    def httpPatch(self,sc,op,rft,cmdTop=False, prop=None):
        rft.printVerbose(4,"{}:{}: in raw".format(rft.subcommand,sc.operation))

        # load patch data--verify its good json
        #  get the patchData from rft.requestData  readin on commandline via: -d <patchData>
        try:
            patchData=json.loads(rft.requestData)
        except ValueError:
            rft.printErr("Patch: invalid Json input data:{}".format(rft.requestData))
            return(5,None,False,None)
        ##print("patchData: {}".format(patchData))


        # we verified that we had two args in RawMain(), so we can just read the <uri> arg here
        path=sc.args[1]
        method="PATCH"
        rft.printVerbose(4,"raw: PATCH: method:{} path:{}".format(method,path))

        apiType=self.getApiType(rft,path)   # UNAUTHENTICATED API or Authenticated API

        # calculate rootUrl--with correct scheme, root path, and rhost IP (w/o querying rhost)
        scheme=rft.getApiScheme(apiType)
        scheme_tuple=[scheme, rft.rhost, "/redfish", "","",""]
        rootUrl=urlunparse(scheme_tuple)  # so rootUrl="http[s]://<rhost>[:<port>]/redfish"

        #read the resource--the generic patch command needs it to get the etag
        rc,r,j,d=rft.rftSendRecvRequest(apiType, "GET", rootUrl, relPath=path)
        if(rc!=0):
            rft.printErr("raw: Error getting resource prior to patching it, aborting")
            return(rc,r,False,None)

        # now call the generic patch function to send the patch
        rc,r,j,d=rft.patchResource(rft, r, patchData)

        if(rc==0):   rft.printVerbose(1," Systems Patch:",skip1=True, printV12=cmdTop)
        return(rc,r,j,d)


    def httpPost(self,sc,op,rft,cmdTop=False, prop=None):
        rft.printVerbose(4,"{}:{}: in raw".format(rft.subcommand,sc.operation))

        # load post data--verify its good json
        #  get the postData from rft.requestData  readin on commandline via: -d <patchData>
        try:
            postData=json.loads(rft.requestData)
        except ValueError:
            rft.printErr("Post: invalid Json input data:{}".format(rft.requestData))
            return(5,None,False,None)
        ##print("postData: {}".format(postData))

        # we verified that we had two args in RawMain(), so we can just read the <uri> arg here
        path=sc.args[1]
        method="POST"
        rft.printVerbose(4,"raw: POST: method:{} path:{}".format(method,path))

        apiType=self.getApiType(rft,path)   # UNAUTHENTICATED API or Authenticated API

        # calculate rootUrl--with correct scheme, root path, and rhost IP (w/o querying rhost)
        scheme=rft.getApiScheme(apiType)
        scheme_tuple=[scheme, rft.rhost, "/redfish", "","",""]
        rootUrl=urlunparse(scheme_tuple)  # so rootUrl="http[s]://<rhost>[:<port>]/redfish"

        #output the post data in json to send over the network   
        reqPostData=json.dumps(postData)
        #Post the data
        rc,r,j,d=rft.rftSendRecvRequest(apiType, method, rootUrl, relPath=path, reqData=reqPostData)
        if(rc!=0):
            rft.printErr("raw: Error sending POST to resource, aborting")
            return(rc,r,False,None)


        if(rc==0):   rft.printVerbose(1," raw POST:",skip1=True, printV12=cmdTop)
        return(rc,r,j,d)


    def httpPut(self,sc,op,rft,cmdTop=False, prop=None):
        rft.printVerbose(4,"{}:{}: in raw".format(rft.subcommand,sc.operation))

        # load put data--verify its good json
        #  get the postData from rft.requestData  readin on commandline via: -d <patchData>
        try:
            putData=json.loads(rft.requestData)
        except ValueError:
            rft.printErr("Put: invalid Json input data:{}".format(rft.requestData))
            return(5,None,False,None)
        ##print("postData: {}".format(postData))

        # we verified that we had two args in RawMain(), so we can just read the <uri> arg here
        path=sc.args[1]
        method="PUT"
        rft.printVerbose(4,"raw: POST: method:{} path:{}".format(method,path))

        apiType=self.getApiType(rft,path)   # UNAUTHENTICATED API or Authenticated API

        # calculate rootUrl--with correct scheme, root path, and rhost IP (w/o querying rhost)
        scheme=rft.getApiScheme(apiType)
        scheme_tuple=[scheme, rft.rhost, "/redfish", "","",""]
        rootUrl=urlunparse(scheme_tuple)  # so rootUrl="http[s]://<rhost>[:<port>]/redfish"

        #output the post data in json to send over the network   
        reqPutData=json.dumps(putData)
        #Put the data
        rc,r,j,d=rft.rftSendRecvRequest(apiType, method, rootUrl, relPath=path, reqData=reqPutData)
        if(rc!=0):
            rft.printErr("raw: Error sending PUT to resource, aborting")
            return(rc,r,False,None)


        if(rc==0):   rft.printVerbose(1," raw PUT:",skip1=True, printV12=cmdTop)
        return(rc,r,j,d)


    def httpDelete(self,sc,op,rft,cmdTop=False, prop=None):
        rft.printVerbose(4,"{}:{}: in raw".format(rft.subcommand,sc.operation))

        # we verified that we had two args in RawMain(), so we can just read the <uri> arg here
        path=sc.args[1]
        method="DELETE"
        rft.printVerbose(4,"raw: DELETE: method:{} path:{}".format(method,path))

        apiType=self.getApiType(rft,path)   # UNAUTHENTICATED API or Authenticated API

        # calculate rootUrl--with correct scheme, root path, and rhost IP (w/o querying rhost)
        scheme=rft.getApiScheme(apiType)
        scheme_tuple=[scheme, rft.rhost, "/redfish", "","",""]
        rootUrl=urlunparse(scheme_tuple)  # so rootUrl="http[s]://<rhost>[:<port>]/redfish"

        #send DELETE to the resource path specified
        rc,r,j,d=rft.rftSendRecvRequest(apiType, method, rootUrl, relPath=path)
        if(rc!=0):
            rft.printErr("raw: Error sending DELETE to resource, aborting")
            return(rc,r,False,None)


        if(rc==0):   rft.printVerbose(1," raw DELETE:",skip1=True, printV12=cmdTop)
        return(rc,r,j,d)
    
      
    def examples(self,sc,op,rft,cmdTop=False,prop=None):
        rft.printVerbose(4,"{}:{}: in operation".format(rft.subcommand,sc.operation))
        print(" {} -r<ip> raw GET /redfish/v1/   # returns the root collection".format(rft.program))

        return(0,None,False,None)



    
'''
TODO:
1. need to handle case where no patch or post data (no -d)
2. add raw PUT
CHANGES:
0.9.2:  no longer call /redfish and /redfish/v1 before executing the raw api
'''

    


