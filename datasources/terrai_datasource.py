__author__ = 'Charlie.Hofmann'

import arcpy
import datetime
import logging
import sys
import urlparse

from datasource import DataSource
from utilities import aws_s3
from utilities import google_sheet as gs


class TerraiDataSource(DataSource):
    """
    Terrai datasource class. Inherits from DataSource
    Used to download the source file and calculate dates in the VAT
    """
    def __init__(self, layerdef):
        logging.debug('Starting terrai datasource')
        super(TerraiDataSource, self).__init__(layerdef)

        self.layerdef = layerdef

    def get_layer(self):
        """
        Download the terrai datasource, add VAT and calculate dates
        :return: an updated layerdef with the local source for the layer.update() process
        """

        raster_url_list = self.data_source.split(',')
        output_list = []

        for ras in raster_url_list:
            out_file = self.download_file(ras, self.download_workspace)
            output_list.append(out_file)

        self.layerdef['source'] = output_list


        return self.layerdef
