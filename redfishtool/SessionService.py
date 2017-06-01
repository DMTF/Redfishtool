# Copyright Notice:
# Copyright 2016 Distributed Management Task Force, Inc. All rights reserved.
# License: BSD 3-Clause License. For full text see link: https://github.com/DMTF/Redfishtool/LICENSE.md

# redfishtool: SessionService.py
#
# contains SessionService related subCommands and access functions
#
# Class RfSessionServiceMain
#  - functions init, displayUsage, displayHelp, displayOperations,
#  - runOperation - SessionService command table, dispatch of operation eg get, reset
#  - SessionServiceMain - called from redfishMain, enforce legal option combinations,
#    and call runOperation to run SessionService operation (sub-sub-command)
#
# Class RfSessionServiceOperations
#  All of the SessionService sub-command operations eg: login, logout, get sessionService, etc
#  - hello - test cmd
#  - get - get the session service
#  - patch - raw subcommand to patch a sessionService, with etag support
#  - setSessionTimeout -- patches the SessionTimeout property w/ etag support
#  - Sessions - get Sessions collection, Session instance, list Sessions, get all Sessions
#  - login - Session login (post to add a new session)
#  - logout - Session logout (delete to delete a session)
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

class RfSessionServiceMain():
    def __init__(self):
        # operation string and remaining args
        self.operation=None
        self.args=None
        self.argnum=0
        self.nonIdCommands=None

    def displayUsage(self,rft):
        if(rft.quiet): return(0)
        print("  Usage:")
        print("   {} [OPTNS]  SessionService  <operation> [<args>]  -- perform <operation> on the SessionService  ".format(rft.program))

    def displayHelp(self,rft):
        self.displayUsage(rft)
        self.displayOperations(rft)
        print("")
   
    def displayOperations(self,rft):
        print("  <operations>:")
        print("     [get]                     -- get the sessionService object. ")
        print("     patch {A: B,C: D,...}     -- patch the sessionService w/ json-formatted {prop: value...} ")
        print("     setSessionTimeout <timeout> -- patches the SessionTimeout property w/ etag support ")
        print("     Sessions [list]           -- get the \"Sessions\" collection, or list \"Id\", username, and Url ")
        print("       Sessions [IDOPTN]       --   get the member specified by IDOPTN: -i<Id>, -m<prop>:<val>, -l<link>, -a #all")
        print("     login                     -- sessionLogin.  post to Sessions collection to create a session")
        print("                                   the user is -u<user>, password is -p<password>")
        print("     logout                    -- logout or delete the session by identified by -i<SessionId> or -l<link>")
        print("                                   where <link> is the session path returned in Location from login")
        print("     examples                  -- example commands with syntax")
        print("     hello                     -- Systems hello -- debug command")
        return(0)


    def runOperation(self,rft):
        #  instantiate SessionServiceOperations class
        op=RfSessionServiceOperations()
        
        #  dispatch table for each subcommand:   "cmdName": cmdClass.cmdFunction"
        operationTable = {
            "get":                          op.get,
            "patch":                        op.patch,
            "setSessionTimeout":            op.setSessionTimeout,
            "Sessions":                     op.getSessions,
            "login":                        op.sessionLogin,
            "logout":                       op.sessionLogout,
            "hello":                        op.hello,
            "examples":                     op.examples
        }

        rft.printVerbose(5,"SessionService:runOperation: operation: {}".format(self.operation))
        rft.printVerbose(5,"SessionService:runOperation: args:  {}".format(self.args))
            
        if self.operation in operationTable:
            rft.printVerbose(5,"SessionService:runOperation: found Oper: {} in table. executing".format(rft.subcommand))
            rc,r,j,d=operationTable[self.operation](self, op, rft, cmdTop=True)
            return(rc,r,j,d)
        
        else: # invalid operation
            rft.printErr("SessionService: Invalid operation: {}".format(self.operation))
            return(2,None,False,None)
        


    def SessionServiceMain(self,rft,cmdTop=False):
        rft.printVerbose(4,"SessionServiceMain:  subcommand: {}".format(rft.subcommand))
        
        if( rft.help ):
            self.displayHelp(rft)
            return(0,None,False,None)
        
        # we will validate usage of -P and -a in action processing
        # actually, if a non 'get' action is specified, -P and -a are just ignored :)

        args=rft.subcommandArgv[0:]
        
        #if no args, this is a getSessionService command
        if(  len(args) < 2 ):
            self.operation="get"
            self.args= None
        else:
            self.operation=args[1]
            self.args = args[1:]        # now args points to the 1st argument
            self.argnum =len(self.args)
            
        rft.printVerbose(5,"SessionService: operation={}, args={}".format(self.operation,self.args))
                          
        # now execute the operation.
        rc,r,j,d = self.runOperation(rft)
                
        if(rc !=0 ):
            rft.printVerbose(5,"SessionService: operation returned with error: rc={}".format(rc))
            return(rc,r,False,None)
        
        #else, if here, the subcommand executed without error.  Return with 0 exit code
        rft.printVerbose(5,"SessionService: operation exited OK")
        return(rc,r,j,d)


