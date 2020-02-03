import cv2
import ezdxf
import numpy as np


def draw_hatch(img, entity, color, mask):
    for poly_path in entity.paths.paths:
        # print(poly_path.path_type_flags)
        polygon = np.array([vertex[:-1] for vertex in poly_path.vertices]).astype(int)
        if poly_path.path_type_flags & 1 == 1:
            cv2.fillPoly(img, [polygon], color)
            cv2.fillPoly(mask, [polygon], (255, 255, 255))
        else:
            cv2.fillPoly(img, [polygon], (255, 255, 255))
    return color


def draw_line(img, entity, color, mask):
    p1 = entity.dxf.start[:-1]
    p2 = entity.dxf.end[:-1]
    cv2.line(img, (int(p1[0]), int(p1[1])), (int(p2[0]), int(p2[1])), color, 1)
    cv2.line(mask, (int(p1[0]), int(p1[1])), (int(p2[0]), int(p2[1])), (255, 255, 255), 2)
    return color


def draw_lwpolyline(img, entity, color, mask):
    polyline = []
    a = np.array(entity.lwpoints.values).astype(int)
    while len(a) > 0:
        polyline.append((a[0], a[1]))
        a = a[5:]
    cv2.polylines(img, [np.array(polyline)], entity.closed, color, 1)
    cv2.polylines(mask, [np.array(polyline)], entity.closed, (255, 255, 255), 2)
    return color


def draw_arc(img, entity, color, mask):
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


def draw_circle(img, entity, color, mask):
    r = entity.dxf.radius
    cx, cy = entity.dxf.center.xyz[:-1]
    cv2.circle(img, (int(cx), int(cy)), int(r), color, 1)
    cv2.circle(mask, (int(cx), int(cy)), int(r), (255, 255, 255), -1)
    return color


def draw_ellipse(img, entity, color, mask):
    cx, cy = entity.dxf.center.xyz[:-1]
    ma = entity.dxf.major_axis.magnitude
    angle = entity.dxf.major_axis.angle_deg
    mi = ma * entity.dxf.ratio
    s = entity.dxf.start_param * 180 / np.pi
    e = entity.dxf.end_param * 180 / np.pi
    if entity.dxf.extrusion.z == -1:
        s = 360 - s
        e = 360 - e
    cv2.ellipse(img, (int(cx), int(cy)), (int(ma), int(mi)), angle, s, e, color, 1)
    cv2.ellipse(mask, (int(cx), int(cy)), (int(ma), int(mi)), angle, s, e, (255, 255, 255), 1)
    return color


def draw_point(img, entity, color, mask):
    cx, cy = entity.dxf.location.xyz[:-1]
    cv2.circle(img, (int(cx), int(cy)), 0, color, 1)
    cv2.circle(mask, (int(cx), int(cy)), 0, (255, 255, 255), -1)
    return color


draw_map = {
    'HATCH': draw_hatch,
    'LINE': draw_line,
    'LWPOLYLINE': draw_lwpolyline,
    'ARC': draw_arc,
    'CIRCLE': draw_circle,
    'ELLIPSE': draw_ellipse,
    'POINT': draw_point,
}


def paint(in_path, out_path, config):
    doc = ezdxf.readfile(in_path)
    extmax, extmin = doc.header['$EXTMAX'], doc.header['$EXTMIN']
    xmin, ymin = np.floor(extmin[:-1]).astype(int)
    xmax, ymax = np.ceil(extmax[:-1]).astype(int)
    img = np.ones((ymax + ymin, xmax + xmin, 3), np.uint8) * 255
    mask = np.zeros_like(img)
    msp = doc.modelspace()
    layers = config.get('layers', {})
    colors = config.get('colors', {})
    # print(doc.layers.entries.keys())
    for layer_name, names in layers.items():
        color = tuple(colors.get(layer_name, [0, 0, 0]))
        for name in names:
            if name not in doc.layers:
                continue
            entities = msp.query('*[layer=="%s"]' % name)
            tmp = np.zeros((ymax + ymin, xmax + xmin), np.uint8)
            for entity in entities:
                if entity.DXFTYPE in draw_map:
                    draw_map[entity.DXFTYPE](img, entity, color, tmp)
                else:
                    print("%s: %s" % (name, entity.DXFTYPE))
            contours, hierarchy = cv2.findContours(tmp, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            cv2.drawContours(mask, contours, -1, color, -1)

    res, img_png = cv2.imencode('.png', cv2.flip(img, 0))
    res, mask_png = cv2.imencode('.png', cv2.flip(mask, 0))
    with open(out_path, 'wb') as f:
        f.write(img_png.tobytes())
    with open(out_path[:-4] + "_mask.png", 'wb') as f:
        f.write(mask_png.tobytes())
