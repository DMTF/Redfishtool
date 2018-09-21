# Copyright Notice:
# Copyright 2016 DMTF. All rights reserved.
# License: BSD 3-Clause License. For full text see link: https://github.com/DMTF/Redfishtool/blob/master/LICENSE.md

# redfishtool: ServiceRoot.py
#
# contains serviceRoot related subCommands and access functions
# Class RfServiceRoot
#  - getServiceRoot   GET /redfish/v1
#  - getOdataServiceDocument    GET /redfish/v1/odata
#  - getOdataMetadataDocument   GET /redfish/v1/$metadata
#
import requests
import json
from urllib.parse import urljoin, urlparse, urlunparse

class RfServiceRoot:
    def __init__(self):
        # option parsing variables
        self.serviceRootDict=None
        self.url=None
        
    def getServiceRoot(self,rft, cmdTop=False, prop=None):
        rft.printVerbose(4,"ServiceRoot: in getServiceRoot")
        
        if(rft.help):
            print(" {} {} -r<rhost> [-vh]   -- get serviceRoot resource".format(rft.program,rft.subcommand))
            return(0,None,False,None)
        
        # execute GET /redfish  to negotiate protocol version and get root path
        # rootPath is stored in rft.rootPath
        rc,r,j,d=rft.getVersionsAndSetRootPath(rft)
        if( rc!=0): return(rc,r,j,d)
        #
        if cmdTop is True:  prop=rft.prop

        # get root service.  if -P prop, showproperty
        rc,r,j,d=rft.rftSendRecvRequest(rft.UNAUTHENTICATED_API, 'GET', rft.rootUri, relPath=rft.rootPath,prop=prop)

        #save the rootService response.  The transport may need it later to get link to session and login
        rft.rootResponseDict=d
        
        if(rc==0 and cmdTop is True):
            rft.printVerbose(1," Service Root:",skip1=True, printV12=cmdTop)
        return(rc,r,j,d)

        
    def getOdataServiceDocument(self,rft,cmdTop=False):
        rft.printVerbose(4,"ServiceRoot: in getOdataServiceDocument")
        
        if(rft.help):
            print(" {} {} -r<rhost> [-vh]   -- get the Odata Service Document".format(rft.program,rft.subcommand))
            return(0,None,False,None)
        
        #get root path, scheme, and create URL
        rc,r,j,d=rft.getVersionsAndSetRootPath(rft)
        if( rc!=0): return(rc,r,j,d)

        #calculate relative path = rootPath / odata
        rpath=urljoin(rft.rootPath, "odata")
        
        rc,r,j,d=rft.rftSendRecvRequest(rft.UNAUTHENTICATED_API, 'GET', rft.rootUri, relPath=rpath)
        if(rc==0 ):
            rft.printVerbose(1," Odata Service Document:",skip1=True, printV12=cmdTop)
        return(rc,r,j,d)


        
    def getOdataMetadataDocument(self,rft,cmdTop=False):
        rft.printVerbose(4,"ServiceRoot: in getOdataMetadataDocument")
        
        if(rft.help):
            print(" {} {} -r<rhost> [-vh]   -- get the CSDL metadata document".format(rft.program,rft.subcommand))
            return(0,None,False,None)
        
        #get root path, scheme, and create URL
        rc,r,j,d=rft.getVersionsAndSetRootPath(rft)
        if( rc!=0): return(rc,r,j,d)

        #calculate relative path = rootPath / $metadata
        rpath=urljoin(rft.rootPath, "$metadata")

        # set content-type to xml  (dflt is application/json)
        hdrs = {"Accept": "application/xml", "OData-Version": "4.0" }


        rc,r,j,d=rft.rftSendRecvRequest(rft.UNAUTHENTICATED_API, 'GET', rft.rootUri, relPath=rpath, jsonData=False, headersInput=hdrs )
        if(rc==0):
            rft.printVerbose(1," Odata Metadata Document:",skip1=True,printV12=cmdTop)
        return(rc,r,j,d)

'''
TODO:
1.


'''
