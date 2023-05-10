import json
import os
import argparse
import sys
import logging
import warnings

import tensorflow as tf

sys.path.append('.')

os.environ["CUDA_VISIBLE_DEVICES"] = "0"
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
if tf.config.list_physical_devices('GPU'):
    tf.config.experimental.set_memory_growth(tf.config.list_physical_devices("GPU")[0], enable=True)

sys.path.insert(0, os.path.abspath('CCDeep'))
sys.path.insert(0, os.path.abspath('.'))

logging.basicConfig(format='%(asctime)s [line:%(lineno)d] %(levelname)s %(message)s', )

parser = argparse.ArgumentParser(description="Welcome to use CCDeep!", add_help=False)
help_content = """
    using this script to auto segment the cell images and identify each cell's  cycle phase.
    usage:
        python main.py -pcna <pcna image filepath>  -bf <bf image filepath> -o [optional] <output result filepath> 
        -t [optional]
"""
parser.add_argument('-ns', '--ns', action='store_true', default=False,
                    help='Optional parameter, segment or not, if call -ns, means do not execute segmentation.')
parser.add_argument('-t', "--track", action='store_true', help='Optional parameter, track or not')
parser.add_argument("-h", "--help", action="help", help=help_content)
parser.add_argument('-p', "--pcna", default=False, help="input image filepath of pcna")
parser.add_argument('-o', "--output", default=False, help='output json file path')
parser.add_argument('-bf', "--bf", default=False, help='input image filepath of bright field')
parser.add_argument('-ot', "--ot", default=False, help='tracking output result saved dir')
parser.add_argument('-js', "--js", default=False, help='annotation json file  path')
parser.add_argument('-r', "--range", default=False,
                    help='tracking frame range, default is None, means tracking whole timelapse')
parser.add_argument('-tp', "--trackpcna", action='store_true', help='Optional parameter, track or not')

args = parser.parse_args()


if len(sys.argv) < 2:
    parser.print_help()
    sys.exit(0)

if args.pcna is False and (not args.ns):
    logging.error("pcna image must be given!")
    sys.exit(-1)
else:
    pcna = args.pcna
if args.bf is False and (not args.ns):
    logging.error("bf image must be given!")
    sys.exit(-1)
else:
    bf = args.bf
if args.output is False:
    output = os.path.join(os.getcwd(), os.path.basename(pcna.replace('.tif', '.json')))
    logging.warning(f"-o  not provided, using the default output file name: {output}")
    logging.info(f"Output segmentation result will saved to {args.output}")
else:
    if not args.output.endswith('.json'):
        if not args.ns:
            logging.error("output filename need <.json> extend name")
            sys.exit(-1)
        else:
            output = os.path.join(os.path.dirname(args.pcna), 'output.json')
    else:
        output = args.output
logging.info(f"Output segmentation result will saved to {output}")

if args.track is True and args.ns is True and args.js is False:
    logging.error("If you just want to do tracking, please give the `-js` parameter")
    sys.exit(-1)
if args.track is True and not args.ns and args.js:
    logging.error("Parameters are ambiguous, please do not give `-js` when you do the segmentation and tracking.")
    sys.exit(-1)

if not args.ns:
    from CCDeep import prediction

    logging.info('start segment ...')
    jsons = prediction.segment(pcna=pcna, bf=bf, output=output, segment_model=None)

elif args.ns and args.js:
    jsons = args.js
else:
    jsons = None


if args.track:
    # from CCDeep import tracking
    from CCDeep.tracking import track

    if args.ot:
        track_output = args.ot
    else:
        if args.range is False:
            xrange = None
        else:
            try:
                xrange = int(args.range)
            except ValueError:
                logging.error(f'param <-r/--range >={args.range}, the value must be int!')
                sys.exit(-1)
        track_output = os.path.dirname(output)
        logging.info(f"Tracking result will saved to {track_output}")
        logging.info('start tracking ...')
        track.start_track(fjson=jsons, fpcna=args.pcna, fbf=None, fout=track_output, track_range=xrange,
                          export_visualization=True, basename=os.path.basename(args.pcna).replace('.tif', ''))


if args.trackpcna:
    from CCDeep.tracking_pcnadeep import track

    if args.ot:
        track_output = args.ot
    else:
        track_output = os.path.dirname(output)
    if args.range is False:
        xrange = None
    else:
        try:
            xrange = int(args.range)
        except ValueError:
            logging.error(f'param <-r/--range >={args.range}, the value must be int!')
            sys.exit(-1)
    if xrange:
        if type(jsons) is dict:
            new_jsons = {key: jsons[key] for key in list(jsons)[:xrange]}
        else:
            with open(jsons) as f:
                js = json.load(f)
                new_jsons = {key: js[key] for key in list(js)[:xrange]}
    else:
        new_jsons = jsons
    logging.info(f"Tracking result will saved to {track_output}")
    logging.info('start tracking ...')
    track.start_track(fjson=new_jsons, fpcna=pcna, fbf=bf, fout=track_output, image_width=1024, image_height=1024)