# Copyright Notice:
# Copyright 2016 Distributed Management Task Force, Inc. All rights reserved.
# License: BSD 3-Clause License. For full text see link: https://github.com/DMTF/Redfishtool/LICENSE.md

# redfishtool:  redfishtoolTransport.py
#
# Contents:
# 1. Class RfSessionAuth --  holds auto-created session Auth info.  'requests' calls to get credentials
# 2. Class RfTransport -- has the generic functions to send/receive http requests, generic print functions, etc  
#  - transport object variables used to pass transport parameters from main to cmdTable and subcommand objects
#  - getApiScheme function -- generates proper scheme (http|https) based on input options and type of API
#  - getVersionAndSetRootPath  function -- executes GET /redfish with optional retry loop to negotiate protocol ver
#         between this program and remote service, and creates the path of the root object
#  - rftSendRecvRequest function--general function to send/receive Requests. handles exceptions, retries, error handling, headers
#         handles proper joining of relative urls, selecting proper Auth and Scheme specified by user, etc
#  - getPropFromDict --extracts a single property from a dict
#  - getVersions      -- function to return the service versions:  GET ^/redfish
#  - printVerbose -- common function used to print based on verbose level
#  - printErr -- common function to print errors
#  - printStatusErr4xx -- expands status_codes >400 to include description eg Unauthorized
#  - rfSessionLogin, rfSessionDelete -- function to create or delete session if -ASession is selected (default)
#  - rfCleanup -- called at end before returning. Deletes auto-created sessions
#  - getPathBy --function that walks collection looking for a specific instance
#  - getLevel2ResourceById -- searches a 2nd level collection (Processors) for -l urlLink, -m prop:val
#  - listCollection -- create a list of a collection members including Id, <prop>, <rpath> of each member
#         this is used by Systems and Chassis... to implement 'list' redfishtool command
#  - getAllCollectionMembers -- given a url to a collection, get it, and then get all members,
#         return dict with all members expanded
#  - patchResource - generic patch function-handles etags and re-reading patched resource if response is 204
#  - parseOdataType --parse the @odata.type property of a resource into Namespace, VersionString, ResourceType
#
# **Reference links for main requests
#      https://github.com/kennethreitz/requests
#
import os
import re
import requests
import json
import sys
import socket
import time
from urllib.parse import urljoin, urlparse, urlunparse
from requests.auth import HTTPBasicAuth, AuthBase
from .ServiceRoot import RfServiceRoot


class RfSessionAuth(AuthBase):
    def __init__(self,authToken):
        self.authToken=authToken
        #print("INIT SESSION AUTH")

    def __call__(self, r):
        r.headers['X-Auth-Token']=self.authToken
        #print("Call SESSION AUTH")
        return(r)

