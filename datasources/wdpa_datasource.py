import os
import sys
import logging
import arcpy

from datasource import DataSource


class WDPADatasource(DataSource):
    """
    WDPA datasource class. Inherits from DataSource
    Used to download the source GDB, find the polygon FC, repair and simplify geometry
    """
    def __init__(self, layerdef):
        logging.debug('Starting simple_datasource')
        super(WDPADatasource, self).__init__(layerdef)

        self.layerdef = layerdef

    def download_wpda_to_gdb(self):
        local_file = self.download_file(self.data_source, self.download_workspace)

        self.unzip(local_file, self.download_workspace)

        unzipped_gdb = None

        for item in os.walk(self.download_workspace):
            dirname = item[0]

            if os.path.splitext(dirname)[1] == '.gdb':
                unzipped_gdb = dirname
                break

        if unzipped_gdb:
            arcpy.env.workspace = unzipped_gdb
        else:
            logging.error("Expected to find GDB somewhere in the unzipped dirs, but didn't. Exiting")
            sys.exit(1)

        poly_list = [x for x in arcpy.ListFeatureClasses() if arcpy.Describe(x).shapeType == 'Polygon']

        if len(poly_list) != 1:
            logging.error("Expected one polygon FC in the wdpa gdb. Found {0}. Exiting now.".format(len(poly_list)))
            sys.exit(1)
        else:
            self.data_source = os.path.join(unzipped_gdb, poly_list[0])

    def prep_source_fc(self):
        logging.debug("Starting repair_geometry")
        arcpy.RepairGeometry_management(self.data_source, "DELETE_NULL")

        simplified_fc = self.data_source + '_simplified'

        logging.debug("Starting simplify_polygon")
        arcpy.SimplifyPolygon_cartography(self.data_source, simplified_fc, algorithm="POINT_REMOVE",
                                          tolerance="10 Meters", minimum_area="0 Unknown", error_option="NO_CHECK",
                                          collapsed_point_option="NO_KEEP")

        self.data_source = simplified_fc

    def get_layer(self):
        """
        Full process, called in layer_decision_tree.py. Downloads and preps the data
        :return: Returns and updated layerdef, used in the layer.update() process in layer_decision_tree.py
        """

        self.download_wpda_to_gdb()

        self.prep_source_fc()

        self.layerdef['source'] = self.data_source

        return self.layerdef
