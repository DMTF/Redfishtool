# Copyright Notice:
# Copyright 2016 DMTF. All rights reserved.
# License: BSD 3-Clause License. For full text see link: https://github.com/DMTF/Redfishtool/blob/master/LICENSE.md

# redfishtool: AccountService.py
#
# contains AccountService related subCommands and access functions
#
# Class RfAccountServiceMain
#  - functions init, displayUsage, displayHelp, displayOperations,
#  - runOperation - AccountService command table, dispatch of operation eg get, reset
#  - AccountServiceMain - called from redfishMain, enforce legal option combinations,
#    and call runOperation to run AccountService operation (sub-sub-command)
#
# Class RfAccountServiceOperations
#  All of the AccountService sub-command operations eg:  get AccountService,Accounts, Sessions, adduser... etc
#  - hello - test cmd
#  - get - get the account service
#  - patch - raw subcommand to patch a accountService, with etag support
#  - Accounts - get Accounts collection, Accounts instance, list Accounts, get all Accounts
#  - Roles    - get Roles collection, Roles instance, list Roles, get all Roles
#  - adduser - add a new user to Accounts collection
#  - setpassword - update the password of an existing user account
#  - deleteuser - delete an existin user from Accouts collection
#  - userAdmin - enable, disable, or unlock a user account
#  - addRole - add a new custom role to the Roles collection
#  - deleteRole - delete an existing role from Roles collection
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

class RfAccountServiceMain():
    def __init__(self):
        # operation string and remaining args
        self.operation=None
        self.args=None
        self.argnum=0
        self.nonIdCommands=None

    def displayUsage(self,rft):
        if(rft.quiet): return(0)
        print("  Usage:")
        print("   {} [OPTNS]  AccountService  <operation> [<args>]  -- perform <operation> on the AccountService  ".format(rft.program))

    def displayHelp(self,rft):
        self.displayUsage(rft)
        self.displayOperations(rft)
        print("")

    def displayOperations(self,rft):
        print("  <operations>:")
        print("     [get]                     -- get the AccountService object. ")
        print("     patch {A: B,C: D,...}     -- patch the AccountService w/ json-formatted {prop: value...} ")
        print("     Accounts [list]           -- get the \"Accounts\" collection, or list \"Id\", username, and Url ")
        print("       Accounts [IDOPTN]       --   get the member specified by IDOPTN: -i<Id>, -m<prop>:<val>, -l<link>, -a #all")
        print("     Roles [list]              -- get the \"Roles\" collection, or list \"Id\", IsPredefined, and Url ")
        print("       Roles [IDOPTN]          --   get the member specified by IDOPTN: -i<Id>, -m<prop>:<val>, -l<link>, -a #all")
        print("     adduser <usernm> <passwd> [<roleId>] -- add a new user to the Accounts collection")
        print("                               -- <roleId>:{Administrator | Operator | ReadOnlyUser | <a custom roleId}, dflt=Operator")
        print("     deleteuser <usernm>       -- delete an existing user from Accouts collection")
        print("     setpassword  <usernm> <passwd>  -- set (change) the password of an existing user account")
        print("     useradmin <userName> [enable|disable|unlock|[setRoleId <roleId>]] -- enable|disable|unlock.. a user account")
        print("     setusername <id> <userName> -- set UserName for account with given Id")
        #print("     addrole   <roleId> <listOfPrivileges> -- add a new custom role to the Roles collection")
        #print("                               -- <listOfPrivileges> is string of form: Login,ConfigeUsers,ConfigureSelf...")
        #print("     deleterole <roleId>       -- delete an existing role from Roles collection")
        print("     examples                  -- example commands with syntax")
        print("     hello                     -- AccountService hello -- debug command")
        return(0)

