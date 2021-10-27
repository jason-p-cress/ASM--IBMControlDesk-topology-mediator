#!/usr/bin/python -u

################################################################
#
# IBM Control Desk REST mediator for topology inclusion into ASM
#
# 10/1/21 - Jason Cress (jcress@us.ibm.com)
#
################################################################

import linecache
from httplib import IncompleteRead
import time
import datetime
import gc
import random
import base64
import json
import re
from pprint import pprint
import os
import ssl
import urllib2
import urllib
from collections import defaultdict
from multiprocessing import Process
import sys

##############
#
# Simple function to validate json
#
##################################

def validateJson(jsonData):
    try:
        json.loads(jsonData)
    except ValueError as err:
        return False
    return True


##############
#
# Simple function to verify if a dictionary key exists
#
######################################################

def keyExists(d, myKey): 
   return d.has_key(myKey) or any(myhaskey(dd) for dd in d.values() if isinstance(dd, dict))

##############
#
# Function to load mediator properties
#
######################################

def loadProperties(filepath, sep='=', comment_char='#'):
    """
    Read the file passed as parameter as a properties file.
    """
    props = {}
    with open(filepath, "rt") as f:
        for line in f:
            l = line.strip()
            if l and not l.startswith(comment_char):
                key_value = l.split(sep)
                key = key_value[0].strip()
                value = sep.join(key_value[1:]).strip().strip('"') 
                props[key] = value 
    return props


##############
#
# Function to verify ASM is running
#
###################################

def verifyAsmHealth():

   # Check to ensure that ASM is healthy

   method = 'GET'

   requestUrl = 'https://' + asmServerDict["server"] + ':' + asmServerDict["port"] + '/1.0/topology/healthcheck'

   authHeader = 'Basic ' + base64.b64encode(asmServerDict["user"] + ":" + asmServerDict["password"])

   try:
      request = urllib2.Request(requestUrl)
      request.add_header("Content-Type",'application/json')
      request.add_header("Accept",'application/json')
      request.add_header("Authorization",authHeader)
      request.add_header("X-TenantId",asmServerDict["tenantid"])
      request.get_method = lambda: method

      response = urllib2.urlopen(request)
      xmlout = response.read()
      if(response.getcode() == 200):
         return 0
      else:
         return response.getcode()

   except IOError, e:
      print 'Failed to open "%s".' % requestUrl
      if hasattr(e, 'code'):
         print 'We failed with error code - %s.' % e.code
      elif hasattr(e, 'reason'):
         print "The error object has the following 'reason' attribute :"
         print e.reason
         print "This usually means the server doesn't exist,",
         print "is down, or we don't have an internet connection."
      return e.code


##############
#
# Function to load ServiceNow classes of interest
#
#################################################

def loadClassList(filepath, comment_char='#'):

   ciClassList = []

   with open(filepath, "rt") as f:
      for line in f:
         l = line.strip()
         if l and not l.startswith(comment_char):
            ciClassList.append(l)
   return(ciClassList)
 

def loadIcdServer(filepath, sep=',', comment_char='#'):

   ##########################################################################################
   #
   # This function reads the ServiceNow server configuration file and returns a dictionary
   #
   ##########################################################################################

   lineNum = 0
   with open(filepath, "rt") as f:
      for line in f:
         icdServerDict = {}
         l = line.strip()
         if l and not l.startswith(comment_char):
            values = l.split(sep)
            if(len(values) < 3):
               print "Malformed server configuration entry on line number: " + str(lineNum)
            else:
               icdServerDict["server"] = values[0]
               icdServerDict["user"] = values[1]
               icdServerDict["password"] = values[2]
         lineNum = lineNum + 1

   return(icdServerDict)

def verifyAsmConnectivity(asmDict):
 
   ##################################################################
   #
   # This function verifies that the ASM server credentials are valid
   # ---+++ CURRENTLY UNIMPLEMENTED +++---
   #
   ##################################################################

   return True

