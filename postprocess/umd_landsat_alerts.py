import arcpy
import numpy
from arcpy import env
from arcpy.sa import *
import urllib
import os
import time
import datetime
from os import walk
import sys
import logging
import subprocess
import requests

from utilities import util

#Check out ArcGIS Extensions
arcpy.CheckOutExtension("Spatial")
arcpy.env.overwriteOutput = True

borneo_mxd = arcpy.mapping.MapDocument(r"D:\GIS Data\GFW\glad\maps\mxds\borneo.mxd")
peru_mxd = arcpy.mapping.MapDocument(r"D:\GIS Data\GFW\glad\maps\mxds\peru.mxd")
roc_mxd = arcpy.mapping.MapDocument(r"D:\GIS Data\GFW\glad\maps\mxds\roc.mxd")
brazil_mxd = arcpy.mapping.MapDocument(r"D:\GIS Data\GFW\glad\maps\mxds\brazil.mxd")


def post_process(layerdef):
    """
    Create density maps for GFW Climate Visualization
    :param layerdef: the layerdef
    """
    logging.debug('starting postprocess glad maps')
    logging.debug(layerdef.source)

    # start country page analysis stuff (not map related)
    logging.debug("starting country page analytics")
    cmd = ['python', 'update_country_stats.py', '-d', 'umd_landsat_alerts', '-a', 'gadm2_boundary']
    cwd = r'D:\scripts\gfw-country-pages-analysis-2'

    if layerdef.gfw_env == 'PROD':
        cmd += ['-e', 'prod']

    else:
        cmd += ['-e', 'staging']

    subprocess.check_call(cmd, cwd=cwd)

    # POST to kick off GLAD Alerts subscriptions now that we've updated the country-pages data
    api_token = util.get_token('gfw-rw-api-prod')

    headers = {'Content-Type': 'application/json', 'Authorization': 'Bearer {0}'.format(api_token)}
    url = r'https://production-api.globalforestwatch.org/subscriptions/notify-updates/glad-alerts'

    r = requests.post(url, headers=headers)
    logging.debug(r.text)

    update_elastic()


    olddata_hash = {}
    past_points = [
    r"D:\GIS Data\GFW\glad\past_points\borneo_day2016.shp",
    r"D:\GIS Data\GFW\glad\past_points\peru_day2016.shp",
    r"D:\GIS Data\GFW\glad\past_points\roc_day2016.shp",
    r"D:\GIS Data\GFW\glad\past_points\brazil_day2016.shp"
    ]

    latest_rasters = []
    new_points = []

    for point in past_points:
        point_name = os.path.basename(point)
        olddata_hash[point_name] = arcpy.SearchCursor(point, "", "", "","GRID_CODE D").next().getValue("GRID_CODE")

    for ras in layerdef.source:
        if "FE" in ras:
            pass
        elif "day" in ras:
            ras_name = os.path.basename(ras)
            shp_name = ras_name.replace(".tif", ".shp")
            where_clause = "Value > " + str(olddata_hash[shp_name])
            raster_extract = ExtractByAttributes(ras, where_clause)
            output = os.path.join (r"D:\GIS Data\GFW\glad\latest_points", ras_name)
            latest_raster = raster_extract.save(output)
            latest_rasters.append(output)
            logging.debug("here's the latest_rasters list %s" %(latest_rasters))
            logging.debug("new values for %s extracted" %(ras_name))
        else:
            pass

    if not latest_rasters:
        pass
    else:
        for ras in latest_rasters:
            ras_name = os.path.basename(ras).replace(".tif", ".shp")
            output = os.path.join(os.path.dirname(ras), ras_name)
            new_point = arcpy.RasterToPoint_conversion(ras, output, "Value")
            new_points.append(output)
            logging.debug("converted %s to points" %(ras))

    if not new_points:
        pass
    else:
        for newp in new_points:
            for pastp in past_points:
                if os.path.basename(newp) == os.path.basename(pastp):
                    arcpy.Copy_management(newp, pastp)
                    logging.debug("copied %s to %s" %(newp, pastp))

    if not new_points:
        pass
    else:
        for idnp in new_points:
            if "borneo" in idnp:
                logging.debug('clipping indonesia data')
                clip = r"D:\GIS Data\GFW\glad\maps\clip\idn_clip.shp"
                name = "borneo_clip.shp"
                output = os.path.join(os.path.dirname(idnp), name)
                idnp_clipped = arcpy.Clip_analysis(idnp, clip, output)
                new_points.remove(idnp)
                new_points.insert(0, output)
                logging.debug(new_points)
            else:
                pass

    if not new_points:
        pass
    else:
        for newp in new_points:
            outKDens = KernelDensity(newp, "NONE", "", "", "HECTARES")
            path = r"D:\GIS Data\GFW\glad\maps\density_rasters"
            name = os.path.basename(newp).replace(".shp", "")
            output = os.path.join(path, name + "_density.tif")
            outKDens.save(output)
            logging.debug("density layer created")

    if not new_points:
        pass
    else:
        for layer in new_points:
            if "peru" in layer:
                logging.debug("creating map for peru")
                make_maps(peru_mxd)
            if "roc" in layer:
                logging.debug("creating map for roc")
                make_maps(roc_mxd)
            if "brazil" in layer:
                logging.debug("creating map for brazil")
                make_maps(brazil_mxd)
            if "borneo" in layer:
                logging.debug("creating map for borneo")
                make_maps(borneo_mxd)
            else:
                pass

