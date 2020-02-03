import argparse
import json
import os
import traceback

from painter import paint


def register_launch_arguments():
    parser = argparse.ArgumentParser(description='Serve the application')
    parser.add_argument('-c', '--cfgpath', help='overrides the default path to config.json', default='./config.json')
    parser.add_argument('-i', '--input', help='input path - folder with dxf files or file', required=True)
    parser.add_argument('-o', '--output', help='output path - folder for png files', required=True)
    parser.add_argument('-t', '--tree', help='iterate in tree of folders', action="store_true")

    return parser.parse_args()


def create_png_path(path_to_dxf, output):
    return os.path.join(output, "%s.png" % os.path.basename(path_to_dxf)[:-len(".dxf")])


def wrapper_painting(in_path, out_path, config):
    try:
        paint(in_path, out_path, config)
        print("Filename `%s`: OK" % in_path)
    except:
        print("Filename `%s`: FAILURE" % in_path)
        traceback.print_exc()
        return 1
    return 0


def is_dxf(path):
    return path[-len("dxf"):].lower() == "dxf"


if __name__ == '__main__':
    args = register_launch_arguments()

    input_path = args.input
    output_path = args.output
    with open(args.cfgpath, 'r', encoding='utf-8') as cfg:
        config = json.load(cfg)

    if not os.path.exists(input_path):
        print("Input path `%s` doesn't exist" % input_path)

    if not os.path.exists(output_path):
        os.makedirs(output_path)

    cnt_fail = 0

    if os.path.isfile(input_path) and is_dxf(input_path):
        cnt_fail += wrapper_painting(input_path, create_png_path(input_path, output_path), config)
    elif not args.tree:
        files = os.listdir(input_path)
        for _ in filter(is_dxf, files):
            cnt_fail += wrapper_painting(os.path.join(input_path, _), create_png_path(_, output_path), config)
    else:
        tree = os.walk(input_path)
        for _ in tree:
            if len(_[1]) > 0:
                continue
            for file in filter(is_dxf, _[2]):
                cnt_fail += wrapper_painting(os.path.join(_[0], file), create_png_path(file, output_path), config)

    print("Fail converting: %d" % cnt_fail)