def loadEntityTypeMapping(filepath, sep=",", comment_char='#'):

   ################################################################################
   #
   # This function reads the entityType map configuration file and returns a dictionary
   #
   ################################################################################

   mapDict = {}
   lineNum = 0
   
   with open(filepath, "rt") as f:
      for line in f:
         l = line.strip()
         if l and not l.startswith(comment_char):
            values = l.split(sep)
            if(len(values) < 2 or len(values) > 2):
               print "Malformed entityType map config line on line " + str(lineNum)
            else:
               mapDict[values[0].replace('"', '')] = values[1].replace('"', '')
   return mapDict

def loadStatusFilter(filepath, sep=",", comment_char='#'):

   ################################################################################
   #
   # This function reads the entityType map configuration file and returns a dictionary
   #
   ################################################################################

   statusArray = []
   lineNum = 0
   
   with open(filepath, "rt") as f:
      for line in f:
         l = line.strip()
         if l and not l.startswith(comment_char):
            statusArray.append(l)
   return statusArray

def loadRelationshipMapping(filepath, sep=",", comment_char='#'):

   ################################################################################
   #
   # This function reads the relationship map configuration file and returns a dictionary
   #
   ################################################################################

   mapDict = {}
   lineNum = 0

   with open(filepath, "rt") as f:
      for line in f:
         l = line.strip()
         if l and not l.startswith(comment_char):
            values = l.split(sep)
            if(len(values) < 2 or len(values) > 2):
               print "Malformed mapping config line on line " + str(lineNum)
            else:
               mapDict[values[0].replace('"', '')] = values[1].replace('"', '')
   return mapDict

def loadRelationshipsIgnore(filepath):

   ################################################################################
   #
   # This function reads the relationship map configuration file and returns an array
   #
   ################################################################################

   array = []
   comment_char = "#"

   lineNum = 0
   with open(filepath, "rt") as f:
      for line in f:
         l = line.strip()
         if l and not l.startswith(comment_char):
            array.append(l)
   return array


def loadAsmServer(filepath, sep=",", comment_char='#'):

   ################################################################################
   #
   # This function reads the ASM server configuration file and returns a dictionary
   #
   ################################################################################

   lineNum = 0
   with open(filepath, "rt") as f:
      for line in f:
         asmDict = {}
         l = line.strip()
         if l and not l.startswith(comment_char):
            values = l.split(sep)
            if(len(values) < 5):
               print "Malformed ASM server config line on line " + str(lineNum)
            else:
               asmDict["server"] = values[0]
               asmDict["port"] = values[1]
               asmDict["user"] = values[2]
               asmDict["password"] = values[3]
               asmDict["tenantid"] = values[4]
               if(verifyAsmConnectivity(asmDict)):
                  return(asmDict)
               else:
                  print "Unable to connect to ASM server " + asmDict["server"] + " on port " + asmDict["port"] + ", please verify server, username, password, and tenant id in " + mediatorHome + "config/asmserver.conf"

def checkAsmRestListenJob(jobName):

   method = 'GET'
   # Check to see if the ASM REST Observer listen job for this ServiceNow mediator exists....
   # Returns boolean True or False

   requestUrl = 'https://' + asmServerDict["server"] + ':' + asmServerDict["port"] + '/1.0/rest-observer/jobs/' + jobName

   authHeader = 'Basic ' + base64.b64encode(asmServerDict["user"] + ":" + asmServerDict["password"])

   try:
      request = urllib2.Request(requestUrl)
      request.add_header("Content-Type",'application/json')
      request.add_header("Accept",'application/json')
      request.add_header("Authorization",authHeader)
      request.add_header("X-TenantId",asmServerDict["tenantid"])
      request.get_method = lambda: method

      response = urllib2.urlopen(request)
      xmlout = response.read()
      return 0

   except IOError, e:
      print 'Failed to open "%s".' % requestUrl
      if hasattr(e, 'code'):
         print 'We failed with error code - %s.' % e.code
      elif hasattr(e, 'reason'):
         print "The error object has the following 'reason' attribute :"
         print e.reason
         print "This usually means the server doesn't exist,",
         print "is down, or we don't have an internet connection."
      return e.code

