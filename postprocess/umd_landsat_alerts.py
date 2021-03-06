import os
import logging
import subprocess
import datetime
from isoweek import Week

from utilities import util
from utilities import update_elastic


def post_process(layerdef):

    # start country page analysis stuff (not map related)
    logging.debug("starting country page analytics")

    cmd = [r'C:\PYTHON27\ArcGISx6410.5\python', 'update_country_stats.py', '-d', 'umd_landsat_alerts']
    cwd = r'D:\scripts\gfw-country-pages-analysis-2'

    cmd += ['-e', layerdef.gfw_env]
    subprocess.check_call(cmd, cwd=cwd)

    # Running this manually for now, as no way to tell when dataset has finished saving in PROD
    # util.hit_vizz_webhook('glad-alerts')

    current_s3_path = update_elastic.get_current_hadoop_output('glad', 's3')
    header_text = 'long,lat,confidence,year,julian_day,country_iso,state_id,dist_id,confidence_text'

    update_elastic.add_headers_to_s3(layerdef, current_s3_path, header_text)

    # region_list = ['se_asia', 'africa', 'south_america']
    country_list = ['PER']

    run_elastic_update(country_list, layerdef.gfw_env)

    # make_climate_maps(region_list)


def run_elastic_update(country_list, api_version):

    logging.debug('starting to update elastic')

    if api_version == 'prod':
        dataset_id = r'e663eb09-04de-4f39-b871-35c6c2ed10b5'
    elif api_version == 'staging':
        dataset_id = r'274b4818-be18-4890-9d10-eae56d2a82e5'
    else:
        raise ValueError('unknown API version supplied: {}'.format(api_version))

    year_list = ['2016', '2017']

    for year in year_list:
        for country in country_list:

            delete_wc = "WHERE year = {0} AND country_iso = '{1}'".format(year, country)
            update_elastic.delete_from_elastic(dataset_id, api_version, delete_wc)

    hadoop_output_url = update_elastic.get_current_hadoop_output('glad')
    update_elastic.append_to_elastic(dataset_id, api_version, hadoop_output_url)


def make_climate_maps(region_list):

    logging.debug('starting make_climate_maps')

    gfw_sync_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    scripts_dir = os.path.dirname(gfw_sync_dir)
    climate_maps_dir = os.path.join(scripts_dir, 'gfw-climate-glad-maps')

    python_exe = r'C:\PYTHON27\ArcGISx6410.5\python'

    current_week = Week.thisweek()

    for i in range(1, 5):
        offset = current_week - i

        year = str(offset.year)
        week = str(offset.week)

        for region in region_list:

            cmd = [python_exe, 'create_map.py', '-y', year, '-w', week, '-r', region]
            logging.debug('calling subprocess:')
            logging.debug(cmd)

            subprocess.check_call(cmd, cwd=climate_maps_dir)