def make_maps(mxd):

    logging.debug('starting postprocess make maps')

    gadm = r"D:\GIS Data\Country Boundaries\country boundaries.gdb\countries"
    global ISO
    global name
    global density

    if mxd == borneo_mxd:
        ISO = "'BRN'"
        name = "IDN13"
        density = r"D:\GIS Data\GFW\glad\maps\density_rasters\borneo_clip_density.tif"
    if mxd == peru_mxd:
        ISO = "'PER'"
        name = "PER"
        density = r"D:\GIS Data\GFW\glad\maps\density_rasters\peru_day2016_density.tif"
    if mxd == brazil_mxd:
        ISO = "'BRA'"
        name = "BRA"
        density = r"D:\GIS Data\GFW\glad\maps\density_rasters\brazil_day2016_density.tif"
    if mxd == roc_mxd:
        ISO = "'COG'"
        name = "COG"
        density = r"D:\GIS Data\GFW\glad\maps\density_rasters\roc_day2016_density.tif"

    arcpy.MakeFeatureLayer_management(gadm,"lyr")
    SQL_query = " code_iso3 = "+ISO
    gadm_path = r"D:\GIS Data\GFW\glad\maps\mxds"
    gadm_output = os.path.join(gadm_path, name + "_clip.shp")
    selection = arcpy.Select_analysis("lyr",gadm_output, SQL_query)
    rows = arcpy.SearchCursor(selection)
    extent = 0
    shapeName = arcpy.Describe(gadm).shapeFieldName
    for row in rows:
        feat = row.getValue(shapeName)
        extent = feat.extent
    Xmin= str(extent.XMin)
    Ymin= str(extent.YMin)
    Xmax= str(extent.XMax)
    Ymax= str(extent.YMax)
    rectangle = Xmin + " " + Ymin + " " + Xmax + " " + Ymax
    print "clipping density layer to GADM boundary"
    clip_path = r"D:\GIS Data\GFW\glad\maps\mxds"
    clip_output = os.path.join(clip_path, name + "_clip.tif")
    density_clip = arcpy.Clip_management(density, rectangle, clip_output, selection, "#", "ClippingGeometry")
    # clip_result = density_clip.getOutput(0)
    logging.debug("adding data to mxd file and setting extent")
    df = arcpy.mapping.ListDataFrames(mxd, "Layers")[0]
    add_results = arcpy.mapping.Layer(clip_output)
    add_gadm = arcpy.mapping.Layer("lyr")
    arcpy.mapping.AddLayer(df, add_gadm, "TOP")
    arcpy.mapping.AddLayer(df, add_results, "TOP")
    gadm_lyr = arcpy.mapping.ListLayers(mxd, "lyr", df)[0]
    arcpy.SelectLayerByAttribute_management(gadm_lyr,"NEW_SELECTION", SQL_query)
    df.zoomToSelectedFeatures()
    arcpy.RefreshActiveView()
    arcpy.mapping.RemoveLayer(df,gadm_lyr)

    #export
    logging.debug("adding symbology and exporting")
    ts = time.time()
    time_year = datetime.datetime.fromtimestamp(ts).strftime("%Y")
    time_week = datetime.datetime.fromtimestamp(ts).strftime("%W")
    density_lyr = arcpy.mapping.ListLayers(mxd)[0]
    Symbology = r"D:\GIS Data\GFW\glad\maps\mxds\color.lyr"
    arcpy.ApplySymbologyFromLayer_management(density_lyr, Symbology)
    arcpy.RefreshActiveView()
    output = os.path.join(r"F:\climate\glad_maps", name + "_" + time_year + "_" + time_week + ".png")
    arcpy.mapping.ExportToPNG(mxd, output)
    logging.debug("map created")


def update_elastic():

    dataset_id = r'ae1fc1d2-2b96-4ce5-8418-b9159e157680'

    staging_token = util.get_token('gfw-rw-api-staging')

    region_list = ['se_asia', 'africa', 'south_america']
    year_list = ['2016', '2017']

    headers = {'Content-Type': 'application/json', 'Authorization': 'Bearer {0}'.format(staging_token)}

    for year in year_list:
        for region in region_list:
            delete_and_append(dataset_id, headers, year, region)


def delete_and_append(dataset_id, headers, year, region):
    delete_url = r'http://staging-api.globalforestwatch.org/query/{0}'.format(dataset_id)

    qry_parms = {"sql": "DELETE FROM index_{0} "
                        "WHERE year = {1} AND region = '{2}'".format(dataset_id.replace('-', ''), year, region)}

    logging.debug('starting delete request')
    logging.debug(qry_parms)

    r = requests.get(delete_url, headers=headers, params=qry_parms)

    logging.debug(r.status_code)
    logging.debug(r.json())

    src_url = r'http://gfw2-data.s3.amazonaws.com/alerts-tsv/glad/{0}_{1}.csv'.format(region, year)
    dataset_url = r'http://staging-api.globalforestwatch.org/dataset/{0}/concat'.format(dataset_id)

    payload = {'url': src_url}

    logging.debug('starting concat')
    logging.debug(payload)

    r = requests.post(dataset_url, headers=headers, json=payload)
    status = r.status_code

    if status == 204:
        logging.debug('Request succeeded!')
    else:
        logging.debug(r.text)
        raise ValueError('Request failed with code: {}'.format(status))