def createAsmRestListenJob(jobName):

   result = manageAsmRestListenJob(jobName, "create")
   return result
         
def deleteAsmRestListenJob(jobName):

   result = manageAsmRestListenJob(jobName, "delete")
   return result
         
def manageAsmRestListenJob(jobName, action):

   ###################################################################
   #
   # If ServiceNow data is to be sent into ASM through ASM's REST API,
   # create a listen job that will accept the topology data
   #
   ###################################################################
   
   if(action == "create"):
      method = "POST"
      requestUrl = 'https://' + asmServerDict["server"] + ':' + asmServerDict["port"] + '/1.0/rest-observer/jobs/listen'
   elif(action == "delete"):
      method = "DELETE"
      requestUrl = 'https://' + asmServerDict["server"] + ':' + asmServerDict["port"] + '/1.0/rest-observer/jobs/' + jobName
   else:
      print "unknown action for manageAsmRestListenJob function"
      return 0

   #requestUrl = 'https://' + asmServerDict["server"] + ':' + asmServerDict["port"] + '/1.0/rest-observer/jobs/listen'

   jsonResource = '{ "unique_id":"' + jobName + '", "type": "listen", "parameters":{"provider": "' + jobName + '"}}'

   authHeader = 'Basic ' + base64.b64encode(asmServerDict["user"] + ":" + asmServerDict["password"])
   #print "auth header is: " + str(authHeader)
   #print "pushing the following json to ASM: " + jsonResource

   try:
      request = urllib2.Request(requestUrl, jsonResource)
      request.add_header("Content-Type",'application/json')
      request.add_header("Accept",'application/json')
      request.add_header("Authorization",authHeader)
      request.add_header("X-TenantId",asmServerDict["tenantid"])
      request.get_method = lambda: method

      response = urllib2.urlopen(request)
      xmlout = response.read()
      return 0

   except IOError, e:
      print 'Failed to open "%s".' % requestUrl
      if hasattr(e, 'code'):
         print 'We failed with error code - %s.' % e.code
      elif hasattr(e, 'reason'):
         print "The error object has the following 'reason' attribute :"
         print e.reason
         print "This usually means the server doesn't exist,",
         print "is down, or we don't have an internet connection."
      return e.code

def createFileResource(resourceDict):

   #######################################################
   # 
   # Function to create a file observer entry for resource
   #
   #######################################################

   jsonResource = json.dumps(resourceDict)
   print "A:" + jsonResource

def createFileConnection(connectionDict):

   #########################################################
   # 
   # Function to create a file observer entry for connection 
   #
   #########################################################

   jsonResource = json.dumps(connectionDict)
   print "E:" + jsonResource

def createAsmResource(resourceDict, jobId):

   #######################################################
   #
   # Function to send a resource to the ASM rest interface
   #
   #######################################################

   method = "POST"

   #requestUrl = 'https://' + asmServerDict["server"] + ':' + asmServerDict["port"] + '/1.0/topology/resources'

   requestUrl = 'https://' + asmServerDict["server"] + ':' + asmServerDict["port"] + '/1.0/rest-observer/rest/resources'

   #print "SENDING CI TO REST, URL IS: " + requestUrl
   authHeader = 'Basic ' + base64.b64encode(asmServerDict["user"] + ":" + asmServerDict["password"])
   #print "auth header is: " + str(authHeader)
   jsonResource = json.dumps(resourceDict)
   #print "creating the following resource in ASM: " + jsonResource

   try:
      request = urllib2.Request(requestUrl, jsonResource)
      request.add_header("Content-Type",'application/json')
      request.add_header("Accept",'application/json')
      request.add_header("Authorization",authHeader)
      request.add_header("X-TenantId",asmServerDict["tenantid"])
      request.add_header("JobId",jobId)
      request.get_method = lambda: method

      response = urllib2.urlopen(request)
      xmlout = response.read()
      return True

   except IOError, e:
      print 'Failed to open "%s".' % requestUrl
      if hasattr(e, 'code'):
         print 'We failed with error code - %s.' % e.code
      elif hasattr(e, 'reason'):
         print "The error object has the following 'reason' attribute :"
         print e.reason
         print "This usually means the server doesn't exist,",
         print "is down, or we don't have an internet connection."
      return False