class RfTransport():
    def __init__(self):
        # constant parameters-- these dont change and are not updated
        self.program="redfishtool"              # program name (in case we want to change it)
        self.version="1.0.0"                    # this redfishtool version
        self.releaseDate="6/1/2017"             # release date for this version of redfishtool
        self.downloadFrom="https://github.com/DMTF/Redfishtool" # where to find redfishtool
        self.magic="12345"                      # used for debug to test for a known parameter in this object
        self.UNAUTHENTICATED_API=1              # unauthenticated API that doesn't send credentials in body data
        self.AUTHENTICATED_API=2                # authenticated API that doesn't send credentials in body data
        self.AUTHENTICATED_WITH_CREDENTIALS_API=3 # Authenticated API that sends credentials eg passwd update, add user
        self.UNAUTHENTICATED_WITH_CREDENTIALS_API=4 # session login (unauthenticated) but sends credentials
        self.authValidValues=["None", "Basic", "Session"]
        self.secureValidValues=["Never", "IfSendingCredentials", "IfLoginOrAuthenticatedApi", "Always"]
        self.supportedVersions=["v1"]      # list of RedfishProtocolVersions that this program supports
        self.MaxNextLinks=10                # max number of requests allowed with NextLink
        self.dfltPatchPostPutHdrs = {'OData-Version': '4.0', 'Content-Type': 'application/json', 'Accept': 'application/json'  }
        self.dfltGetDeleteHeadHdrs = {'Accept': 'application/json', 'OData-Version': '4.0' }


        # options and argument read from commandline options
        #    these are all set or updated by Main and remain constant for all APIs called for the cmd
        self.verbose=0
        self.status=0
        self.help=False
        self.quiet=False
        self.user=""
        self.password=""
        self.rhost=None
        self.token=None
        self.protocolVer="v1"
        self.auth="Basic"  # or "Session" using Basic as default now
        self.timeout=10         # http transport timeout in seconds, stored as int here
        self.checkProtocolVer=False  # if -C option, then we need to check/verify the protocol ver. dflt=false

        # more option parsing variables
        self.prop=None
        self.requestMethod=None  #used by raw subcommand
        self.requestData=None    #used by raw subcommand
        self.Id=None
        self.firstOptn=False
        self.gotIdOptn=False
        self.IdOptnCount=0
        self.gotPropOptn=False
        self.oneOptn=False
        self.allOptn=False
        self.gotMatchOptn=False
        self.matchProp=None
        self.matchValue=None
        
        self.IdLevel2=None
        self.gotIdLevel2Optn=False
        self.IdLevel2OptnCount=0
        
        self.gotMatchLevel2Optn=False
        self.matchLevel2Prop=None
        self.matchLevel2Value=None

        self.linkLevel2=None  # -l <link> or --link=<link>
        
        self.Link=None   # -L <Link> or --Link=<link>
        self.configFile=""      
        self.secure="IfLoginOrAuthenticatedApi" #Never
        self.waitTime=3
        self.waitNum=1
        self.headers=None
        self.dbgFlag=0
        self.subcommand=""
        self.subcommandArgv=""

        # transport parameters -- set by transport based on options and GetVersions
        #     these remain constant for all APIs called for the command
        self.rhostVersions=None
        self.rootPath=None
        self.rootUri=None
        self.rootResponseDict=None
        self.rhostSupportedVersions=None
        self.versionToUse=None
        
        # API parameters that are calculated for each (multiple) API call used to execute the cmd
        self.scheme=None   #not used any longer
        self.scheme0=None  #not used any longer
        self.apiType=None
        #self.sessionId=None

        # addl session login parameters
        self.sessionId=None
        self.sessionLink=None
        self.authToken=None
        self.cleanupOnExit=True

        # measured execution time
        self.elapsed=None

        requests.packages.urllib3.disable_warnings()

             
    # calculate the user-specified minimum security scheme based on APItype and --Secure options
    # usage:    userSpecifiedScheme=rft.getApiScheme(apiType)
    # self.secureValidValues=["IfSendingCredentials", "IfLoginOrAuthenticatedApi", "Always", "Never"]
    def getApiScheme(self,apiTypeIn):
        scheme=None
        if( self.secure == "Always" ):
            scheme="https"
        elif( self.secure == "Never" ):
            scheme="http"
        elif( (self.secure == "IfSendingCredentials") and
            (   (apiTypeIn==self.AUTHENTICATED_WITH_CREDENTIALS_API) or 
                (apiTypeIn==self.UNAUTHENTICATED_WITH_CREDENTIALS_API) or
                ( (apiTypeIn==self.AUTHENTICATED_API) and (self.auth == "Basic") ) ) ):
            scheme="https"
        elif( (self.secure=="IfLoginOrAuthenticatedApi") and 
            (   (apiTypeIn==self.AUTHENTICATED_API) or
                (apiTypeIn==self.UNAUTHENTICATED_WITH_CREDENTIALS_API)  )):
                scheme="https"
        else:
            scheme="http"
            #print("else HTTP dflt")
        return(scheme)  #return ok
            
    def getVersionsAndSetRootPath(self,rft,forceCheckProtocolVer=False):
        # Read the Redfish Versions API (/redfish) to determine which protocol versions the service supports
        # The proper ServiceRoot Path returned for each protocol version eg:  { "v1": "/redfish/v1" }.
        # If self.redfishProtocolVersion="Latest" (which is the default), we will select the latest version
        #    that is supported by both the remote redfish service AND this program.
        # If the -R <redfishVer> option is called where the user specifies a version to use,
        #    we must verify that the remote redfish client supports that version and that this program supports it
        # Initially, only "v1" is specified, so this program and services should all support only v1.
        #    But it is important that client code be coded to negotiate properly to be compatible with future services
        # The versions supported by this program are in a list supportedVersions=["v1",...]
        # If the -W <waitNum>:<waitTime> was specified with waitNum > 1, then we will loop executing the /redfish
        #    API up to waitNum times with http "connection" timeout=waitTime for the service to respond
        # Note that we will always send at least one request to /redfish API even if waitNum=0.
        #    Waiting for the service to be up this way can aid in sending commands to services connected through
        #    shared NICs where the network path can goes away for a few seconds as the host OS boots and NICs
        #    reset and authenticate with switches. If we wait until we have a connection to start, most false
        #    failures are avoided (although the connection can also go away during cmd exec-but that window is smaller
        rft.printVerbose(5,"getVersionsAndRootPath: read versions from rhost")

        # if already executed, just return
        if( rft.rootPath is not None):
            rft.printVerbose(5,"Transport.getRootPath: path already exists")
            #return(0,None,False,None)
        if( rft.rhost is None):
            rft.printErr("Transport: -r rHost was not specified and is required by this command. aborting")
            return(5,None,False,None)

        # if the checkProtocol flag is not set true, dont query rhost for /redfish version
        # just use what was passed in with -R <redfishVersion> or the default "v1"
        if( (rft.checkProtocolVer is False) and (forceCheckProtocolVer is not True) ):
            # If here, checkProtocolVer is false.  we will generate the rootURL and hope for the best
            # This saves additional Get /redfish query that 99.9% of time is ok
            # the Get Versions API (GET /redfish) calls the routine with forceCheckProtocolVer=True
            rft.rootPath=urljoin("/redfish/", (rft.protocolVer + "/") )
            #id of protocolVersion is v1, rft.rootPath="/redfish/v1/"

            # calculate the rootUri including scheme,rhost,rootPath properly
            scheme=rft.getApiScheme(rft.UNAUTHENTICATED_API)
            scheme_tuple=[scheme,rft.rhost, rft.rootPath, "","",""]
            rootUrl=urlunparse(scheme_tuple)
            rft.rootUri=rootUrl
            # save parameters
            rft.rhostSupportedVersions=None
            rft.versionToUse=rft.protocolVer
            rft.printVerbose(5,"Transport.getRootPath: protocolVer to use={},  rootPath={}".format(rft.versionToUse, rft.rootPath))
            return(0,None,False,None) # return ok

        # create scheme based on input parameters and apiType(set here) using setApiScheme() function above.
        scheme=rft.getApiScheme(rft.UNAUTHENTICATED_API)

        #define header and put the full URL together
        hdrs = dict(rft.dfltGetDeleteHeadHdrs)

        scheme_tuple=[scheme, rft.rhost, "/redfish", "","",""]
        url=urlunparse(scheme_tuple)                # url= "http[s]://<rhost>[:<port>]/redfish"
        
        rft.printVerbose(5,"Transport.getRootPath: url={}".format(url))

        # now send request to rhost, with retries based on -W <waitNum>:<waitTime> option.
        # handle exceptions including timeouts.
        success=None
        r=None
        for attempt in range(0,rft.waitNum):
            try:
                rft.printVerbose(3,"Transport:getVersions: GET {}".format(url))
                t1=time.time()
                r = requests.get(url, headers=hdrs, verify=False, timeout=(rft.waitTime,rft.timeout))  # GET ^/redfish
                t2=time.time()
                rft.elapsed = t2 - t1
                # print request headers
                rft.printStatus(3,r=r,authMsg=None)

            except requests.exceptions.ConnectTimeout:
                # connect timeout occured.  try again w/o sleeping since a timeout already occured
                rft.printVerbose(5,"Tranport: connectTimeout, try again")
                pass
            except (socket.error):
                # this exception needed as requests is not catching socket timeouts
                #  especially "connection refused" eg web server not started
                # issue: https://github.com/kennethreitz/requests/issues/1236
                # Nothing timed out.  this is a connect error. So wait and retry
                rft.printVerbose(5,"Tranport: socket.error,  wait and try again")
                time.sleep(rft.waitTime)
            except (requests.exceptions.ReadTimeout):
                # read timeout occured. This shouldn't happen, so fail it
                rft.printErr("Transport: Fatal timeout waiting for response from rhost")
                return(5)
            except (requests.exceptions.ConnectionError):
                # eg DNS error, connection refused.  wait and try again
                rft.printVerbose(5,"Tranport: ConnectionError, wait and try again")
                time.sleep(rft.waitTime)
            except requests.exceptions.RequestException as e:
                # otherl requests exceptions.  return with error
                rft.printErr("Transport: Fatal exception trying to connect to rhost. Error:{}".format(e))
                return(5,None,False,None)
            
            else:  # if no exception
                #print the response status (-ssss)
                rft.printStatus(4,r=r,authMsg=None)
                rft.printStatus(5,r=r,authMsg=None)
                
                if( r.status_code==requests.codes.ok):
                    success=True
                    break

                
        if not success:   # retries were exceeded w/o success
            rft.printErr("Transport: Cant connect to remote redfish service. Aborting command")
            if( (r is not None) and ( r.status_code >= 400 )):
                rft.printStatusErr4xx(r.status_code)
            else:
                rft.printErr("Transport Error. No response")
            return(5,None,False,None)
        
        #print the response status (-ssss)
        rft.printStatus(4,r=r)
        
        # if here, r is the response to the GET /redfish  request
        rft.printVerbose(5,"Transport: getVersionsAndRootPath: Get /redfish: statusCode: {}".format(r.status_code))
            
        # load it into a python dictionary
        try:
            rft.rhostVersions=json.loads(r.text)
        except ValueError:
            rft.printErr("Transport: Error reading Versions from /redfish: Bad Json:{}".format(r.text))
            return(5,None,False,None)

        #create a list of version numbers that the service supports from the response dict.
        # this will look something like ["v1", "v2"...]
        serviceSupportedVersions=list(rft.rhostVersions)

        # now determine the right protocol to use based on -P protocolVer option (default=Latest), the versions that
        #   the remote service supports, and the versions that this program supports.
        rfVer=None  # rfVer holds the version we select.  It will be a string eg "v1"
        
        # first calculate the version to use for the default "-P Latest" option setting--means "use the latest common protocol ver"
        if(rft.protocolVer=="Latest"):
            #reverse sort the supportedVersions list for this program (latest means highest first in list
            reverseSortedRftVersions=list(rft.supportedVersions)  # make a copy of the list. this list looks like ["v1","v2"...]
            
            # now reverse sort it based on the number (the 1 in v1).  the result looks like ["v2", "v1", ...]
            reverseSortedRftVersions.sort(key=lambda x: int(x[1:]),reverse=True)  # reverse sort it based on number (the 1 in v1)
            #print("rf",reverseSortedRftVersions)

            #search to find latest version supported by both redfishtool and the remote service
            for ver in reverseSortedRftVersions:
                if ver in serviceSupportedVersions:
                    rfVer=ver
                    break
            if( not rfVer):
                rft.printErr("Transport: Error: no match looking for latest common protocol version")
                rft.printErr("  between {} and remote service".format(rft.program),noprog=True)

        # second, calculate the version to use if the user specifies a specific version number eg -P v2
        else:  # user explicitely specified a version to use.  Check if service supports it
            if rft.protocolVer in rft.supportedVersions:
                if rft.protocolVer in serviceSupportedVersions:
                    rfVer=rft.protocolVer
                else:
                    rft.printErr("Error: protocol version {} is not supported by remote redfish service".format(rft.protocolVer))
                    rft.printErr("  Versions supported by remote service: {}".format(serviceSupportedVersions),noprog=True)

            else:
                rft.printErr("Error: protocol version {} is not supported by {}".format( rft.protocolVer,rft.program))
                rft.printErr("  Versions supported by {}: {}".format(rft.program,rft.supportedVersions),noprog=True)

        if( not rfVer):  # more error messages if error
            return(4,None,False,None)

        # If here, we have a valid protocol version
        # get the service root path for that version from the Versions response
        # save the service root path in transport object
        rft.rootPath=self.rhostVersions[rfVer]
        rft.rootUri=r.url
        #rft.rootUri=self.scheme+self.rhost+self.rootPath
        rft.rhostSupportedVersions=list(serviceSupportedVersions)
        rft.versionToUse=rfVer
        rft.printVerbose(5,"Transport.getRootPath: protocolVer to use={},  rootPath={}".format(rfVer, rft.rootPath))
        return(0,r,True,rft.rhostVersions) # return ok

    #'''
    # the main workhorse send/receive request function used to send gets, patches, posts, deletes...
    # handles the following processing within this function:
    #  x-- getting minimum security scheme based on command type input
    #  x-- reconcilling min scheme with baseUrl scheme (will join to use the most secure)
    #  x-- joining with relative path (but not allowing scheme less than min calculated if relPath (input) included a scheme
    #  1-- setting headers based on: authenticationType, method, etag, dataType for the command
    #  1-- add appropriate authentication for commandType, and command options
    #  -- calling the Requests function with additional kwargs for header, data
    #  -- if a collection Get where not all members are returned, looping to get all of the members
    #  1-- processing Requests exceptions correctly
    #  1-- loading json into Dict with exception handling
    #  -- printing error messages from Requests or json.loads, and setting return codes
    #  x-- returning standard tuple: rc,r,j,d
    #       rc,r,j,d =(returnCode(int: 0=ok), RequestsResponse, jsonData(True/False), data (type: None|dict|text))
    # Syntax:  rc,r,j,d = rftSendRecvRequest( apiType, method, baseUrl, relPath=None, jsonData=True,  prop=None,
    #                                     collection=False, loadData=True, redirect=True, data=None (inputdata),
    #                                     getEtagFirst=False (for patches, get etag from rhost 1st),**kwargs)                                 
    # todo:
    # 1.  exception handling on urlparse, urlunparse, urljoin

    def rftSendRecvRequest( rft, apiType, method, baseUrl, relPath=None, data=None, jsonData=True,  prop=None,
                            redirects=True, reqData=None, verify=False,
                            headersInput=None, **kwargs ):

        rft.printVerbose(5,"Transport.rftProcessRequest: method={}, baseUrl={}, rpath={}".format(method,baseUrl,relPath))
        rft.printVerbose(5,"Transport.rftProcessRequest: apiType={}".format(apiType))
        # get scheme based on input parameters and apiType(set here) using getApiScheme() function above.
        userSpecifiedScheme=rft.getApiScheme(apiType)

        # parse url into its parts: scheme, netloc, path, params, query fragment
        # the assumption is that baseUrl was the url sent back from the previous request--might have been a redirect
        # urlp is a urlparse Response class
        urlp=urlparse(baseUrl)

        # if baseUrl scheme is https, use https no matter what the user specified scheme is.
        #     this got upgraded from the service side as a redirect.
        #     but we don't allow service to redirect us to a less secure scheme than the user specified one
        if( urlp.scheme == 'https' ):
            scheme='https'
        else:
            scheme=userSpecifiedScheme;

        # now unparse the api with most secure scheme
        scheme_tuple=[scheme, urlp.netloc, urlp.path, "","",""]
        urlBase2=urlunparse(scheme_tuple)
        
        #join the baseURL and relative path passed in
        #  note that if no relPath was specified, it defaults to None, which joins nothing to base URL
        # this re-joining logic makes redfishtool correctly follow normal relative URL rules.
        # although redfish does not allow local relative paths, redfishtool will work if they were implemented
        url=urljoin(urlBase2,relPath)
        
        #define headers.
        # the transport will use defaults specified in the Transport defaults properties dfltXYZHdrs depending on method XYZ.
        # if headers were passed in by a command function in property headersInput, then add them or modify default with those values
        # And also: if addl headers were specified in the commandline -H <hdrs> option, add them to the defaults above

        # ex self.dfltPatchPostPutHdrs  = {"content-type": "application/json", "Accept": "application/json", "OData-Version": "4.0" }
        # ex self.dfltGetDeleteHeadHdrs = {"Accept": "application/json", "OData-Version": "4.0" }


        # get default headers based on the method being called
        if( (method == 'PATCH') or (method == 'POST') or (method == 'PUT') ):
            hdrlist=rft.dfltPatchPostPutHdrs
        else:  # method is GET, DELETE, HEAD
            hdrlist=rft.dfltGetDeleteHeadHdrs

        # make copy of the dict.  Otherwise Requests is sometimes not adding addl headers.  a byte vs string bug in requests
        hdrs=dict(hdrlist)

        # if a list of headers was sent in in the function, then add them (or update defaults with new values)
        if( headersInput is not None):  # headers passed in from a calling function overrides defaults
            for key in headersInput:
                hdrs[key]=headersInput[key]
            
        # check and see if an additional/alternate hdr value was passed in on CLI as -H option
        if( rft.headers is not None):
            # a user passed-in an addl header using -H {A:B, C:D},
            # This changes the current value or adds the new header if it doesn't already exist
            for key in rft.headers:
                hdrs[key]=rft.headers[key]
                           
        #print("hdrs:{}".format(hdrs))
        hdrs['Accept-Encoding']=None
                
        #calculate the authentication method
        authType=None
        authMsg=None

        rft.printVerbose(5,"Transport.ProcessRequest: url={}".format(url))
        authenticatedApi=None
        if( (apiType==rft.UNAUTHENTICATED_API) or (apiType==rft.UNAUTHENTICATED_WITH_CREDENTIALS_API)):
            authenticatedApi=False
        elif( (apiType==rft.AUTHENTICATED_API) or (apiType==rft.AUTHENTICATED_WITH_CREDENTIALS_API)):
            authenticatedApi=True
            
        if( (authenticatedApi is False) or (rft.auth=="None") ):
            authType=None
            authMsg=None
        elif( (authenticatedApi is True) and (rft.auth=="Basic")):
            authType=HTTPBasicAuth(rft.user, rft.password)
            authMsg="Basic"
        elif( (authenticatedApi is True) and (rft.auth=="Session")):
            if( rft.authToken is None):   # ie: we dont already have a token that was passed in or previously loggedin
                rc,r,j,d=rft.rfSessionLogin(rft)  #cleanup=true tells the transport to logout at end of cmd
                #this will save the authToken at rft.token, and sessionLink at rft.sessionLink
                if( rc != 0):  # error logging in
                    return(rc,r,j,d)
            # now we should have a valid auth token. create an instance of this auth
            authMsg="Session"
            authType=RfSessionAuth(rft.authToken)
        else:  # unknown auth type or API
            rft.printErr("Transport: Invalid auth type specified, aborting command")
            return(4,None,False,None)
        
        # now send request to rhost, with retries based on -W <waitNum>:<waitTime> option.
        # handle exceptions including timeouts.
        success=None
        r=None
        respd=None
        nextLink=True
        for attempt in range(0,rft.MaxNextLinks):
            try:
                rft.printVerbose(3,"Transport:SendRecv:    {} {}".format(method,url))
                t1=time.time()
                r = requests.request(method, url, headers=hdrs, auth=authType, verify=verify, data=reqData,
                                     timeout=(rft.waitTime,rft.timeout),**kwargs)  # GET ^/redfish
                t2=time.time()
                rft.elapsed = t2 - t1
                # print request headers
                rft.printStatus(3,r=r,authMsg=authMsg)

            except requests.exceptions.ConnectTimeout:
                # connect timeout occured.  try again w/o sleeping since a timeout already occured
                rft.printVerbose(5,"Tranport: connectTimeout, try again")
                return(5,r,False,None)
            except (socket.error):
                # this exception needed as requests is not catching socket timeouts
                #  especially "connection refused" eg web server not started
                # issue: https://github.com/kennethreitz/requests/issues/1236
                # Nothing timed out.  this is a connect error. So wait and retry
                rft.printVerbose(5,"Tranport: socket.error,  wait and try again")
                time.sleep(rft.waitTime)
                return(5,r,False,None)
            except (requests.exceptions.ReadTimeout):
                # read timeout occured. This shouldn't happen, so fail it
                rft.printErr("Transport: Fatal timeout waiting for response from rhost")
                return(5,r,False,None)
            except (requests.exceptions.ConnectionError):
                # eg DNS error, connection refused.  wait and try again
                rft.printVerbose(5,"Tranport: ConnectionError, wait and try again")
                time.sleep(rft.waitTime)
                return(5,r,False,None)
            except requests.exceptions.RequestException as e:
                # otherl requests exceptions.  return with error
                rft.printErr("Transport: Fatal exception trying to connect to rhost. Error:{}".format(e))
                return(5,r,False,None)
            else:  # if no exception
                rc=0
                #print the response status (-ssss)
                rft.printStatus(4,r=r,authMsg=authMsg)
                rft.printStatus(5,r=r,authMsg=authMsg)
                #rft.printStatus(5,data=r.text)  # print the response data (-ssssss)
                
                if( r.status_code >= 400):
                    rft.printStatusErr4xx(r.status_code)
                    return(5,r,False,None)
                if( r.status_code == 302):
                    rft.printErr("Transport: Redirected: status_code: {}".format(r.status_code))
                    return(5,r,False,None)

                if( r.status_code==204):
                    success=True
                    return(rc,r,False,None)
                elif( (r.status_code==200) and (method=="HEAD") ):
                    success=True
                    return(rc,r,False,None)
                elif((r.status_code==200) or (r.status_code==201) ):  
                    if( jsonData is True):
                        try:
                            d=json.loads(r.text)
                        except ValueError:
                            rft.printErr("Transport: Error loading Data: uri: {}".format(url))
                            respd=None
                            rc=5
                            jsonData=False
                            return(rc,r,False,None)
                    else:
                        d=r.text #xml data
                        return(rc,r,jsonData,d)

                    #if here, no error, and its json data
                    # if specific property was specified, filter here
                    if(( method == "GET") and (prop is not None) ):
                        rc,r,j,d=rft.getPropFromDict(rft,r,d,prop)
                        return(rc,r,j,d)
                    if( (respd is None) and ( not "Members@odata.nextLink" in d)):
                        # normal case where single response w/ no next link
                        return(rc,r,jsonData,d)
                    elif( (respd is None ) and ("Members@odata.nextLink" in d)):
                        #then this is the 1st nextlink
                        respd=d
                        url=urljoin(urlBase2,d["Members@odata.nextLink"])
                        #dont return--keep looping
                    elif( not respd is None )and ("Members@odata.nextLink" in d):
                        # this is 2nd or later response-that has a nextlink
                        respd["Members"]= respd["Members"] + d["Members"]
                        url=urljoin(urlBase2,d["Members@odata.nextLink"])
                    elif( not respd is None )and (not "Members@odata.nextLink" in d):
                        # this final response to a multi-response request, and it has not nextlink
                        respd["Members"]= respd["Members"] + d["Members"]
                        return(rc,r,jsonData,respd)
                elif( r.status_code!=200):
                    success=False
                    rft.printErr("Transport: processing response status codes")
                    return(5,r,False,None)



    def getPropFromDict(self,rft,r,d,prop):
        if(prop in d):
            propDict={prop: d[prop]}
        else:
            rft.printErr("Error: the resource does not have a {} property".format(prop))
            return(4,None,False,None)
        return(0,r,True,propDict)


        
    #  function to return service versions from GET /redfish as a python Dictionary
    #  returns (rc, rhostVersions) to lib main
    #  returns (rc) to CLI main
    def getVersions(self,rft,cmdTop=False):
        rft.printVerbose(4,"Transport: in getVersions")
        if(rft.help):
            print(" {} versions | redfish [-vh]   -- get redfishProtocol versions supported by rhost".format(rft.program))
            return(0,None,False,None)
        rc,r,j,d=rft.getVersionsAndSetRootPath(rft, forceCheckProtocolVer=True)
        if(rc != 0):
            return(rc,None,False,None)

        # note that getVersionAndSetRootPath() returns the versions data as d,
        #  so there is no need to call GET /redfish again.  we have it at rft.versionsDict
        #  So just return it with the response
      
        # create the addlData dict:
        rft.printVerbose(2,"Additional Data:",skip1=True)
        rft.printVerbose(2,"   redfishtool Supported Redfish Protocol Versions: {}".format(rft.supportedVersions))
        rft.printVerbose(2,"   rhost       Supported Redfish Protocol Versions: {}".format(rft.rhostSupportedVersions))
        rft.printVerbose(2,"   negotiated  protocol version to use:             {}".format(rft.versionToUse))
        rft.printVerbose(2,"   rootServicePath:                                 {}".format(rft.rootPath))
            
        # some command debug
        rft.printVerbose(4,"Transport:getVersions: got serviceVersions and root path")

        # if -v print header
        rft.printVerbose(1," rhost Redfish Protocol Versions: GET /redfish",skip1=True)
        return(rc,r,True,d)



    #login to rhost and get a session Id
    #authToken,sessionId=rft.rfSessionLogin()
    def rfSessionLogin(self,rft,cmdTop=False,cleanupOnExit=True):
        rft.printVerbose(4,"Transport: in SessionLogin")

        # get the URL of the Sessions  collection from the root service response
        d=rft.rootResponseDict
        loginUri=None

        #if we don't have a root resource response, then get it now
        if( d is  None ):
            # read the rootService
            svcRoot=RfServiceRoot()
            rc,r,j,d = svcRoot.getServiceRoot(rft)
            if(rc!=0):
                rft.printErr("Error: SessionLogin: could not read service root")
                return(rc,None,False,None)
            
        if( ("Links" in d) and ("Sessions" in d["Links"]) and ("@odata.id" in d["Links"]["Sessions"]) ):
            loginUri=rft.rootResponseDict["Links"]["Sessions"]["@odata.id"]
            #print("loginUri:{}".format(loginUri))
        else:
            rft.printErr("Error: the rootService response does not have a login link: \"Links\":\"Sessions\":{{\"@odata.id\": <uri>}")
            return(4,None,False,None)

        # create the Credential structure:  { "UserName": "<username>", "Password": "<passwd>" }
        credentials={"UserName": rft.user, "Password": rft.password }
        loginPostData=json.dumps(credentials)

        # now we have a login uri,  login
        # NOTE: this is API type:UNAUTHENTICATED_WITH_CREDENTIALS_API:
        # POST the user credentials to the login URI, and read the SessionLink and SessionAuthToken from header
        rc,r,j,d=rft.rftSendRecvRequest(rft.UNAUTHENTICATED_WITH_CREDENTIALS_API, 'POST', rft.rootUri, relPath=loginUri,
                                         reqData=loginPostData)
        if(rc!=0):
            rft.printErr("Error: Session Login Failed: Post to Sessions collection failed")
            return(rc,None,False,None)        # save the sessionId and SessionAuthToken

        # SessionAuthToken is in header:     X-Auth-Token: <token>
        # the SessionLink is in header:      Location: <sessionLinkUrl>
        # the sessionId is read from the response: d["Id"]
        if( not "X-Auth-Token" in r.headers ):
            rft.printErr("Error: Session Login Failed: Post to Session collection did not return Session Token")
            return(4,None,False,None)
        if( not "Location" in r.headers ):
            rft.printErr("Error: Session Login Failed: Post to Session Collection did not return Link to session in Location hdr")
            return(4,None,False,None)

        #save auth token, sessionId, and sessionLink in transport database
        rft.authToken=r.headers["X-Auth-Token"]
        if( ( d is not None) and ( "Id" in d )):
                rft.sessionId=d["Id"]
        else:
            rft.printErr("Error: Session Login either didn't return the new session or property Id was missing ")
            return(4,None,False,None)
        rft.sessionLink=r.headers["Location"]
        rft.cleanupOnExit=cleanupOnExit
        
        rft.printStatus(3,r=r,addSessionLoginInfo=True)

        return(rc,r,j,d)
    

    
    def rfSessionDelete(self,rft,cmdTop=False,sessionLink=None):
        rft.printVerbose(4,"Transport: in Session Delete (Logout)")

        #if session link was passed-in (logout cmd) use that,  otherwise, use the saved value in the transport
        if(sessionLink is None):
            # delete this session saved in rft.sessionId, rft.sessionLink
            # delete in rft
            self.printVerbose(5,"rfSessionDelete: deleting session:{}".format(rft.sessionId))
            rft.printVerbose(4,"Transport: delete session: id:{},  link:{}".format(rft.sessionId, rft.sessionLink))
            sessionLink=rft.sessionLink
            
        # now we have a login uri,  login
        # POST the user credentials to the login URI, and read the SessionLink and SessionAuthToken from header
        rc,r,j,d=rft.rftSendRecvRequest(rft.AUTHENTICATED_API, 'DELETE', rft.rootUri, relPath=sessionLink)
        if(rc!=0):
            rft.printErr("Error: Logout: Session Delete Failed: Delete to Sessions collection failed")
            rft.printErr("  sessionId:{}".format(sessionLink))
            return(rc,None,False,None)

        # save the sessionId and SessionAuthToken to None
        self.sessionId=None
        self.sessionLink=None
        rc=0
        return(rc,r,False,None)

    
    def rfCleanup(self,rft):       
        #if we created a temp session in this cmd, logout
        self.printVerbose(5,"rfCleanup:Cleaningup session: {}".format(self.sessionId))
        if((rft.cleanupOnExit is True ) and (rft.sessionId is not None) ):

            #delete the session
            rc,r,j,d=rft.rfSessionDelete(rft)
            #nothing else to do for now
            return(rc)
        else:
         return(0)


    def printVerbose(self,v,*argv, skip1=False, printV12=True,**kwargs): 
        if(self.quiet):
            return(0)
        if( (v==1 or v==2) and (printV12 is True) and (self.verbose >= v )):
            if(skip1 is True):  print("#")
            print("#",*argv, **kwargs)
        elif( (v==1 or v==2) and (self.verbose >4 )):
            if(skip1 is True):  print("#")
            print("#",*argv, **kwargs)            
        elif((v==3 ) and (printV12 is True) and (self.verbose >=v)):
            if(skip1 is True):  print("#")
            print("#REQUEST:",*argv,file=sys.stdout,**kwargs)
        elif((v==4 or v==5) and (self.verbose >=v)):
            if(skip1 is True):  print("#")
            print("#DB{}:".format(v),*argv,file=sys.stdout,**kwargs)
        elif( v==0):  #print no mater value of verbose, but not if quiet=1
            if(skip1 is True):  print("")
            print(*argv, **kwargs)
        else:
            pass

        sys.stdout.flush()
        #if you set v= anything except 0,1,2,3,4,5 it is ignored


    def printStatus(self, s, r=None, hdrs=None, authMsg=None, addSessionLoginInfo=False): 
        if(self.quiet):
            return(0)
        if(   (s==1 ) and (self.status >= s ) and (r is not None) ):
            print("#STATUS: Last Response: r.status_code: {}".format(r.status_code))
        elif( (s==2 ) and (self.status >= s ) and (r is not None) ):
            print("#STATUS: Last Response: r.url: {}".format(r.url))
            print("#STATUS: Last Response: r.elapsed(responseTime): {0:.2f} sec".format(self.elapsed))
        elif( (s==3 ) and (self.status >= s ) and (r is not None) ):
            if( addSessionLoginInfo is True):
                print("#____AUTH_TOKEN:  {}".format(self.authToken))
                print("#____SESSION_ID:  {}".format(self.sessionId))
                print("#____SESSION_URI: {}".format(self.sessionLink))
            else:
                print("#REQUEST:  {}     {} ".format(r.request.method, r.request.url))
                print("#__Request.Headers:  {}".format(r.request.headers))
                print("#__Request AuthType: {}".format(authMsg))
                print("#__Request Data: {}".format(r.request.body))
                print("#__Response.status_code: {},         r.url: {}".format(r.status_code,r.url))
                print("#__Response.elapsed(responseTime): {0:.2f} sec".format(self.elapsed))
        elif( (s==4 ) and (self.status >= s ) and (r is not None) ):
            print("#__Response.Headers: {}".format(r.headers))
        elif( (s==5 ) and (self.status >= s )  ):
            print("#__Response. Data: {}".format(r.text))
        else:
            pass
            #if you set v= anything except 1,2,3,4,5 it is ignored
        sys.stdout.flush()
        



    def printErr(self,*argv,noprog=False,prepend="",**kwargs):
        if( self.quiet == False):
            if(noprog is True):
                print(prepend,*argv, file=sys.stderr, **kwargs)
            else:
                print(prepend,"  {}:".format(self.program),*argv, file=sys.stderr, **kwargs)
        else:
            pass
        
        sys.stderr.flush()
        return(0)


    def printStatusErr4xx(self, status_code,*argv,noprog=False, prepend="",**kwargs):
        if(self.quiet):
            return(0)
        if( status_code < 400 ):
            self.printErr("status_code: {}".format(status_code))
        else:
            if( status_code == 400 ):
                errMsg="Bad Request"
            elif( status_code == 401 ):
                errMsg="Unauthorized"
            elif( status_code == 402 ):
                errMsg="Payment Required ?"
            elif( status_code == 403 ):
                errMsg="Forbidden--user not authorized to perform action"
            elif( status_code == 404 ):
                errMsg="Not Found"
            elif( status_code == 405 ):
                errMsg="Method Not Allowed"
            elif( status_code == 406 ):
                errMsg="Not Acceptable"
            elif( status_code == 407 ):
                errMsg="Proxy Authentication Required"
            elif( status_code == 408 ):
                errMsg="Request Timeout"
            elif( status_code == 409 ):
                errMsg="Conflict"
            elif( status_code == 410 ):
                errMsg="Gone"
            elif( status_code == 411 ):
                errMsg="Length Required"
            elif( status_code == 412 ):
                errMsg="Precondition Failed"
            elif( status_code == 413 ):
                errMsg="Request Entity Too Large"
            elif( status_code == 414 ):
                errMsg="Request-URI Too Long"
            elif( status_code == 415 ):
                errMsg="Unsupported Media Type"
            elif( status_code == 416 ):
                errMsg="Requested Range Not Satisfiable"
            elif( status_code == 417 ):
                errMsg="Expectation Failed"
            elif( status_code < 500 ):
                errMsg=""
            elif( status_code >=500 ):
                errMsg="Internal Server Error"
            elif( status_code >=501 ):
                errMsg="Not Implemented"
            else:
                errMsg=""
            self.printErr("Transport: Response Error: status_code: {} -- {}".format(status_code, errMsg ))
            
        sys.stdout.flush()
        return(0)



    def getPathBy(self,rft, r, coll):
        if('Members'  not in coll):
            rft.printErr("Error: getPathBy: no members array in collection")
            return(None,1,None,False,None)
        else:
            numOfLinks=len(coll['Members'])
            if( numOfLinks == 0 ):
                rft.printErr("Error: getPathBy: empty members array")
                return(None,1,None,False,None)
            
        if(rft.Link is not None):
            for i in range (0,numOfLinks):
                if( '@odata.id'  not in coll['Members'][i] ):
                    rft.printErr("Error: getPathBy --Link option: improper formatted link-no @odata.id")
                    return(None,1,None,False,None)
                else:
                    path=coll['Members'][i]['@odata.id']
                    if( path == rft.Link ):
                        return(path,0,None,False,None)
                    
            #if we get here, there was no link in Members array that matched -L <link>
            rft.printErr("Error: getPathBy --Link option: none of the links in the collection matched -L<link>")
            return(None,1,None,False,None)

        elif(rft.oneOptn):
            if(numOfLinks > 1):
                rft.printErr("Error: getPathBy --One option: more than one link in members array")
                return(None,1,None,False,None)
            if('@odata.id'  not in coll['Members'][0] ):
                rft.printErr("Error: getPathBy --One option: improper formatted link-no @odata.id")
                return(None,1,None,False,None)
            else:
                return(coll['Members'][0]['@odata.id'],0,None,False,None)

        elif( rft.firstOptn and not rft.gotMatchOptn):
            if( '@odata.id'  not in coll['Members'][0] ):
                rft.printErr("Error: getPathBy --First option: improper formatted link-no @odata.id")
                return(None,1,None,False,None)
            else:   
                return(coll['Members'][0]['@odata.id'],0,None,False,None)

        elif(rft.gotMatchOptn):
            baseUrl=r.url
            matchedPath=None
            matches=0
            for i in range (0,numOfLinks):
                if( '@odata.id'  not in coll['Members'][i] ):
                    rft.printErr("Error: getPathBy --Id or --Match option: improper formatted link-no @odata.id")
                    return(None,1,None,False,None)
                else:
                    path=coll['Members'][i]['@odata.id']
                    rc,r,j,d=rft.rftSendRecvRequest(rft.AUTHENTICATED_API, 'GET', baseUrl, relPath=path)
                    if(rc==0):  # if matchProp found
                        if( d[rft.matchProp] == rft.matchValue ):
                            matchedPath=path
                            matches +=1
                            if( matches > 1 ):
                                rft.printErr("Error: getPathBy --Id or --Match option: failed: found multiple matches.")
                                return(None,1,None,False,None)
                            if(rft.firstOptn):
                                return(matchedPath,rc,r,j,d)
                        else:
                            rft.printVerbose(4,"Transport:getPathBy:Match: failed match: matchProp={}, matchValue={}, readValue={}".format(rft.matchProp,rft.matchValue,d[rft.matchProp]))
                            pass
                    else:    # the request to this member failed
                        rft.printErr("Error: getPathBy --Id or --Match option: failed request to read collection member.")
                        pass
            #after looping over all members in the array,
            #if here, if we got a match, return the path.  If not, then no match was found. return none
            if( matches > 0 ):
                return(matchedPath,rc,r,j,d)
            else:
                rft.printErr("Error: getPathBy --Id or --Match option: no match found in collection")
                return(None,1,None,False,None)

        else:
            rft.printErr("Transport:getPathBy: Error: incorrect option specification")
            return(None,1,None,False,None)


    # returns <path> rc, r, j, d
    def getLevel2ResourceById(self,rft, r, coll):
        if('Members'  not in coll):
            rft.printErr("Error: getPathBy2: no members array in collection")
            return(None,1,None,False,None)
        else:
            numOfLinks=len(coll['Members'])
            if( numOfLinks == 0 ):
                rft.printErr("Error: getPathBy2: empty members array")
                return(None,1,None,False,None)
            
        if(rft.linkLevel2 is not None):
            for i in range (0,numOfLinks):
                if( '@odata.id'  not in coll['Members'][i] ):
                    rft.printErr("Error: getPathBy --Link option: improper formatted link-no @odata.id")
                    return(None,1,None,False,None)
                else:
                    path=coll['Members'][i]['@odata.id']
                    if( path == rft.linkLevel2 ):
                        return(path,0,None,False,None)
                    
            #if we get here, there was no link in Members array that matched -L <link>
            rft.printErr("Error: getPathBy --Link option: none of the links in the collection matched -L<link>")
            return(None,1,None,False,None)
        elif(rft.gotMatchLevel2Optn is True):
            baseUrl=r.url
            for i in range (0,numOfLinks):
                if( '@odata.id'  not in coll['Members'][i] ):
                    rft.printErr("Error: getPathBy2 --Id or --Match option: improper formatted link-no @odata.id")
                    return(None,1,None,False,None)
                else:
                    path=coll['Members'][i]['@odata.id']
                    rc,r,j,d=rft.rftSendRecvRequest(rft.AUTHENTICATED_API, 'GET', baseUrl, relPath=path)
                    if(rc==0):  # if matchProp found
                        if( d[rft.matchLevel2Prop] == rft.matchLevel2Value ):
                            return(path,rc,r,j,d)
                        else:
                            rft.printVerbose(5,"Transport:getPathBy2:Match: failed match: matchProp={}, matchValue={}, readValue={}".format(rft.matchLevel2Prop,rft.matchLevel2Value,d[rft.matchLevel2Prop]))
                            pass
                    else:    # the request to this member failed
                        pass
            #after looping over all members in the array,
            #if here, if we got a match, return the path.  If not, then no match was found. return none
            return(None,1,None,False,None)

        else:
            rft.printErr("Transport:getPathBy2: Error: incorrect option specification")
            return(None,1,None,False,None)




    # create a dict list of the collection containing: Id, <prop>, <rpath>
    # if prop=None, then the additional property is not included
    # return rc,r,j,d
    def listCollection(self, rft, r, coll, prop=None):
        if('Members'  not in coll):
            rft.printErr("Error: listCollection: no members array in collection")
            return(4,None,False,None)

        else:
            numOfLinks=len(coll['Members'])
            if( numOfLinks == 0 ):
                rft.printVerbose(4,"listCollection: empty members array: {}")
                return(0,r,True,coll) # returns an empty collection

        baseUrl=r.url

        members=list()
        for i in range (0,numOfLinks):
            if( '@odata.id'  not in coll['Members'][i] ):
                rft.printErr("Error: listCollection  improper formatted link-no @odata.id")
                return(4,None,False,None)
            else:
                path=coll['Members'][i]['@odata.id']
                rc,r,j,d=rft.rftSendRecvRequest(rft.AUTHENTICATED_API, 'GET', r.url, relPath=path)
                if(rc==0):  # if remote host returned a response
                    if( "Id" not in d ):
                        rft.printErr("Error: listCollection: no \"Id\" property in Collection member")
                        return(4,None,False,None)
                    if( prop is not None):
                        if( prop not in d):
                            propVal=None;
                        else:
                            propVal=d[prop]
                    # create a member dict. Always include  Id and path
                    listMember={"Id": d["Id"], "@odata.id": d["@odata.id"] }
                    # if a property was specified to include, add it to the list dict
                    if( prop is not None ):
                        listMember[prop]=propVal           
                    # add the member to the listd
                    members.append(listMember)

        #create base list dictionary
        collPath=urlparse(baseUrl).path
        collname=""
        if "Name" in coll:
            collname=coll["Name"]
        listd={ "_Path": collPath, "Name": collname, "Members@odata.count": numOfLinks, "Members": members }
        return(0, None, True, listd)



    # given a url to a collection, get it, and then get all members, return dict with all members expanded
    def getAllCollectionMembers(self, rft, baseUrl, relPath=None ):
        #get all members of a collection expanded
        #first get the collection
        rc,r,j,coll=rft.rftSendRecvRequest(rft.AUTHENTICATED_API, 'GET', baseUrl, relPath=relPath)
        if('Members'  not in coll):
            rft.printErr("Error: getAllCollectionMembers: no members array in collection")
            return(4,None,False,None)
        else:
            numOfLinks=len(coll['Members'])
            if( numOfLinks == 0 ):
                rft.printVerbose(4,"getAllCollectionMembers: empty members array: {}")

        #then create new members array
        #for each member in members array, read the link into a new memberEntry
        baseUrl=r.url
        expandedMembers=list()
        for i in range (0,numOfLinks):
            if( '@odata.id'  not in coll['Members'][i] ):
                rft.printErr("Error: getAllCollectionMembers  improper formatted link-no @odata.id")
                return(4,None,False,None)
            else:
                path=coll['Members'][i]['@odata.id']
                rc,r,j,d=rft.rftSendRecvRequest(rft.AUTHENTICATED_API, 'GET', baseUrl, relPath=path)
                if(rc==0):  # if remote host returned a response
                    #save this as new member entry
                    expandedMembers.append(d)

        #update base list dictionary
        coll["Members"]=expandedMembers
           
        return(rc,r,j,coll)


    # this is the generic patch routing used by Systems patch, Chassis patch, etc
    def patchResource(self, rft, r, patchData, getResponseAfterPatch=True ):
        if( patchData is None ):
            rft.printErr("Transport:Patch: patchData=None")
            return(4,None,False,None)
        if(r is  None):
            rft.printErr("Transport:Patch: resource Get response is None")
            return(4,None,False,None)
        
        #output the patch data in json to send over the network   
        reqPatchData=json.dumps(patchData)

        # check if an etag was in response header, and extract the etag value if there
        # if an etag header was returned in Get, then we must include the etag on the patch, so this is required
        # the format of etag header for redfish is:  ETag: W/"<string>" or "<string"
        # that is: double quotes are around the etag part
        # If the get returns an etag header, the patch should include header:  If-Match: W/"<string>"
        # for some patches (updating users, the service will reject it if not included

        #print("DEBUG: etag header:{}".format(r.headers))
        if( "Etag" in r.headers ):
            getEtag=r.headers["Etag"]
            patchHeaders={ "content-type": "application/json", "if-match": getEtag }
            #where in this case, the getEtag header will have double quotes embedded in it
        else:
            getEtag=None
            #patchHeaders={ "content-type": "application/json"} --dont need to specifiy this now
            patchHeaders=None

        # ideally, we should verify that the property to be patched is supported in the get response
        # but this routine leaves checking that the patch property is good up to the calling routine
        # but since the data passed in may be complex, this is not easy to do for this general patch command
        # IE, we are doing this validation in the specific command operations like boot or setIndicatorLed or setAssetTag
        # send patch to rhost
        rc,r,j,d=rft.rftSendRecvRequest(rft.AUTHENTICATED_API, 'PATCH', r.url,
                                        headersInput=patchHeaders, reqData=reqPatchData)
        # if response was good but no data retured (status_Code=204), then do another GET to get the response
        if(rc==0):
            if(r.status_code==204):  #no data returned, get the response   
                # if the getResponseAfterPatch was set False, dont get a response
                # this is used by change password to not execute after changing password since the
                if getResponseAfterPatch is True:
                    rc,r,j,d=rft.rftSendRecvRequest(rft.AUTHENTICATED_API, 'GET', r.url )
                    if( rc != 0):  return(rc,r,False,None)
                else:
                    return(rc,r,False,None)
            #now check if status_code=200, but the content is a message--not a resource representation
            #some 1.0 implementations are returning 200 with message OK
            #thus, we need to do another GET
            elif( (r.status_code==200) and (not "@odata.id" in d)):
                rc,r,j,d=rft.rftSendRecvRequest(rft.AUTHENTICATED_API, 'GET', r.url )
                if( rc != 0):  return(rc,r,False,None)
        return(rc,r,j,d) 



    #parse the @odata.type property into {namespace, version, resourceType}  following redfish syntax rules
    # returns: namespace, version, resourceType.
    # If error parsing, returns None,None,None
    def parseOdataType(self,rft,resource):
        if not "@odata.type" in resource:
            rft.printErr("Transport:parseOdataType: Error: No @odata.type in resource")
            return(None,None,None)

        resourceOdataType=resource["@odata.type"]
    
        #the odataType format is:  <namespace>.<version>.<type>   where version may have periods in it 
        odataTypeMatch = re.compile('^#([a-zA-Z0-9]*)\.([a-zA-Z0-9\._]*)\.([a-zA-Z0-9]*)$')  
        resourceMatch = re.match(odataTypeMatch, resourceOdataType)
        if(resourceMatch is None):
            rft.printErr("Transport:parseOdataType: Error parsing @odata.type")
            return(None,None,None)
        namespace=resourceMatch.group(1)
        version=resourceMatch.group(2)
        resourceType=resourceMatch.group(3)
    
        return(namespace, version, resourceType)



        
'''
TODO:
1.

'''