#  - changePassword - update the password of an existing user account
#  - deleteUser - delete an existin user from Accouts collection
#  - userAdmin - enable, disable, or unlock a user account
#  - addRole - add a new custom role to the Roles collection
#  - deleteRole - delete an existing role from Roles collection
#  - examples --prints some example apis

    def runOperation(self,rft):
        #  instantiate AccountService class
        op=RfAccountServiceOperations()

        #  dispatch table for each subcommand:   "cmdName": cmdClass.cmdFunction"
        operationTable = {
            "get":                          op.get,
            "patch":                        op.patch,
            "Accounts":                     op.getAccounts,
            "Roles":                        op.getRoles,
            "adduser":                      op.addUser,
            "deleteuser":                   op.deleteUser,
            "setpassword":                  op.setPassword,
            "useradmin":                    op.userAdmin,
            "setusername":                  op.setUsername,
            #"addrole":                      op.addRole,
            #"deleterole":                   op.deleteRole,
            "hello":                        op.hello,
            "examples":                     op.examples
        }

        rft.printVerbose(5,"AccountService:runOperation: operation: {}".format(self.operation))
        rft.printVerbose(5,"AccountService:runOperation: args:  {}".format(self.args))
            
        if self.operation in operationTable:
            rft.printVerbose(5,"AccountService:runOperation: found Oper: {} in table. executing".format(rft.subcommand))
            rc,r,j,d=operationTable[self.operation](self, op, rft, cmdTop=True)
            return(rc,r,j,d)
        
        else: # invalid operation
            rft.printErr("AccountService: Invalid operation: {}".format(self.operation))
            return(2,None,False,None)
        


    def AccountServiceMain(self,rft,cmdTop=False):
        rft.printVerbose(4,"AccountServiceMain:  subcommand: {}".format(rft.subcommand))
        
        if( rft.help ):
            self.displayHelp(rft)
            return(0,None,False,None)
        
        # we will validate usage of -P and -a in action processing
        # actually, if a non 'get' action is specified, -P and -a are just ignored :)

        args=rft.subcommandArgv[0:]
        
        #if no args, this is a getAccountService command
        if(  len(args) < 2 ):
            self.operation="get"
            self.args= None
        else:
            self.operation=args[1]
            self.args = args[1:]        # now args points to the 1st argument
            self.argnum =len(self.args)
            
        rft.printVerbose(5,"AccountService: operation={}, args={}".format(self.operation,self.args))
                          
        # now execute the operation.
        rc,r,j,d = self.runOperation(rft)
                
        if(rc !=0 ):
            rft.printVerbose(5,"AccountService: operation returned with error: rc={}".format(rc))
            return(rc,r,False,None)
        
        #else, if here, the subcommand executed without error.  Return with 0 exit code
        rft.printVerbose(5,"AccountService: operation exited OK")
        return(rc,r,j,d)