def createAsmConnection(connectionDict, jobId):

   #########################################################
   #
   # Function to send a connection to the ASM rest interface
   #
   #########################################################
   
   method = "POST"

   requestUrl = 'https://' + asmServerDict["server"] + ':' + asmServerDict["port"] + '/1.0/rest-observer/rest/references'

   authHeader = 'Basic ' + base64.b64encode(asmServerDict["user"] + ":" + asmServerDict["password"])
   #print "auth header is: " + str(authHeader)
   jsonResource = json.dumps(connectionDict)
   #print "adding the following connection to ASM: " + jsonResource

   try:
      request = urllib2.Request(requestUrl, jsonResource)
      request.add_header("Content-Type",'application/json')
      request.add_header("Accept",'application/json')
      request.add_header("Authorization",authHeader)
      request.add_header("X-TenantId",asmServerDict["tenantid"])
      request.add_header("JobId",jobId)
      request.get_method = lambda: method

      response = urllib2.urlopen(request)
      xmlout = response.read()
      return True

   except IOError, e:
      print 'Failed to open "%s".' % requestUrl
      if hasattr(e, 'code'):
         print 'We failed with error code - %s.' % e.code
      elif hasattr(e, 'reason'):
         print "The error object has the following 'reason' attribute :"
         print e.reason
         print "This usually means the server doesn't exist,",
         print "is down, or we don't have an internet connection."
      return False

def getTotalRelCount():

   method = 'GET'
   requestUrl = 'https://' + snowServerDict["server"] + '/api/now/stats/cmdb_rel_ci?sysparm_count=true'
   print("issuing relationship count query: " + requestUrl)
   authHeader = 'Basic ' + base64.b64encode(snowServerDict["user"] + ":" + snowServerDict["password"])
     
   try:
      request = urllib2.Request(requestUrl)
      request.add_header("Content-Type",'application/json')
      request.add_header("Accept",'application/json')
      request.add_header("Authorization",authHeader)
      request.get_method = lambda: method

      response = urllib2.urlopen(request)
      relCountResult = response.read()

   except IOError, e:
      print 'Failed to open "%s".' % requestUrl
      if hasattr(e, 'code'):
         print 'We failed with error code - %s.' % e.code
      elif hasattr(e, 'reason'):
         print "The error object has the following 'reason' attribute :"
         print e.reason
         print "This usually means the server doesn't exist,",
         print "is down, or we don't have an internet connection."


   relCountResultDict = json.loads(relCountResult)
   print("Found " + relCountResultDict["result"]["stats"]["count"])
   return(int(relCountResultDict["result"]["stats"]["count"]))

def fetchFileData(linenum):
   with open (mediatorHome + "/log/raw-ci.json") as rawFp:
      for index, line in enumerate(rawFp):
         if(index == linenum):
            return line
            break
   return(False)
      
   
