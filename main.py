import argparse
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
    return os.path.join(output, "%s.png" % os.path.basename(path_to_dxf)[:-len("dxf")])


def wrapper_painting(input, output):
    try:
        paint(input, output)
        print("Filename `%s`: OK" % input)
    except:
        print("Filename `%s`: FAILURE" % input)
        traceback.print_exc()
        return 1
    return 0


if __name__ == '__main__':
    args = register_launch_arguments()

    input_path = args.input
    output_path = args.output

    if not os.path.exists(input_path):
        print("Input path `%s` doesn't exist" % input_path)

    if not os.path.exists(output_path):
        os.makedirs(output_path)

    cnt_fail = 0

    if os.path.isfile(input_path) and input_path[-len("dxf"):].lower() == "dxf":
        cnt_fail += wrapper_painting(input_path, create_png_path(input_path, output_path))
    elif not args.tree:
        files = os.listdir(input_path)
        for _ in filter(lambda x: x[-len("dxf"):].lower() == "dxf", files):
            cnt_fail += wrapper_painting(os.path.join(input_path, _), create_png_path(_, output_path))
    else:
        tree = os.walk(input_path)
        for _ in tree:
            if len(_[1]) > 0:
                continue
            for file in filter(lambda x: x[-len("dxf"):].lower() == "dxf", _[2]):
                cnt_fail += wrapper_painting(os.path.join(_[0], file), create_png_path(file, output_path))

    print("Fail converting: %d" % cnt_fail)