#
# contains operations related to the SessionService subCommand
#
class RfSessionServiceOperations():
    def __init__(self):
        self.SessionServicePath=None
        self.SessionServiceCollectionDict=None


    def hello(self,sc,op,rft,cmdTop=False):
        rft.printVerbose(4,"in hello")
        rft.printVerbose(4,"   subcmd:{}, operation:{}, args:{}".format(rft.subcommand,sc.operation,sc.args))
        print("hello world from SessionService")
        return(0,None,False,None)



    def get(self,sc,op,rft, cmdTop=False, prop=None):
        rft.printVerbose(4,"{}:{}: in operation".format(rft.subcommand,sc.operation))

        # 1st get serviceRoot
        svcRoot=RfServiceRoot()
        rc,r,j,d = svcRoot.getServiceRoot(rft)
        if( rc != 0 ):
            rft.printErr("get SessionService: Error getting service root, aborting")
            return(rc,r,False,None)

        # get the link to the SessionService
        # need to test we got good data
        if (("SessionService" in d) and ("@odata.id" in d["SessionService"])):
            sessionServiceLink=d["SessionService"]["@odata.id"]
        else:
            rft.printErr("Error:  root does not have a SessionService link")
            return(4)
        
        rft.printVerbose(4,"SessionService: get SessionService: link is: {}".format(sessionServiceLink))
      
        if cmdTop is True:   prop=rft.prop
              
        # do a GET to get the SessionService, if -P show property, else show full response
        rc,r,j,d=rft.rftSendRecvRequest(rft.AUTHENTICATED_API, 'GET', r.url, relPath=sessionServiceLink, prop=prop)

        if(rc==0):   rft.printVerbose(1," SessionService Resource:",skip1=True, printV12=cmdTop)
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
            rft.printErr("     : expect: SessionService patch \"{ <prop>: <value> }\"")
            return(4,None,False,None)

        # read the sessionServiceLink resource
        # this is used by the generic rft.patchResource() function to see if there is an etag in the response
        # if an etag is in response hdr, then we must include the etag on the patch, so this get is required
        # note: the format of etag header for redfish is:  ETag: W/"<string>" or "<string"
        rc,r,j,d=op.get(sc,op,rft)
        if( rc != 0):
            return(rc,r,False,None)

        # now call the generic patch function to send the patch
        rc,r,j,d=rft.patchResource(rft, r, patchData)

        if(rc==0):   rft.printVerbose(1," SessionService Patch:",skip1=True, printV12=cmdTop)
        return(rc,r,j,d)


        
    def setSessionTimeout(self,sc,op,rft,cmdTop=False, prop=None):
        rft.printVerbose(4,"{}:{}: in operation".format(rft.subcommand,sc.operation))

        propName="SessionTimeout"
        
        # get the SessionTimeout from args
        if(len(sc.args) < 2 ):
            rft.printErr("Error, no SessionTimeout value specified")
            rft.printErr("Syntax:  {} [options] SessionService setSessionTimeout <timeoutInt> ".format(rft.program))
            return(8,None,False,None)
        sessTimeout=int(sc.args[1],0)  # base 0 means int() will interpret 0x<num> as hex and <num> as decimal
        patchData={propName: sessTimeout}
        
        # get the resource to verify it includes AssetTag,
        # the response will also be used by Patch() to check for etag 
        rc,r,j,d=op.get(sc,op,rft)
        if( rc != 0):  return(rc,r,False,None)
        if( not propName in d ):
            rft.printErr("SessionService resource does not have a {} property.".format(propName))
            return(8,r,False,None)

        rc,r,j,d=rft.patchResource(rft, r, patchData)
        if(rc==0):
            rft.printVerbose(1," SessionService setSessionTimeout:",skip1=True, printV12=cmdTop)
            assetTag={propName: d[propName]}
            return(rc,r,j,assetTag)         
        else: return(rc,r,False,None)



    def getSessions(self,sc,op, rft, cmdTop=False, prop=None):
        rft.printVerbose(4,"{}:{}: in operation: getSessions collection".format(rft.subcommand,sc.operation))

        # get the system resource
        rc,r,j,d=op.get(sc,op, rft)     
        if( rc != 0):  return(rc,r,False,None)
        
        collName="Sessions"
        # get the link to the Sessions collection
        if ((collName in d) and ("@odata.id" in d[collName])):
            sessionsLink=d[collName]["@odata.id"]
        else:
            rft.printErr("Error: SessionService resource does not have a {} link".format(collName))
            return(6,None,False,None)
        
        if cmdTop is True:   prop=rft.prop

        # check if there is a list arg for the operation
        if( sc.argnum > 1 and sc.args[1] == 'list' ):
            #get the collection
            rc,r,j,d=rft.rftSendRecvRequest(rft.AUTHENTICATED_API, 'GET', r.url, relPath=sessionsLink)
            #loop through the members and create the list sub-operation response
            rc,r,j,d=rft.listCollection(rft, r, d, prop="UserName")
            if(rc==0):
                rft.printVerbose(1," list {} Collection member info: Id, URI, Socket".format(collName,skip1=True, printV12=cmdTop))

        # else: check if no session was specified.  If not, return the collection
        elif(rft.IdLevel2OptnCount==0):
            rc,r,j,d=rft.rftSendRecvRequest(rft.AUTHENTICATED_API, 'GET', r.url, relPath=sessionsLink, prop=prop)
            if(rc==0):
                rft.printVerbose(1," {} Collection ".format(collName,skip1=True, printV12=cmdTop))

        # else:  check if the -a (all) option is set. If not, return the session specific by -i or -m or -l
        # search collection to find path using getPath2 
        elif( rft.allOptn is not True ):
            # get the Sessions collection
            rc,r,j,d=rft.rftSendRecvRequest(rft.AUTHENTICATED_API, 'GET', r.url, relPath=sessionsLink, prop=prop)
            collUrl=r.url

            # now search for 2nd level resource and return
            path2,rc,r,j,d=rft.getLevel2ResourceById(rft,r,d)
            if(rc!=0):
                return(rc,r,j,d)
            # so rc=0
            #if sysPath returned a response but we need to extract the property do it here
            if( (r is not None) and (prop is not None) ):
                rc,r,j,d=rft.getPropFromDict(rft,r,d,prop)

            # otherwise, we need to do a GET to get the session, if -P show property, else show full response
            elif( r is None ):
                rc,r,j,d=rft.rftSendRecvRequest(rft.AUTHENTICATED_API, 'GET', collUrl, relPath=path2, prop=prop)
                if(rc==0):
                    rft.printVerbose(1," {} Collection Member ".format(collName,skip1=True, printV12=cmdTop))

        # else, return ALL of the Sessions members
        else:
            rft.printVerbose(4,"getting expanded Sessions Collection")
            rc,r,j,d=rft.getAllCollectionMembers(rft, r.url, relPath=sessionsLink)
            if(rc==0):
                rft.printVerbose(1," Get ALL {} Collection Members".format(collName,skip1=True, printV12=cmdTop))
        
        return(rc,r,j,d)


    

    #SessionService -u <username> -p <passwd> login,  returns authToken and sessionId
    def sessionLogin(self,sc,op,rft,cmdTop=False, prop=None):
        rft.printVerbose(4,"{}:{}: in operation".format(rft.subcommand,sc.operation))

        #note that <username> and <password> were passed-in in -u and -p options and are stores in
        # rft.user and rft.password

        # 1st get serviceRoot
        svcRoot=RfServiceRoot()
        rc,r,j,d = svcRoot.getServiceRoot(rft)
        if( rc != 0 ):
            rft.printErr("SessionService: login: Error getting service root, aborting")
            return(rc,r,False,None)

        #call rfSessionLogin in transport class to login
        rc,r,j,d=rft.rfSessionLogin(rft,cleanupOnExit=False)
        if(rc == 0):
            # return sessionId and authToken
            respData={"SessionId": rft.sessionId, "SessionLocation": rft.sessionLink, "X-Auth-Token": rft.authToken}
            rft.printVerbose(1," SessionLogin: {}".format(respData, skip1=True, printV12=cmdTop))
            return(rc,r,j,respData)
        else:
            return(rc,r,j,d)


    #SessionService -t<token> logout [-i<sessionId>|-l<sessionLink>],   returns 204 no content
    def sessionLogout(self,sc,op,rft,cmdTop=False, prop=None):
        rft.printVerbose(4,"{}:{}: in operation".format(rft.subcommand,sc.operation))

        if( (rft.linkLevel2 is None) and( rft.IdLevel2 is None) ):
            rft.printErr("Error, logout:  no sessionId or sessionLink specified")
            rft.printErr("Syntax:  {} [options] [SessionService] logout [-i<sessionId> | -l <sessionLink>]".format(rft.program))
            return(8,None,False,None)

        # 1st get serviceRoot
        svcRoot=RfServiceRoot()
        rc,r,j,d = svcRoot.getServiceRoot(rft)
        if( rc != 0 ):
            rft.printErr("SessionService: login: Error getting service root, aborting")
            return(rc,r,False,None)
            
        #find Sessions collection
        if( ("Links" in d) and ("Sessions" in d["Links"]) and ("@odata.id" in d["Links"]["Sessions"]) ):
            sessionsLink=rft.rootResponseDict["Links"]["Sessions"]["@odata.id"]
            #print("loginUri:{}".format(loginUri))
        else:
            rft.printErr("Error: the rootService response does not have a login link: \"Links\":\"Sessions\":{{\"@odata.id\": <uri>}")
            return(4,None,False,None)
            
        # get the Sessions collection
        rc,r,j,d=rft.rftSendRecvRequest(rft.AUTHENTICATED_API, 'GET', r.url, relPath=sessionsLink, prop=prop)
        if(rc != 0):
            rft.printErr("Error: logout: cant read sessions collection")
            return(6,None,False,None)
        # now search for 2nd level resource and return
        path2,rc,r,j,d=rft.getLevel2ResourceById(rft,r,d)
        if(rc!=0):
            rft.printErr("Error: the specified sessionId or sessionLink was not a valid Sessions collection entry")
            return(rc,r,j,d)

        #path2 is the path the the session we want to delete
        rc,r,j,d=rft.rfSessionDelete(rft,sessionLink=path2)
        if(rc!=0):
            rft.printErr("Error: Logout: the session delete failed")
            return(rc,r,j,d)
        else:
            rft.printVerbose(1," SessionLogout successful".format(skip1=True, printV12=cmdTop))
            return(rc,r,j,d)


    
      
    def examples(self,sc,op,rft,cmdTop=False,prop=None):
        rft.printVerbose(4,"{}:{}: in operation".format(rft.subcommand,sc.operation))
        print(" {} -r<ip> SessionService                   # gets the sessionService".format(rft.program))
        print(" {} -r<ip> SessionService setSessionTimeout <timeout> # sets the session timeout property".format(rft.program))
        print(" {} -r<ip> SessionService Sessions             # gets Sessions collection".format(rft.program))
        print(" {} -r<ip> SessionService Sessions -l<sessUrl> # gets the session at URI=<sessUrl".format(rft.program))
        print(" {} -r<ip> SessionService Sessions -i<sessId>  # gets the session with session Id <sessId>".format(rft.program))
        print(" {} -r<ip> SessionService patch {{A: B,C: D,...}} # patch the json-formatted {{prop: value...}} data to the sessionService object".format(rft.program))
        print(" {} -r<ip> SessionService login <usernm> <passwd> # login (create session)".format(rft.program))
        print(" {} -r<ip> SessionService logout <sessionId>      # logout (delete session <sessId>".format(rft.program))
        return(0,None,False,None)


    
'''
TODO:
1. e

'''

    