def fetchRestData(offset, page, rsStart, maxItems):

   authHeader = 'Basic ' + base64.b64encode(icdServerDict["user"] + ":" + icdServerDict["password"])
   method = "GET"

   requestUrl = icdServerDict["server"] + '/maxrest/rest/os/mxosci/?' + statusFilter + '&_lid=' + icdServerDict["user"] + '&_lpwd=' + icdServerDict["password"] + '&_format=json&_tc=true&_maxItems=' + str(maxItems) + '&_rsStart=' + str(rsStart)
   #requestUrl = icdServerDict["server"] + '/maxrest/rest/os/mxosci/?_lid=' + icdServerDict["user"] + '&_lpwd=' + icdServerDict["password"] + '&_format=json&_tc=true&_maxItems=' + str(maxItems) + '&_rsStart=' + str(rsStart)

   print "My query URL is: " + requestUrl

   try:
      request = urllib2.Request(requestUrl)
      request.add_header("Content-Type",'application/json')
      request.add_header("Accept",'application/json')
      request.add_header("Authorization",authHeader)
      request.get_method = lambda: method

      response = urllib2.urlopen(request)
      ciDataResult = response.read()

   except IOError, e:
      print 'Failed to open "%s".' % requestUrl
      if hasattr(e, 'code'):
         print 'We failed with error code - %s.' % e.code
      elif hasattr(e, 'reason'):
         print "The error object has the following 'reason' attribute :"
         print e.reason
         print "This usually means the server doesn't exist,",
         print "is down, or we don't have an internet connection."
      return False

   return(ciDataResult)
 
def getCiData():

   ###################################################
   #
   # query ICD mxosci table and generate ASM objects
   #
   ###################################################

   global ciUniqueIdSet
   global readCisFromFile

   readCiEntries = []

   if(1==1):
 
      linenum = 0
      numCi = 0
      isMore = 1
      offset = 0
      firstRun = 1
      page = 1
      rsStart = 0
      maxItems = ciFetchLimit
   
      while(isMore):

         if(readCisFromFile == "0"):
            ciDataResult = fetchRestData(offset, page, rsStart, maxItems)
         else:
            ciDataResult = fetchFileData(linenum)
            linenum = linenum + 1
            if not ciDataResult:
               break
         
      
         #print "Result is: " + str(ciDataResult)
         if(validateJson(ciDataResult)):
            ciEntries = json.loads(ciDataResult)
            print "Number of CI entries for this fetch is: " + str(len(ciEntries["QueryMXOSCIResponse"]["MXOSCISet"]["CI"]))
            numReturned = int(ciEntries["QueryMXOSCIResponse"]["rsCount"])
            totalRecords = int(ciEntries["QueryMXOSCIResponse"]["rsTotal"])
            currentStart = int(ciEntries["QueryMXOSCIResponse"]["rsStart"])
            if(saveCisToFile == "1" and readCisFromFile == "0"):
               text_file = open(mediatorHome + "/log/raw-ci.json", "a")
               text_file.write(json.dumps(ciEntries))
               text_file.write("\n")
               text_file.close()
            for ci in ciEntries["QueryMXOSCIResponse"]["MXOSCISet"]["CI"]:
               #print "adding " + ci["name"] + " to readCiEntries..."
               evaluateCi(ci)
               #readCiEntries.append(ci)
               #print ci["Attributes"]["CINAME"]["content"] + " -=- " + ci["Attributes"]["CLASSSTRUCTUREID"]["content"]
               #print "RELATIONSHIPS:" 
               #print ci["RelatedMbos"]

            numCi = numCi + numReturned
            time.sleep(ciFetchPause)
            print "numCi is " + str(numCi) + ", totalRecords is " + str(totalRecords)
            if(numCi >= totalRecords):
               #print "no more"
               isMore = 0
            else:
               #print "is more"
               rsStart = currentStart + ciFetchLimit
               isMore = 1
         else:
            print "invalid JSON returned. We got:"
            print ciDataResult
            exit()
      
         print str(numCi) + " items in the cmdb ci table out of a total of " + str(totalRecords)


   