#
# contains operations related to the AccountService subCommand
#
class RfAccountServiceOperations():
    def __init__(self):
        self.AccountServicePath=None
        self.AccountServiceCollectionDict=None


    def hello(self,sc,op,rft,cmdTop=False):
        rft.printVerbose(4,"in hello")
        rft.printVerbose(4,"   subcmd:{}, operation:{}, args:{}".format(rft.subcommand,sc.operation,sc.args))
        print("hello world from AccountService")
        return(0,None,False,None)



    def get(self,sc,op,rft, cmdTop=False, prop=None):
        rft.printVerbose(4,"{}:{}: in operation".format(rft.subcommand,sc.operation))

        # 1st get serviceRoot
        svcRoot=RfServiceRoot()
        rc,r,j,d = svcRoot.getServiceRoot(rft)
        if( rc != 0 ):
            rft.printErr("get AccountService: Error getting service root, aborting")
            return(rc,r,False,None)

        # get the link to the AccountService
        # need to test we got good data
        if (("AccountService" in d) and ("@odata.id" in d["AccountService"])):
            accountServiceLink=d["AccountService"]["@odata.id"]
        else:
            rft.printErr("Error:  root does not have a AccountService link")
            return(4)
        
        rft.printVerbose(4,"AccountService: get AccountService: link is: {}".format(accountServiceLink))
      
        if cmdTop is True:   prop=rft.prop
              
        # do a GET to get the AccountService, if -P show property, else show full response
        rc,r,j,d=rft.rftSendRecvRequest(rft.AUTHENTICATED_API, 'GET', r.url, relPath=accountServiceLink, prop=prop)

        if(rc==0):   rft.printVerbose(1," AccountService Resource:",skip1=True, printV12=cmdTop)
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

        # read the AccountService resource
        # this is used by the generic rft.patchResource() function to see if there is an etag in the response
        # if an etag is in response hdr, then we must include the etag on the patch, so this get is required
        # note: the format of etag header for redfish is:  ETag: W/"<string>" or "<string"
        rc,r,j,d=op.get(sc,op,rft)
        if( rc != 0):
            return(rc,r,False,None)

        # now call the generic patch function to send the patch
        rc,r,j,d=rft.patchResource(rft, r, patchData)

        if(rc==0):   rft.printVerbose(1," AccountService Patch:",skip1=True, printV12=cmdTop)
        return(rc,r,j,d)


        

    def getAccounts(self,sc,op, rft, cmdTop=False, prop=None):
        rft.printVerbose(4,"{}:{}: in operation: getAccounts collection".format(rft.subcommand,sc.operation))

        # get the AccountService resource
        rc,r,j,d=op.get(sc,op, rft)     
        if( rc != 0):  return(rc,r,False,None)
        
        collName="Accounts"
        # get the link to the Accounts collection
        if ((collName in d) and ("@odata.id" in d[collName])):
            accountsLink=d[collName]["@odata.id"]
        else:
            rft.printErr("Error: AccountsService resource does not have a {} link".format(collName))
            return(6,None,False,None)
        
        if cmdTop is True:   prop=rft.prop

        # check if there is a list arg for the operation
        if( sc.argnum > 1 and sc.args[1] == 'list' ):
            #get the collection
            rc,r,j,d=rft.rftSendRecvRequest(rft.AUTHENTICATED_API, 'GET', r.url, relPath=accountsLink)
            #loop through the members and create the list sub-operation response
            rc,r,j,d=rft.listCollection(rft, r, d, prop="UserName")
            if(rc==0):
                rft.printVerbose(1," list {} Collection member info: Id, URI, UserName".format(collName,skip1=True, printV12=cmdTop))

        # else: check if no account was specified.  If not, return the collection
        elif(rft.IdLevel2OptnCount==0):
            rc,r,j,d=rft.rftSendRecvRequest(rft.AUTHENTICATED_API, 'GET', r.url, relPath=accountsLink, prop=prop)
            if(rc==0):
                rft.printVerbose(1," {} Collection ".format(collName,skip1=True, printV12=cmdTop))

        # else:  check if the -a (all) option is set. If not, return the session specific by -i or -m or -l
        # search collection to find path using getPath2 
        elif( rft.allOptn is not True ):
            # get the Accounts collection
            rc,r,j,d=rft.rftSendRecvRequest(rft.AUTHENTICATED_API, 'GET', r.url, relPath=accountsLink, prop=prop)
            collUrl=r.url

            # now search for 2nd level resource and return
            path2,rc,r,j,d=rft.getLevel2ResourceById(rft,r,d)
            if(rc!=0):
                return(rc,r,j,d)
            # so rc=0
            #if sysPath returned a response but we need to extract the property do it here
            if( (r is not None) and (prop is not None) ):
                rc,r,j,d=rft.getPropFromDict(rft,r,d,prop)

            # otherwise, we need to do a GET to get the account, if -P show property, else show full response
            elif( r is None ):
                rc,r,j,d=rft.rftSendRecvRequest(rft.AUTHENTICATED_API, 'GET', collUrl, relPath=path2, prop=prop)
                if(rc==0):
                    rft.printVerbose(1," {} Collection Member ".format(collName,skip1=True, printV12=cmdTop))

        # else, return ALL of the Accounts members
        else:
            rft.printVerbose(4,"getting expanded Accounts Collection")
            rc,r,j,d=rft.getAllCollectionMembers(rft, r.url, relPath=accountsLink)
            if(rc==0):
                rft.printVerbose(1," Get ALL {} Collection Members".format(collName,skip1=True, printV12=cmdTop))
        
        return(rc,r,j,d)

        

    def getRoles(self,sc,op, rft, cmdTop=False, prop=None):
        rft.printVerbose(4,"{}:{}: in operation: getRoles collection".format(rft.subcommand,sc.operation))

        # get the AccountService resource
        rc,r,j,d=op.get(sc,op, rft)     
        if( rc != 0):  return(rc,r,False,None)
        
        collName="Roles"
        # get the link to the Roles collection
        if ((collName in d) and ("@odata.id" in d[collName])):
            rolesLink=d[collName]["@odata.id"]
        else:
            rft.printErr("Error: AccountsService resource does not have a {} link".format(collName))
            return(6,None,False,None)
        
        if cmdTop is True:   prop=rft.prop

        # check if there is a list arg for the operation
        if( sc.argnum > 1 and sc.args[1] == 'list' ):
            #get the collection
            rc,r,j,d=rft.rftSendRecvRequest(rft.AUTHENTICATED_API, 'GET', r.url, relPath=rolesLink)
            #loop through the members and create the list sub-operation response
            rc,r,j,d=rft.listCollection(rft, r, d, prop="IsPredefined")
            if(rc==0):
                rft.printVerbose(1," list {} Collection member info: Id, URI, IsPredefined".format(collName,skip1=True, printV12=cmdTop))

        # else: check if no account was specified.  If not, return the collection
        elif(rft.IdLevel2OptnCount==0):
            rc,r,j,d=rft.rftSendRecvRequest(rft.AUTHENTICATED_API, 'GET', r.url, relPath=rolesLink, prop=prop)
            if(rc==0):
                rft.printVerbose(1," {} Collection ".format(collName,skip1=True, printV12=cmdTop))

        # else:  check if the -a (all) option is set. If not, return the session specific by -i or -m or -l
        # search collection to find path using getPath2 
        elif( rft.allOptn is not True ):
            # get the Accounts collection
            rc,r,j,d=rft.rftSendRecvRequest(rft.AUTHENTICATED_API, 'GET', r.url, relPath=rolesLink, prop=prop)
            collUrl=r.url

            # now search for 2nd level resource and return
            path2,rc,r,j,d=rft.getLevel2ResourceById(rft,r,d)
            if(rc!=0):
                return(rc,r,j,d)
            # so rc=0
            #if sysPath returned a response but we need to extract the property do it here
            if( (r is not None) and (prop is not None) ):
                rc,r,j,d=rft.getPropFromDict(rft,r,d,prop)

            # otherwise, we need to do a GET to get the account, if -P show property, else show full response
            elif( r is None ):
                rc,r,j,d=rft.rftSendRecvRequest(rft.AUTHENTICATED_API, 'GET', collUrl, relPath=path2, prop=prop)
                if(rc==0):
                    rft.printVerbose(1," {} Collection Member ".format(collName,skip1=True, printV12=cmdTop))

        # else, return ALL of the Accounts members
        else:
            rft.printVerbose(4,"getting expanded Roles Collection")
            rc,r,j,d=rft.getAllCollectionMembers(rft, r.url, relPath=rolesLink)
            if(rc==0):
                rft.printVerbose(1," Get ALL {} Collection Members".format(collName,skip1=True, printV12=cmdTop))
        
        return(rc,r,j,d)


    

    # adduser <username> <passwd> [<roleId>] ---add a new user
    def addUser(self,sc,op,rft,cmdTop=False, prop=None):
        rft.printVerbose(4,"{}:{}: in operation".format(rft.subcommand,sc.operation))

        # verify we got 2 args <username> and <passwd>
        # if we got 3rd arg <roleId>, use it, otherwise use builtin Operator role
        # get the Accounts collection
        # then verify we don't already have a user with that username
        # then get Roles collection, and verify it is a valid role for that system
        # create patch string
        # POST new entry to Accounts with: user, passwd, roleId to create new user

        # verify we have two addl arg, 
        if(len(sc.args) < 3 ):
            rft.printErr("Error, adduser: invalid number of arguments")
            rft.printErr("Syntax:  {} AccountService adduser <username> <passwd> [<roleId>]".format(rft.program))
            rft.printErr("      default <roleId> is Operator")
            return(8,None,False,None)
        
        # get the <username> and <password> from args
        userName=sc.args[1]
        password=sc.args[2]

        # if a roleId was specified (arg3), then use it, otherwise use default operator
        if(len(sc.args) > 3 ):
            roleVal=sc.args[3]
        else:
            roleVal="Operator"
            
        # get Accounts collection
        rc,r,j,d=op.getAccounts(sc,op, rft)     
        if( rc != 0):  return(rc,r,False,None)
        accountsUrl=r.url
        
        # check if we already have a user with this username
        rft.gotMatchLevel2Optn=True
        rft.matchLevel2Prop="UserName"
        rft.matchLevel2Value=userName
        path,rc,r,j,d=rft.getLevel2ResourceById(rft,r,d)  # this will return path to the acct as well as current resource in d
        if( rc == 0):  # if we found the user with this name
            rft.printErr("Error: username {} already exists".format(userName))
            return(9,None,False,None)
        
        # verify that the specified RoleId is valid for this system
        # get Roles collection
        rc,r,j,d=op.getRoles(sc,op, rft)     
        if( rc != 0):  return(rc,r,False,None)
        # check if the roleId specified is supported on this platform
        rft.gotMatchLevel2Optn=True
        rft.matchLevel2Prop="Id"
        rft.matchLevel2Value=roleVal
        path,rc,r,j,d=rft.getLevel2ResourceById(rft,r,d)  # this will return path to the acct as well as current resource in d
        if( rc != 0):
            rft.printErr("Error: roleId: {} is not supported on remote service".format(roleVal))
            return(rc,None,False,None)

        # create POST request data
        postData={"UserName": userName, "Password": password, "RoleId": roleVal}
        
        # POST new entry to Accounts with: user, passwd, roleId to create new user
        reqPostData=json.dumps(postData)
        rc,r,j,d=rft.rftSendRecvRequest(rft.AUTHENTICATED_API, 'POST', accountsUrl, reqData=reqPostData)
        if(rc==0):
            rft.printVerbose(1," Add User: {} (POST to Accounts collection): ".format(userName), skip1=True, printV12=cmdTop)
            respData=d
            return(rc,r,j,respData)
        else: return(rc,r,False,None)




    # deleteuser <username>
    def deleteUser(self,sc,op,rft,cmdTop=False, prop=None):
        rft.printVerbose(4,"{}:{}: in operation".format(rft.subcommand,sc.operation))

        # verify one addl arg username
        # get Accounts collection
        # then find the Account entry for username, and verify we have that user
        # sent DELETE to Accounts collection to remove the account

        # verify we have one addl arg: username 
        if(len(sc.args) < 2 ):
            rft.printErr("Error, deleteuser: invalid number of arguments")
            rft.printErr("Syntax:  {} AccountService deleteuser <username>".format(rft.program))
            return(8,None,False,None)
        
        # get the <username> and <password> from args
        userName=sc.args[1]

        # get Accounts collection
        rc,r,j,d=op.getAccounts(sc,op, rft)     
        if( rc != 0):  return(rc,r,False,None)
        accountsUrl=r.url
        
        # check if we indeed have a user with this username
        rft.gotMatchLevel2Optn=True
        rft.matchLevel2Prop="UserName"
        rft.matchLevel2Value=userName
        accountPath,rc,r,j,d=rft.getLevel2ResourceById(rft,r,d)  # this will return path to the acct as well as current resource in d
        if( rc != 0):  # if we found the user with this name
            rft.printErr("Error: username {} does not exists".format(userName))
            return(9,None,False,None)

        # send DELETE to this account Url to remove it from the Accounts collection
        rc,r,j,d=rft.rftSendRecvRequest(rft.AUTHENTICATED_API, 'DELETE', accountsUrl, relPath=accountPath)
        if(rc==0):
            rft.printVerbose(1," Delete User: {} (DELETE to Account entry): ".format(userName), skip1=True, printV12=cmdTop)
            return(rc,r,False,None)
        else: return(rc,r,False,None)




    # useradmin <username> {enable|disable|unlock|{setRoleId <roleId>}}
    def userAdmin(self,sc,op,rft,cmdTop=False, prop=None):
        rft.printVerbose(4,"{}:{}: in operation".format(rft.subcommand,sc.operation))

        # verify we have two addl arg, and it is a valid keyword: enable,disable,unlock,setRoleId=...
        # create the patch strint
        # get Accounts collection
        # then find the Accounts entry for username, and verify we have that user
        # verify the service supports the properties we need to set
        # send patch to set the properties
        #print("arglen:{}, arg0:{}, args:{}".format(len(sc.args),sc.args[0], sc.args))
        
        # verify we have two addl arg, 
        if(len(sc.args) < 3 ):
            rft.printErr("Error, userAdmin: invalid number of arguments")
            rc=self.userAdminUsage(rft)
            return(rc,None,False,None)
        
        # get the <username> and <action> from args
        userName=sc.args[1]
        action=sc.args[2]
        roleVal=""
        
        # create the patch string, and identify property to set so that we can check that the resource has the property later
        if(   action=="enable"):
            prop="Enabled"
            patchData={prop: True}
        elif( action=="disable"):
            prop="Enabled"
            patchData={prop: False}
        elif( action=="unlock"):
            prop="Locked"
            patchData={prop: False}
        elif( action=="setRoleId"):
            if(len(sc.args) < 4):
                rft.printErr("Error, userAdmin setRoleId: no <roleId> argument")
                rc=self.userAdminUsage(rft)
                return(rc,None,False,None)            
            else:
                prop="RoleId"
                roleVal=sc.args[3]
                patchData={prop: roleVal}
        else:
            rft.printErr("Error: userAdmin: specified <action> not valid")
            rc=self.userAdminUsage(rft)
            return(rc,None,False,None)
                 
        # get Accounts collection
        rc,r,j,d=op.getAccounts(sc,op, rft)     
        if( rc != 0):  return(rc,r,False,None)

        # find the Accounts entry for username, and verify we have that user
        rft.gotMatchLevel2Optn=True
        rft.matchLevel2Prop="UserName"
        rft.matchLevel2Value=userName
        path,rc,r,j,d=rft.getLevel2ResourceById(rft,r,d)  # this will return path to the acct as well as current resource in d
        if( rc != 0):
            rft.printErr("Error: username {} is not valid user".format(userName))
            return(rc,None,False,None)
        accountResponse=r
        
        # verify the service supports the properties we need to set
        if( not prop in d ):
            rft.printErr("Error: userAdmin: property {} not in the remote service user account resource".format(prop))
            return(8,None,False,None)

        # if action=setRoleId, verify the service has that role
        if( action=="setRoleId"):
            # get Roles collection
            rc,r,j,d=op.getRoles(sc,op, rft)     
            if( rc != 0):  return(rc,r,False,None)
            # check if the roleId specified is supported on this platform
            rft.gotMatchLevel2Optn=True
            rft.matchLevel2Prop="Id"
            rft.matchLevel2Value=roleVal
            path,rc,r,j,d=rft.getLevel2ResourceById(rft,r,d)  # this will return path to the acct as well as current resource in d
            if( rc != 0):
                rft.printErr("Error: roleId: {} is not supported on remote service".format(roleVal))
                return(rc,None,False,None)
              
        # send patch to set the properties
        rc,r,j,d=rft.patchResource(rft, accountResponse, patchData)
        if(rc==0):
            rft.printVerbose(1," AccountService userAdmin {} {} :".format(action,roleVal),skip1=True, printV12=cmdTop)
            respData={prop: d[prop]}
            return(rc,r,j,respData)
        else: return(rc,r,False,None)

    def userAdminUsage(self,rft):
        rft.printErr("Syntax:  {} useradmin <username> {{enable|disable|unlock|{{setRoleId <roleId>}} }}".format(rft.program))
        return(8)


    # setusername <id> <username>
    def setUsername(self, sc, op, rft, cmdTop=False, prop=None):
        rft.printVerbose(4, "{}:{}: in operation".format(rft.subcommand, sc.operation))

        # verify we have two addl args (<id> and <username>)
        # create the patch string
        # get Accounts collection
        # then find the Accounts entry for the id, and verify we have that id
        # verify the service supports the properties we need to set
        # send patch to set the properties
        # print("arglen:{}, arg0:{}, args:{}".format(len(sc.args),sc.args[0], sc.args))

        # verify we have two additional args,
        if (len(sc.args) != 3):
            rft.printErr("Error, setusername: invalid number of arguments")
            rc = self.setUsernameUsage(rft)
            return (rc, None, False, None)

        # get the <id> and <username> from args
        idVal = sc.args[1]
        userName = sc.args[2]

        # create the patch string, and identify property to set so that we can check that the resource has the property later
        prop = "UserName"
        patchData = {prop: userName}

        # get Accounts collection
        rc, r, j, d = op.getAccounts(sc, op, rft)
        if (rc != 0):  return (rc, r, False, None)

        # find the Accounts entry for id, and verify we have that id
        rft.gotMatchLevel2Optn = True
        rft.matchLevel2Prop = "Id"
        rft.matchLevel2Value = idVal
        path, rc, r, j, d = rft.getLevel2ResourceById(rft, r,
                                                      d)  # this will return path to the acct as well as current resource in d
        if (rc != 0):
            rft.printErr("Error: Id {} is not a valid account Id".format(idVal))
            return (rc, None, False, None)
        accountResponse = r

        # verify the service supports the properties we need to set
        if (not prop in d):
            rft.printErr("Error: setusername: property {} not in the remote service user account resource".format(prop))
            return (8, None, False, None)

        # send patch to set the properties
        rc, r, j, d = rft.patchResource(rft, accountResponse, patchData)
        if (rc == 0):
            rft.printVerbose(1, " AccountService setusername {} {} :".format(idVal, userName), skip1=True,
                             printV12=cmdTop)
            respData = {prop: d[prop]}
            return (rc, r, j, respData)
        else:
            return (rc, r, False, None)

    def setUsernameUsage(self, rft):
        rft.printErr(
            "Syntax:  {} setusername <id> <username>".format(rft.program))
        return (8)


    # setpassword <username> <password>
    def setPassword(self,sc,op,rft,cmdTop=False, prop=None):
        rft.printVerbose(4,"{}:{}: in operation".format(rft.subcommand,sc.operation))

        # verify we have two addl args:  <username> <passwd>.
        # create the patch string
        # get Accounts collection
        # then find the Accounts entry for username, and verify we have that user
        # send patch to set the password

        # verify we have two addl arg, 
        if(len(sc.args) < 3 ):
            rft.printErr("Error, setPassword: invalid number of arguments")
            rft.printErr("Syntax:  {} AccountService setPassword setpassword <username> <password>".format(rft.program))
            return(8,None,False,None) 
        
        # get the <username> and <action> from args, and for the patchData
        prop="Password"
        userName=sc.args[1]
        password=sc.args[2]
        patchData={prop: password}

        # get Accounts collection
        rc,r,j,d=op.getAccounts(sc,op, rft)     
        if( rc != 0):  return(rc,r,False,None)

        # find the Accounts entry for username, and verify we have that user
        rft.gotMatchLevel2Optn=True
        rft.matchLevel2Prop="UserName"
        rft.matchLevel2Value=userName
        path,rc,r,j,d=rft.getLevel2ResourceById(rft,r,d)  # this will return path to the acct as well as current resource in d
        if( rc != 0):
            rft.printErr("Error: username {} is not valid user".format(userName))
            return(rc,None,False,None)

        # send patch to set the properties
        # but set flag not to read the account back 
        #    since the password has changed, this would fail for Basic Auth
        rc,r,j,d=rft.patchResource(rft, r, patchData, getResponseAfterPatch=False )  
        if(rc==0):
            rft.printVerbose(1," AccountService setPassword: successful",skip1=True, printV12=cmdTop)
            respData=d
            return(rc,r,j,respData)
        else: return(rc,r,False,None)

        


    # addRole <RoleId> <priviletes string>  -- operation flow similar to addUser
    #def setPassword(self,sc,op,rft,cmdTop=False, prop=None):
    #    rft.printVerbose(4,"{}:{}: in operation".format(rft.subcommand,sc.operation))



    # deleteRole <RoleId>   -- operation flow similar to deleteUser
    #def setPassword(self,sc,op,rft,cmdTop=False, prop=None):
    #    rft.printVerbose(4,"{}:{}: in operation".format(rft.subcommand,sc.operation))


    
      
    def examples(self,sc,op,rft,cmdTop=False,prop=None):
        rft.printVerbose(4,"{}:{}: in operation".format(rft.subcommand,sc.operation))
        print(" {} -r<ip> AccountService                          # gets the AccountService".format(rft.program))
        print(" {} -r<ip> AccountService patch {{ \"AccountLockoutThreshold\": 5 }} ]# set failed login lockout threshold".format(rft.program))
        print(" {} -r<ip> AccountService Accounts                 # gets Accounts collection".format(rft.program))
        print(" {} -r<ip> AccountService Accounts list            # list Accounts to get Id, username, url for each account".format(rft.program))
        print(" {} -r<ip> AccountService Accounts -mUserName:john # gets the Accounts member with username: john".format(rft.program))
        print(" {} -r<ip> AccountService Roles  list              # list Roles collection to get RoleId, IsPredefined, & url for each role".format(rft.program))
        print(" {} -r<ip> AccountService Roles   -iAdministrator  # gets the Roles member with RoleId=Administrator".format(rft.program))
        print(" {} -r<ip> AccountService adduser john 12345 Administrator # add new user (john) w/ passwd \"12345\" and role: Administrator".format(rft.program))
        print(" {} -r<ip> AccountService deleteuser john          # delete user \"john\"s account".format(rft.program))
        print(" {} -r<ip> AccountService useradmin john disable   # disable user \"john\"s account".format(rft.program))
        print(" {} -r<ip> AccountService useradmin john unlock    # unlock user \"john\"s account".format(rft.program))
        print(" {} -r<ip> AccountService setusername 3 alice      # set username for account with id=3 to \"alice\"".format(rft.program))
        return(0,None,False,None)

    
'''
TODO:
1. add "addRole" and "deleteRole" commands
2.


'''

    


