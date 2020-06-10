# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2019 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

from collections import deque
from . import bbox_utils
from typing import Iterable
class ParamsQueue(object):
    """ queue: (limit=1, handle=0), (lim1, handle1), ..
    if response error, retry with smaller limit from h0 to h1
    """
    def __init__(self, params: Iterable, **kw):
        raise NotImplementedError()
    def has_next(self) -> bool:
        raise NotImplementedError()
    def get_params(self):
        raise NotImplementedError()
    def gen_params(self, **kw):
        pass
    def gen_retry_params(self, **params):
        pass
    def has_retry(self) -> bool:
        return False

class SimpleQueue(ParamsQueue):
    def __init__(self, params: list=None, key=None, **kw):
        self._queue = list()
        self.idx = 0
        if params:
            self.set_params(params)
    def has_next(self):
        return self.idx < len(self._queue)
    def get_params(self):
        idx = self.idx
        self.idx += 1 
        return self._queue[idx]
    def set_params(self, lst: list):
        self._queue = list(lst)
        self.idx = 0

        
class CachedQueue(ParamsQueue):
    def __init__(self, key=None, **kw):
        self._key = key
        self._queue = list()
        self._cache = set()
        self.idx = 0
    def set_params(self, lst: list):
        self._cache.update(p[self._key] for p in self._queue[:self.idx] if self._key in p)
        self._queue = [p for p in lst 
            if self._key in p and 
            p[self._key] not in self._cache]
        self.idx = 0
    def has_next(self):
        return self.idx < len(self._queue)
    def get_params(self):
        idx = self.idx
        self.idx += 1 
        return self._queue[idx]

class DequeParamsQueue(ParamsQueue):
    def __init__(self, params: list, **kw):
        self._queue = deque(params)
    def has_next(self) -> bool:
        return len(self._queue) > 0
    def get_params(self):
        params = self._queue.popleft()
        return params

class ParamsQueue_deque_v1(ParamsQueue):
    """ queue: (limit=1, handle=0), (lim1, handle1), ..
    if response error, retry with smaller limit from h0 to h1
    """
    def __init__(self, params, buffer_size=1):
        self._buffer_size = buffer_size
        self.retries = 0
        self.limit = params.get("limit",1)
        self.handle = params.get("handle",0)
        self._queue = deque([dict(limit=self.limit, handle=self.handle)])
        self.handle += self.limit
    def gen_params(self, buffer_size=None):
        if buffer_size is None:
            buffer_size = self._buffer_size
        limit = self.limit
        h0 = self.handle
        h1 = h0 + limit * buffer_size
        self._queue.extend([dict(limit=limit, handle=h) for h in range(h0, h1, limit)])
        self.handle = h1
    def gen_retry_params(self, **params):
        limit = self.limit
        lim = params["limit"]
        handle = params["handle"]
        if lim <= 1:
            # SHOULD RAISE ERROR !!!!
            return
        lim1 = max(1, min(limit, lim//2))
        lim2 = lim % lim1
        h0 = handle
        h1 = h0 + lim
        lst_retry = [dict(limit=lim1, handle=h) for h in range(h0, h1, lim1)] + [dict(limit=lim2, handle=h1-lim2)]
        self._queue.extendleft(reversed(lst_retry))
        self.limit = lim1
        self.retries += len(lst_retry)
    def has_retry(self):
        return self.retries        
    def has_next(self):
        return len(self._queue) > 0
    def get_params(self):
        self.retries = max(0, self.retries-1)
        params = self._queue.popleft()
        return params

class ParamsQueue_deque_v2(ParamsQueue_deque_v1):
    """ queue: (limit=1), (lim1, handle1), ..
    The parameter limit must be between 1 and 100000. (API 21.01.2019)
    if response error, retry with the same request
    """
    def __init__(self, params, buffer_size=1):
        self._buffer_size = buffer_size
        self.retries = 0
        self.limit = params.get("limit",1)
        self.handle = params.get("handle",0)
        self._queue = deque([dict(limit=self.limit)])
        self.handle += self.limit
    def gen_params(self, handle=None):
        limit = self.limit
        if handle is None:
            handle = self.handle
        self._queue.append(dict(limit=limit, handle=handle))
        self.handle = max(self.handle, handle)
    def gen_retry_params(self, **params):
        lst_retry = [params]
        self._queue.extendleft(reversed(lst_retry))
        self.retries += len(lst_retry)

class ParamsQueue_deque_bbox(ParamsQueue_deque_v2):
    def __init__(self, params, buffer_size=1):
        self._buffer_size = buffer_size
        self.retries = 0
        self.limit = params.get("limit",1000)
        self.bbox = params["bbox"]
        self.nx = params.get("nx",6)
        self.ny = params.get("ny",6)

        self._queue = deque([dict(limit=self.limit, bbox=b) 
            for b in bbox_utils.split_bbox(self.bbox,self.nx, self.ny)
        ])
    def gen_params(self, buffer_size=None):
        raise NotImplementedError("queue is generated once")
    def gen_retry_params(self, **params):
        bbox = params["bbox"]
        limit = params["limit"]
        lst_retry =  [dict(limit=self.limit, bbox=b) 
            for b in bbox_utils.split_bbox(bbox,self.nx, self.ny)
        ]
        self._queue.extendleft(reversed(lst_retry))
        self.retries += len(lst_retry)


# above approach of divide and conquer is slow
# because many retry_params that with limit > optimal
# still will be executed
class ParamsQueue_deque_smart(ParamsQueue_deque_v2):
    """ when fetch from retry queue
    if limit < self.limit:
        remove that params,
        generate new retry params with self.limit
    self.limit is current optimal limit
    limit is old generated params
    """
    def get_params(self):
        params = self._queue.popleft()
        while params["limit"] > self.limit:
            self.gen_retry_params(**params)
            params = self._queue.popleft()
        return params

# if API gives estimate byteSize of 1 features
# then params queue can use that for an optimal limit
# gen_retry_params should not change the optimal limit