def evaluateCi(ci):

   ############
   # Grab additional data (cispec and relationships) and build ciList and relationshipList
   ############

   if(1==1):
   #for ci in readCiEntries:

      if ci["Attributes"]["STATUS"]["content"] in ciStatusList:
         #print json.dumps(ci)
         asmObject = {}
         asmObject["entityTypes"] = []
   
         ############
         # Add attributes to ASM object
         ############
   
         for attribute in ci["Attributes"]:
            asmObject[attribute] = ci["Attributes"][attribute]["content"]
            asmObject["uniqueId"] = ci["Attributes"]["CINUM"]["content"]
            asmObject["name"] = ci["Attributes"]["CINAME"]["content"]
            asmObject["matchTokens"] = []
            asmObject["matchTokens"].append(ci["Attributes"]["CINAME"]["content"])
   
         ############
         # Assign entityType based on entityTypeMapping configuration. If not in the mapping config file, drop
         ############
    
         if(ci["Attributes"].has_key("CLASSSTRUCTUREID")):
            if ci["Attributes"]["CLASSSTRUCTUREID"]["content"] in entityTypeMappingDict:
               asmObject["entityTypes"].append(entityTypeMappingDict[ci["Attributes"]["CLASSSTRUCTUREID"]["content"]])
            else:
               asmObject["entityTypes"].append("ignore")
         else:
            print "WARNING: found CI that does not have an associated CLASSSTRUCTUREID:"
            print json.dumps(ci)
            asmObject["entityTypes"].append("ignore")
            #exit()
            
         ############
         # Process CISPEC and CIRELATION entries
         ############
   
         if "RelatedMbos" in ci:
            if "CISPEC" in ci["RelatedMbos"]:
               for cispec in ci["RelatedMbos"]["CISPEC"]:
                  if "ALNVALUE" in cispec["Attributes"]:
                     asmObject[cispec["Attributes"]["ASSETATTRID"]["content"]] = cispec["Attributes"]["ALNVALUE"]["content"]
   
            if "CIRELATION" in ci["RelatedMbos"]:
               for relation in ci["RelatedMbos"]["CIRELATION"]:
                  #pass
                  relationDict = {}
                  relationDict["_fromUniqueId"] = relation["Attributes"]["SOURCECI"]["content"]
                  relationDict["_toUniqueId"] = relation["Attributes"]["TARGETCI"]["content"]
                  if("RELATIONNUM" in relation["Attributes"]):
                     if(relation["Attributes"]["RELATIONNUM"]["content"] in relationshipMappingDict):
                        relationDict["_edgeType"] = relationshipMappingDict[relation["Attributes"]["RELATIONNUM"]["content"]]
                     else:
                        relationDict["_edgeType"] = "connectedTo"
                  else:
                     relationDict["_edgeType"] = "connectedTo"
   
                  tempEdgesFile.write(json.dumps(relationDict) + "\n")
                  tempEdgesFile.flush()
                  
                  #if(relationDict not in relationList):
                  #   relationList.append(relationDict)
   
         if("ignore" not in asmObject["entityTypes"]):
            #ciList.append(asmObject)
            verticesFile.write("V:" + json.dumps(asmObject) + "\nW:5 millisecond" + "\n")
            verticesFile.flush()
            ciUniqueIdSet.add(asmObject["uniqueId"])
            print("Number of items in ciUniqueIdSet is " + str(len(ciUniqueIdSet)) + ", and memsize of ciUniqueIdSet is " + str(sys.getsizeof(ciUniqueIdSet)) + " bytes.")
         else:
            pass
            #print "ignoring device that is not in the CI mapping file"
      else:
         #print "This CI is not in the agreeable status list, ignoring"
         pass
      
def evaluateRelationships():          

   print "Data collection complete. Analyzing relationships and building edges file..."
   numRelations = 0

   with open(mediatorHome + "/log/tempEdgesFile.json") as fp:
      for line in fp:
         if(validateJson(line)):
            relationship = json.loads(line)
            if(relationship["_toUniqueId"] in ciUniqueIdSet and relationship["_fromUniqueId"] in ciUniqueIdSet):
               edgesFile.write("E:" + json.dumps(relationship) + "\nW:5 millisecond" + "\n")
               edgesFile.flush()
               numRelations = numRelations + 1
         else:
            print "malformed line in temporary relationship file"
   
