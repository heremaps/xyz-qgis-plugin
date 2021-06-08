# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2019 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

import os
import sys

sys.path.insert(0, os.path.abspath("."))
print(sys.path)

from XYZHubConnector.xyz_qgis.layer import parser

from XYZHubConnector.xyz_qgis.network import NetManager
from qgis.PyQt.QtCore import QEventLoop
from XYZHubConnector.xyz_qgis.models.connection import SpaceConnectionInfo
from qgis.testing import start_app

app = start_app()


def make_point_feat(coord):
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": list(coord)}
    }


def get_idx(lon, lat):
    # translate negative lon lat to 1d index
    return (lon + 180) * 181 + lat + 90


def iter_lon_lat(range_lon=(-180, 180), range_lat=(-90, 90), step=1):
    return [(lon, lat)
            for lon in range(range_lon[0], range_lon[1] + 1, step)
            for lat in range(range_lat[0], range_lat[1] + 1, step)]


def step_from_level(level):
    step = 25 - level
    print("level", level, "step", step)
    return step


def precompute_tags():
    tags = [list() for i in iter_lon_lat()]

    for level in range(25):
        step = step_from_level(level)
        for lon, lat in iter_lon_lat(step=step):
            tags[get_idx(lon, lat)].append(level)
    return tags


def format_tags(tags, prefix=None):
    s = ",".join(str(t) for t in tags)
    if prefix:
        s = ",".join([s,
                      prefix,
                      ",".join("%s-%s" % (prefix, t) for t in tags)
                      ])
    return s


def make_point_json(lst_tags):
    obj = {
        "type": "FeatureCollection"
    }
    d = dict()
    lst_coord = list(iter_lon_lat())
    print("len coord/feat", len(lst_coord))
    for tags, feat in zip(lst_tags, map(make_point_feat, lst_coord)):
        d.setdefault(tags, list()).append(feat)

    return dict(
        (tags, parser.make_lst_feature_collection(features))
        for tags, features in d.items())


class Counter():
    cnt = 0


def count_reply(total, callback):
    Counter.cnt = 0

    def fn():
        Counter.cnt += 1
        print("Progress: %s/%s" % (Counter.cnt, total))
        if Counter.cnt == total:
            callback()
            print("Done")

    return fn


def make_point_features():
    # minimize total number of features
    # by generate tags for all levels
    # smallest step for coord currently is 1 (can be smaller)

    lst_tags = [
        format_tags(t, prefix="point")
        for t in precompute_tags()
    ]
    # print(lst_tags)
    print("len tags", len(lst_tags))
    tags_lst_obj = make_point_json(lst_tags)
    print("len set tags", len(set(lst_tags)))
    print("len tags_lst_obj", len(tags_lst_obj))
    total = sum(len(lst) for lst in tags_lst_obj.values())
    print("total obj", total)
    return tags_lst_obj


def upload_features(tags_lst_obj, token, space_id):
    conn_info = SpaceConnectionInfo()
    conn_info.set_(space_id=space_id, token=token)

    loop = QEventLoop()
    network = NetManager(app)
    total = sum(len(lst) for lst in tags_lst_obj.values())
    network.network.finished.connect(count_reply(total, loop.quit))

    for i, (tags, lst_obj) in enumerate(tags_lst_obj.items()):
        # print(len(lst_obj[0]["features"]), tags)
        for obj in lst_obj:
            reply = network.add_features(conn_info, obj, tags=tags)
    loop.exec_()


if __name__ == "__main__":
    tags_lst_obj = make_point_features()
    # print(list(tags_lst_obj.items())[0])

    token, space_id = sys.argv[1:3]
    upload_features(tags_lst_obj, token, space_id)
