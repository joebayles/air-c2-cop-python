# -*- coding: utf-8 -*-

###############################################################################
# Authors: Shaun Nicholson, Esri UK, May 2015
#          Anthony Giles, Helyx SIS, Feb 2016
#
# (C) Copyright ESRI (UK) Limited 2011. All rights reserved
# ESRI (UK) Ltd, Millennium House, 65 Walton Street, Aylesbury, HP21 7QG
# Tel: +44 (0) 1296 745500  Fax: +44 (0) 1296 745544
###############################################################################

import arcpy
from arcpy import env
import sys
import os
import os.path
import inspect
import time
import datetime
import logging
import json

import config
import utils.common

###########################################################################
# Class to write an ACO to a GDB.
# Process the block types:
#
###########################################################################
class ACOWriter:

    _sourceJson = None
    _targetWS   = None

    def __init__(self):
        pass

    def execute(self, sourceJson, targetWS):
        utils.common.OutputMessage(logging.DEBUG, "{0} ACOWriter.execute() - Start".format(time.ctime()))

        utils.common.OutputMessage(logging.DEBUG, "Target Workspace: " + targetWS)
        
        #Check if header has EXER block or OPER block
        if 'EXER' in sourceJson['header']:
            id      = sourceJson['header']['EXER']['id']       
        if 'OPER' in sourceJson['header']:
            id      = sourceJson['header']['OPER']['id']
        
        name    = sourceJson['header']['AMPN']['title']
        file    = sourceJson['metadata']['filename']

        self._insertHeader(targetWS, id, name, file)
        self._insertGeometry(targetWS, id, sourceJson)

        utils.common.OutputMessage(logging.DEBUG, "{0} ACOWriter.execute() - Finish".format(time.ctime()))

        pass

    def _insertHeader(self, targetWS, id, name, filename):
        utils.common.OutputMessage(logging.DEBUG, "{0} ACOWriter._insertHeader() - Start".format(time.ctime()))

        values  = [id, name, filename]

        table   = '%s/AMS_RECORD' % (targetWS)
        fields  = ['AMSID', 'NAME', 'FILENAME']

        cursor  = arcpy.da.InsertCursor(table, fields)
        row     = cursor.insertRow(values)

        del row
        del cursor

        utils.common.OutputMessage(logging.DEBUG, "{0} ACOWriter._insertHeader() - Finish".format(time.ctime()))

    def _insertGeometry(self, targetWS, amsId, sourceJson):
        utils.common.OutputMessage(logging.DEBUG, "{0} ACOWriter._insertGeometry() - Start".format(time.ctime()))

        fields          = ['AMSID', 'ACM', 'NAME', 'USE', 'EFFLEVEL', 'MIN_HEIGHT', 'MAX_HEIGHT', 'MIN_HEIGHT_REF', 'MAX_HEIGHT_REF', 'EXT_HEIGHT', 'SHAPE@JSON', 'Status']
        valuesPolygon   = []
        valuesLine      = []
        valuesPoint     = []

        geometryRecords = sourceJson['geometry']
        for item in geometryRecords:
            record = item['ACMID']
            if ('geometry' in record) == True:
                id      = record['id']
                name    = record['name']
                type    = record['type']
                use     = record['use']
                level   = record['efflevel']['label']
                min     = record['efflevel']['min_height']
                max     = record['efflevel']['max_height']
                min_ref     = record['efflevel']['min_height_ref']
                max_ref     = record['efflevel']['max_height_ref']
                extrude = record['efflevel']['ext_height']
                geom    = json.dumps(record['geometry'])
                                
                if type.upper() == 'GEOLINE':
                    valuesLine.append((amsId, id, name, use, level, min, max, min_ref, max_ref, extrude, geom, 'INACTIVE'))
                elif type.upper() == 'LINE':
                    valuesLine.append((amsId, id, name, use, level, min, max, min_ref, max_ref, extrude, geom, 'INACTIVE'))
                elif type.upper() == 'CORRIDOR':
                    valuesPolygon.append((amsId, id, name, use, level, min, max, min_ref, max_ref, extrude, geom, 'INACTIVE'))
                elif type.upper() == 'CIRCLE':
                    valuesPolygon.append((amsId, id, name, use, level, min, max, min_ref, max_ref, extrude, geom, 'INACTIVE'))
                elif type.upper() == 'POINT':
                    valuesPoint.append((amsId, id, name, use, level, min, max, min_ref, max_ref, extrude, geom, 'INACTIVE'))
                elif type.upper() == 'POLYGON':
                    valuesPolygon.append((amsId, id, name, use, level, min, max, min_ref, max_ref, extrude, geom, 'INACTIVE'))
                else:
                    utils.common.OutputMessage(logging.DEBUG, type.upper() + " is not a valid geometry")
            if ('period' in record) == True:
                self._insertPeriods(targetWS, amsId, id, record['period'], record['name'])

        
        # Insert polygon records        
        table   = '%s/ACO_POLYGON' % (targetWS)
        cursor  = arcpy.da.InsertCursor(table, fields)
        for row in valuesPolygon:
            cursor.insertRow(row)            
        del cursor

        # Insert line records
        table   = '%s/ACO_LINE' % (targetWS)
        cursor  = arcpy.da.InsertCursor(table, fields)
        for row in valuesLine:
            cursor.insertRow(row)
        del cursor
        
        # Insert point records        
        table   = '%s/ACO_POINT' % (targetWS)
        cursor  = arcpy.da.InsertCursor(table, fields)
        for row in valuesPoint:
            cursor.insertRow(row)            
        del cursor
        
        utils.common.OutputMessage(logging.DEBUG, "{0} ACOWriter._insertGeometry() - Finish".format(time.ctime()))

    def _insertPeriods(self, targetWS, parentAMSID, parentId, periodsJson, periodsName):
        utils.common.OutputMessage(logging.DEBUG, "{0} ACOWriter._insertPeriods() - Start".format(time.ctime()))
        utils.common.OutputMessage(logging.DEBUG, periodsName)
        fields = ['AMSID', 'ID', 'TYPE', 'INDEX', 'PERIOD_FROM', 'PERIOD_TO', 'FREQUENCY', 'DURATION', 'Name' ]
        values = []

        for item in periodsJson:
            record = item['APERIOD']
            values.append((parentAMSID, parentId, record['type'], item['SORTORDER'], record['start'], record['stop'], record['frequency'], record['duration'], periodsName))

        table   = '%s/ACO_PERIOD' % (targetWS)
        cursor  = arcpy.da.InsertCursor(table, fields)
        for row in values:
            cursor.insertRow(row)
        del cursor

        utils.common.OutputMessage(logging.DEBUG, "{0} ACOWriter._insertPeriods() - Finish".format(time.ctime()))