#   for rel in relationList:
#      if(rel["_toUniqueId"] in ciUniqueIdSet and rel["_fromUniqueId"] in ciUniqueIdSet):
#         edgesFile.write("E:" + json.dumps(rel) + "\nW:5 millisecond" + "\n")
#         edgesFile.flush()

   print str(len(ciUniqueIdSet)) + " CI objects found"
   print str(numRelations) + " relationships found"
   gc.collect()
   #print "there are " + str(len(ciUniqueIdSet)) + " items in ciUniqueIdSet, while there are " + str(len(ciUniqueIdList)) + " items in ciCysIdList..."
   return()

######################################
#
#  ----   Main multiprocess dispatcher
#
######################################

if __name__ == '__main__':

   # messy global definitions in the interest of saving time..........

   global mediatorHome
   global logHome
   global configHome
   configDict = {}
   global asmDict
   asmDict = {}
   global snowServerDict
   global relationshipMappingDict
   relationshipMappingDict = {}
   global ciList
   ciList = []
   global ciUniqueIdList
   ciUniqueIdList = []
   global ciUniqueIdSet
   ciUniqueIdSet = set()
   global uniqueClasses
   uniqueClasses = set()
   global relationList
   relationList = []
   global entityTypeMappingDict
   entityTypeMappingDict = {}
   global relTypeSet
   relTypeSet = set() 
   global totalSnowCmdbRelationships
   global restJobId
   global startTime
   global ciFetchPause

   if (not os.environ.get('PYTHONHTTPSVERIFY', '') and getattr(ssl, '_create_unverified_context', None)):
      ssl._create_default_https_context = ssl._create_unverified_context


   ############################################
   #
   # verify directories and load configurations
   #
   ############################################

   mediatorBinDir = os.path.dirname(os.path.abspath(__file__))
   extr = re.search("(.*)bin", mediatorBinDir)
   if extr:
      mediatorHome = extr.group(1)
      #print "Mediator home is: " + mediatorHome
   else:
      print "FATAL: unable to find mediator home directory. Is it installed properly? bindir = " + mediatorBinDir
      exit()

   if(os.path.isdir(mediatorHome + "log")):
      logHome = extr.group(1)
   else:
      print "FATAL: unable to find log directory at " + mediatorHome + "log"
      exit()

   if(os.path.isfile(mediatorHome + "/config/icdserver.conf")):
      icdServerDict = loadIcdServer(mediatorHome + "/config/icdserver.conf")
   else:
      print "FATAL: unable to find ICD server list file " + mediatorHome + "/config/snowserver.conf"
      exit()


   if(os.path.isfile(mediatorHome + "/config/asmserver.conf")):
      asmServerDict = loadAsmServer(mediatorHome + "/config/asmserver.conf")
   else:
      print "FATAL: unable to find ASM server configuration file " + mediatorHome + "/config/asmserver.conf"
      exit()

   if(os.path.isfile(mediatorHome  + "/config/relationship-mapping.conf")):
      relationshipMappingDict = loadRelationshipMapping(mediatorHome + "/config/relationship-mapping.conf")
   else:
      print "FATAL: no relationship mapping file available at " + mediatorHome + "/config/relationship-mapping.conf"

   if(os.path.isfile(mediatorHome  + "/config/entitytype-mapping.conf")):
      entityTypeMappingDict = loadEntityTypeMapping(mediatorHome + "/config/entitytype-mapping.conf")
   else:
      print "FATAL: no entity type mapping file available at " + mediatorHome + "/config/entitytype-mapping.conf"
      exit()

   if(os.path.isfile(mediatorHome  + "/config/status-filter.conf")):
      ciStatusList = loadStatusFilter(mediatorHome + "/config/status-filter.conf")
      global statusFilter
      statusFilter = ""
      for filter in ciStatusList:
         statusFilter = statusFilter + "=~eq~" + urllib.quote(filter)
         
   else:
      print "FATAL: no status filter file available at " + mediatorHome + "/config/status-filter.conf"
      exit()

   if(os.path.isfile(mediatorHome  + "/config/getICDData.props")):
      configVars = loadProperties(mediatorHome + "/config/getICDData.props")
      print str(configVars)
      if 'saveCisToFile' in configVars.keys():
         global saveCisToFile
         saveCisToFile = configVars['saveCisToFile']
         if(saveCisToFile == "1"):
            print "will save raw json to file"
            if(os.path.exists(mediatorHome + "/log/raw-ci.json")):
               os.remove(mediatorHome + "/log/raw-ci.json")
      if 'readCisFromFile' in configVars.keys():
         global readCisFromFile
         readCisFromFile = configVars['readCisFromFile']
         if(readCisFromFile == "1"):
            print "will read CIs from file if available"
         else:
            print "will read CIs from ServiceNow REST API"
      else:
         print "readCisFromFile property not set, defaulting to 0, read from ServiceNow REST API"
         readCisFromFile = 0
      if 'readRelationshipsFromFile' in configVars.keys():
         global readRelationshipsFromFile
         readRelationshipsFromFile = configVars['readRelationshipsFromFile']
         if(readRelationshipsFromFile == "1"):
            print "will read relationships from file if available"
         else:
            print "will read relationships from ServiceNow REST API"
      else:
         print("readRelationshipsFromFile not in properties file, defaulting to 0, read from ServiceNow REST API")
         readRelationshipsFromFile = 0
      if 'ciFetchPause' in configVars.keys():
         ciFetchPause = int(configVars['ciFetchPause'])
      else:
         ciFetchPause = 0
      if 'ciFetchLimit' in configVars.keys():
         global ciFetchLimit
         ciFetchLimit = int(configVars['ciFetchLimit'])
      if 'sendToRest' in configVars.keys():
         sendToRest = configVars['sendToRest']
         if(sendToRest == "1"):
            if 'restJobId' in configVars.keys():
               print "Will write relationships to ASM through the REST API"
               restJobId = configVars['restJobId']
            else:
               print "Send to REST enabled, but no 'restJobId' specified in the configuration file. Will not send to ASM REST interface"
               sendToRest = 0
      else:
         sendToRest = 0

   else:
      print "FATAL: unable to find the properties file " + mediatorHome + "/config/getICDData.props"

   ########################################
   #
   # Create the REST observer listen job...
   #
   ########################################

   if(sendToRest == "1"):
      result = verifyAsmHealth()
      if(result <> 0):
         if(result == 401):
            print "Unable to access ASM (Error 401: Unauthorized). Verify ASM server credentials in the asmserver.conf file."
         else:
            print "ASM server health check failed. Verify ASM is running and available."
            print "Error code " + str(result)
         exit()
   
      result = checkAsmRestListenJob(restJobId)
      if(result == 200 or result == 0):
         print "REST job already exists, deleting"
         result = deleteAsmRestListenJob(restJobId)
         if(result <> 0):
            print "Error removing existing REST listen job: " + restJobId
            exit()
      elif(result == 401):
         print "Unable to access ASM (Error 401: Unauthorized). Verify ASM server credentials"
         exit()
   
      result = createAsmRestListenJob(restJobId)
      if(result == 0):
         print "Successfully created REST listen job"
      else:
         print "FAIL: unable to create REST listen job"
         if(result == 401):
            print "Unable to access ASM (Error 401: Unauthorized). Verify ASM server credentials"
         else:
            print "Exit code is: " + str(result)
         exit()

   # Begins here

   startTime=datetime.datetime.now().strftime("%m%d%Y-%H%M%S")
   verticesFile = open(mediatorHome + "/file-observer-files/icdTopology-vertices-" + datetime.datetime.now().strftime("%m%d%Y-%H%M%S") + ".txt", "w")
   tempEdgesFile = open(mediatorHome + "/log/tempEdgesFile.json", "w")
   edgesFile = open(mediatorHome + "/file-observer-files/icdTopology-edges-" + datetime.datetime.now().strftime("%m%d%Y-%H%M%S") + ".txt", "w")
   print("Start time: " + startTime)
   getCiData()
   tempEdgesFile.close()
   evaluateRelationships()
   endTime=datetime.datetime.now().strftime("%m%d%Y-%H%M%S")
   print("End time: " + endTime)

   exit()
