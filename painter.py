import cv2
import ezdxf
import numpy as np


def get_color(entity, layer):
    code = entity.dxf.color
    if code == 256:
        color = list(ezdxf.tools.aci2rgb(layer.dxf.color))
    else:
        color = list(ezdxf.tools.aci2rgb(code))
    tmp = color[0]
    color[0] = color[2]
    color[2] = tmp
    return tuple(color)


def draw_hatch(img, entity, layer, mask):
    color = get_color(entity, layer)
    for poly_path in entity.paths.paths:
        # print(poly_path.path_type_flags)
        polygon = np.array([vertex[:-1] for vertex in poly_path.vertices]).astype(int)
        if poly_path.path_type_flags & 1 == 1:
            cv2.fillPoly(img, [polygon], color)
            cv2.fillPoly(mask, [polygon], (255, 255, 255))
        else:
            cv2.fillPoly(img, [polygon], (255, 255, 255))
    return color


def draw_line(img, entity, layer, mask):
    color = get_color(entity, layer)
    p1 = entity.dxf.start[:-1]
    p2 = entity.dxf.end[:-1]
    cv2.line(img, (int(p1[0]), int(p1[1])), (int(p2[0]), int(p2[1])), color, 1)
    cv2.line(mask, (int(p1[0]), int(p1[1])), (int(p2[0]), int(p2[1])), (255, 255, 255), 2)
    return color


def draw_lwpolyline(img, entity, layer, mask):
    color = get_color(entity, layer)
    polyline = []
    a = np.array(entity.lwpoints.values).astype(int)
    while len(a) > 0:
        polyline.append((a[0], a[1]))
        a = a[5:]
    cv2.polylines(img, [np.array(polyline)], entity.closed, color, 1)
    cv2.polylines(mask, [np.array(polyline)], entity.closed, (255, 255, 255), 2)
    return color


def draw_arc(img, entity, layer, mask):
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
    cv2.polylines(mask, [points], abs(s - e) < 1e-9, (255, 255, 255), 2)
    return color


def draw_circle(img, entity, layer, mask):
    color = get_color(entity, layer)
    r = entity.dxf.radius
    cx, cy = entity.dxf.center.xyz[:-1]
    cv2.circle(img, (int(cx), int(cy)), int(r), color, 1)
    cv2.circle(mask, (int(cx), int(cy)), int(r), (255, 255, 255), -1)
    return color


def draw_ellipse(img, entity, layer, mask):
    color = get_color(entity, layer)
    cx, cy = entity.dxf.center.xyz[:-1]
    ma = entity.dxf.major_axis.magnitude
    angle = entity.dxf.major_axis.angle_deg
    mi = ma * entity.dxf.ratio
    s = entity.dxf.start_param * 180 / np.pi
    e = entity.dxf.end_param * 180 / np.pi
    cv2.ellipse(img, (int(cx), int(cy)), (int(ma), int(mi)), angle, s, e, color, 1)
    cv2.ellipse(mask, (int(cx), int(cy)), (int(ma), int(mi)), angle, s, e, (255, 255, 255), -1)
    return color


draw_map = {
    'HATCH': draw_hatch,
    'LINE': draw_line,
    'LWPOLYLINE': draw_lwpolyline,
    'ARC': draw_arc,
    'CIRCLE': draw_circle,
    'ELLIPSE': draw_ellipse,
}


def paint(in_path, out_path, config):
    doc = ezdxf.readfile(in_path)
    extmax, extmin = doc.header['$EXTMAX'], doc.header['$EXTMIN']
    xmin, ymin = np.floor(extmin[:-1]).astype(int)
    xmax, ymax = np.ceil(extmax[:-1]).astype(int)
    img = np.ones((ymax + ymin, xmax + xmin, 3), np.uint8) * 255
    mask = np.zeros_like(img)
    msp = doc.modelspace()
    layers = config.get('layers', [])
    # print(doc.layers.entries.keys())
    for layer_name in layers:
        if layer_name not in doc.layers:
            continue
        # print(layer_name)
        entities = msp.query('*[layer=="%s"]' % layer_name)
        layer = doc.layers.get(layer_name)
        tmp = np.zeros((ymax + ymin, xmax + xmin), np.uint8)
        color = (0, 0, 0)
        for entity in entities:
            # print(entity.DXFTYPE)
            if entity.DXFTYPE in draw_map:
                color = draw_map[entity.DXFTYPE](img, entity, layer, tmp)
        contours, hierarchy = cv2.findContours(tmp, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(mask, contours, -1, color, -1)

    res, img_png = cv2.imencode('.png', cv2.flip(img, 0))
    res, mask_png = cv2.imencode('.png', cv2.flip(mask, 0))
    with open(out_path, 'wb') as f:
        f.write(img_png.tobytes())
    with open(out_path[:-4] + "_mask.png", 'wb') as f:
        f.write(mask_png.tobytes())
