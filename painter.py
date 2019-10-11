import cv2
import ezdxf
import numpy as np


def get_color(entity, layer):
    code = entity.dxf.color
    if code == 256:
        return ezdxf.tools.aci2rgb(layer.dxf.color)
    return ezdxf.tools.aci2rgb(code)


def draw_hatch(img, entity, layer):
    color = get_color(entity, layer)
    for poly_path in entity.paths.paths:
        print(poly_path.path_type_flags)
        polygon = np.array([vertex[:-1] for vertex in poly_path.vertices]).astype(int)
        if poly_path.path_type_flags & 1 == 1:
            cv2.fillPoly(img, [polygon], color)
        else:
            cv2.fillPoly(img, [polygon], (255, 255, 255))


def draw_line(img, entity, layer):
    color = get_color(entity, layer)
    p1 = entity.dxf.start[:-1]
    p2 = entity.dxf.end[:-1]
    cv2.line(img, (int(p1[0]), int(p1[1])), (int(p2[0]), int(p2[1])), color, 1)


def draw_lwpolyline(img, entity, layer):
    color = get_color(entity, layer)
    polyline = []
    a = np.array(entity.lwpoints.values).astype(int)
    while len(a) > 0:
        polyline.append((a[0], a[1]))
        a = a[5:]
    cv2.polylines(img, [np.array(polyline)], entity.closed, color, 1)


def draw_arc(img, entity, layer):
    color = get_color(entity, layer)
    s = entity.dxf.start_angle * np.pi / 180
    e = entity.dxf.end_angle * np.pi / 180
    if s > e:
        s -= 2 * np.pi
    d = (e - s) / (int((e - s) * 180 / np.pi) + 1)
    r = entity.dxf.radius
    cx, cy = entity.dxf.center.xyz[:-1]
    angles = np.arange(s, e + d / 2, d)
    x = cx + r * np.cos(angles)
    y = cy + r * np.sin(angles)
    points = np.column_stack((x, y)).astype(int)
    cv2.polylines(img, [points], abs(s - e) < 1e-9, color, 1)


draw_map = {
    'HATCH': draw_hatch,
    'LINE': draw_line,
    'LWPOLYLINE': draw_lwpolyline,
    'ARC': draw_arc,
}


def paint(in_path, out_path, config):
    doc = ezdxf.readfile(in_path)
    extmax, extmin = doc.header['$EXTMAX'], doc.header['$EXTMIN']
    xmin, ymin = np.floor(extmin[:-1]).astype(int)
    xmax, ymax = np.ceil(extmax[:-1]).astype(int)
    img = np.ones((ymax + ymin, xmax + xmin, 3)) * 255
    msp = doc.modelspace()
    layers = config.get('layers', [])
    print(doc.layers.entries.keys())
    for layer_name in layers:
        if layer_name not in doc.layers:
            continue
        print(layer_name)
        entities = msp.query('*[layer=="%s"]' % layer_name)
        layer = doc.layers.get(layer_name)
        for entity in entities:
            print(entity.DXFTYPE)
            if entity.DXFTYPE in draw_map:
                draw_map[entity.DXFTYPE](img, entity, layer)

    res, im_png = cv2.imencode('.png', cv2.flip(img, 0))
    with open(out_path, 'wb') as f:
        f.write(im_png.tobytes())