###########################################################################
# Class to write an ATO to a GDB.
# Process the block types:
#
###########################################################################
class ATOWriter:

    _sourceJson = None
    _targetWS   = None

    def __init__(self):
        pass

    def execute(self, sourceJson, targetWS):
        utils.common.OutputMessage(logging.DEBUG, "{0} ATOWriter.execute() - Start".format(time.ctime()))
        self._insertGeometry(targetWS, '', sourceJson)

        utils.common.OutputMessage(logging.DEBUG, "{0} ATOWriter.execute() - Finish".format(time.ctime()))

        pass

    def _insertGeometry(self, targetWS, amsId, sourceJson):
        utils.common.OutputMessage(logging.DEBUG, "{0} ATOWriter._insertGeometry() - Start".format(time.ctime()))
        
        fields = []
        fields.append('AMSID')
        fields.append('TASK_COUNTRY')
        fields.append('TASK_UNIT')
        fields.append('TASK_UNIT_LOC')
        fields.append('MSN_NO')
        fields.append('MSN_TYPE')
        fields.append('AC_TYPE')
        fields.append('AC_CALLSIGN')
        fields.append('DEP_LOC')
        fields.append('REC_LOC')
        fields.append('ROUTE')
                
        # GTGTLOC ATTRIBUTES
        fields.append('GTGT_NLT')
        fields.append('GTGT_TOT')
        fields.append('GTGT_NET')
        fields.append('GTGT_DESIG')
        fields.append('GTGT_TYPE')
        fields.append('GTGT_ID')
        fields.append('GTGT_NAME')
        fields.append('GTGT_DESC')
        fields.append('GTGT_PRIORITY')
        fields.append('SHAPE@JSON')
        
        id = sourceJson['header']['EXER']['id']

        valuesPoint = []
        for TaskGroupingCategory in sourceJson['Missions']:
            
            taskUnit = TaskGroupingCategory['taskUnit']
            
            for task in TaskGroupingCategory['taskUnit']['tasks']:
            
                amsndat_ind = task['AMSNDAT']
                
                values = []
                values.append(id)
                values.append(taskUnit['Nationality'])
                values.append(taskUnit['UnitID'])
                values.append(taskUnit['UnitLocation'])
                values.append(amsndat_ind['missionNo'])
                
                values.append(amsndat_ind['primaryMissionType'])
                values.append(amsndat_ind['aircraft']['aircraftCount'] + " x " + amsndat_ind['aircraft']['aircraftType'])
                values.append(amsndat_ind['aircraft']['callsign'])
                values.append(amsndat_ind['departureLocation'])
                values.append(amsndat_ind['recoveryLocation'])
                
                if amsndat_ind['route']:
                    values.append(amsndat_ind['route']['route'])
                else:
                    values.append(None)
                
                
                if amsndat_ind['GTGTLOC']:
                    if amsndat_ind['GTGTLOC']['geometry']:
                        values.append(amsndat_ind['GTGTLOC']['notLaterThan'])
                        values.append(amsndat_ind['GTGTLOC']['timeOnTarget'])
                        values.append(amsndat_ind['GTGTLOC']['notEarlierThan'])
                        values.append(amsndat_ind['GTGTLOC']['designator'])
                        values.append(amsndat_ind['GTGTLOC']['targetType'])
                        values.append(amsndat_ind['GTGTLOC']['dmpiId'])
                        values.append(amsndat_ind['GTGTLOC']['targetName'])
                        values.append(amsndat_ind['GTGTLOC']['dmpiDesc'])
                        values.append(amsndat_ind['GTGTLOC']['priority'])
                        values.append(json.dumps(amsndat_ind['GTGTLOC']['geometry']))
                        valuesPoint.append(values)                                  
        

        # Insert points
        table   = '%s/ATO_MISSION' % (targetWS)
        cursor  = arcpy.da.InsertCursor(table, fields)
        for row in valuesPoint:
            cursor.insertRow(row)
        del cursor

        utils.common.OutputMessage(logging.DEBUG, "{0} ATOWriter._insertGeometry() - Finish".format(time.ctime()))

###########################################################################
# Write JSON file to target location.
#
###########################################################################
def writeJSON(jsonData, paths):
    utils.common.OutputMessage(logging.DEBUG, "{0} writeJSON() - Start".format(time.ctime()))

    currentPath     = os.path.dirname(os.path.realpath(__file__))
    utils.common.OutputMessage(logging.DEBUG, "{0} writeJSON() - {1}".format(time.ctime(), currentPath))

    targetPath      = [currentPath, '..', '..', '..']
    targetPath      = targetPath + paths
    utils.common.OutputMessage(logging.DEBUG, "{0} writeJSON() - {1}".format(time.ctime(), targetPath))

    currentFile     = os.path.join(*targetPath)

    utils.common.OutputMessage(logging.DEBUG, "{0} writeJSON() - {1}".format(time.ctime(), currentFile))

    with open(currentFile, 'w') as outfile:
        json.dump(jsonData, outfile, indent = 4, ensure_ascii=False)
