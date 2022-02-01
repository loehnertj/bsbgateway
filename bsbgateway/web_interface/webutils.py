# coding: utf8

##############################################################################
#
#    Copyright (C) Johannes Loehnert, 2013-2015
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

'''Various useful functions for global use in a web.py app.
'''

# Imports that are only needed for one function are within the def.

import sys
import os
import logging

import web

if sys.version_info[0] == 2:
    range = xrange
else:
    basestring = str

__all__ = [
    'bridge_call',
    'autojson',
    'filter_kwargs', 
    'cast_if_there',
    'intlist',
    'find_classes_with_url',
    'serve_file',
    'UrlDir',
    'profile',
]

PROFILE_SETTINGS = dict(
    n_lines=50,
    filter_path='FIXME',
    dump_file='',
    print_file='~/webpytools-profile.txt',
)

def warning(*args, **kwargs):
    logging.getLogger(__name__).warning(*args, **kwargs)

def bridge_call(obj, methodname, inputs, conversions=None, json=True):
    '''does the plumbing to translate a request into a function call and back.

    obj : object reference
    methodname : the function to be invoked --> ultimately obj.<methodname> will be called.
    inputs: dict with input string values. There are some special keys, see below.
    conversions: dict defining input conversions:
        'name': func --> inputs['name'] is replaced by func(inputs['name'])
        'name->newname': func --> if inputs['name'] is there, inputs['newname'] is set to func result
    converted inputs are passed to the method as kwargs. Unsupported kwargs are silently discarded.
    json: if True (default), the method result is converted to json if not string or template output.
        If False, the result is returned as-is.

    Along the way, exceptions and result headers are raised/set as appropriate.

    Special input keys (that are not passed to the method):
        * _profile: if present, the method call is profiled. The profile is
            printed to stdout and profile.txt.
            (uses PROFILE_SETTINGS)
    '''
    prof_nruns = inputs.get('_profile', '0')
    prof_nruns = int(prof_nruns or '1')
    if prof_nruns:
        del inputs['_profile']

    if conversions:
        convs = [key.split('->')[0] for key in conversions.keys()]
        for key in inputs:
            if key not in convs:
                warning('bridge_call: Input key "%s" is not defined in conversions. '
                    'If it is a legal parameter, you should list it. '
                    '(from: %r; method: "%s")'%(key, obj, methodname))

        # might raise 400 Bad Request
        cast_if_there(inputs, conversions)

    method = filter_kwargs(getattr(obj, methodname))
    if prof_nruns:
        with profile(**PROFILE_SETTINGS):
            for n in range(prof_nruns):
                result = method(**inputs)
        raise web.seeother('_profile_results')
    else:
        result = method(**inputs)
    
    if json:
        # might set Content-Type
        result = autojson(result)
    return result


from contextlib import contextmanager
@contextmanager
def profile(n_lines=50, filter_path='', print_file='', dump_file=''):
    '''profile the with..: body and print results.

    The first 50 lines are printed, sorted by cumulative time.
    Only calls in modules within filter_path are shown
    (see python docs for profile(), namely print_stats()).
    if print_file is given, the unfiltered human-readable profile 
    is saved to the file.
    if dump_file is given, the binary profile info is saved to this file.

    WARNING: print_file + dump_file are overwritten without warning.
    '''
    import cProfile, pstats
    p = cProfile.Profile()
    p.enable()

    yield

    p.disable()
    p.create_stats()
    stats = pstats.Stats(p)
    stats.sort_stats('cumulative')
    stats.print_stats(filter_path, n_lines)
    if dump_file:
        stats.dump_stats(dump_file)

    if print_file:
        with open(print_file, 'w') as fh:
            stats = pstats.Stats(p, stream=fh)
            stats.sort_stats('cumulative')
            stats.print_stats()



def autojson(obj):
    '''checks result of a handler before shipping.
    * if string, pass through
    * if obj has to_json method, return obj.to_json() and set Content-Type.
    * else, try to return json.dumps(obj) and set Content-Type.
    '''
    import json
    from web.template import TemplateResult
    if isinstance(obj, basestring):
        return obj

    if isinstance(obj, TemplateResult):
        return obj

    if hasattr(obj, 'to_json'):
        result = obj.to_json()
    else:
        result = json.dumps(obj)
    web.header('Content-Type', 'application/json; charset=utf-8')
    return result


def filter_kwargs(fn):
    '''decorator which swallows all kwargs not supported by the wrapped fn.'''
    from inspect import getargspec
    allowed, dummy1, dummy2, dummy3 = getargspec(fn)
    # *args must be included or it won't work with methods (self is automatically
    # passed as anonymous first arg).
    def wrapped(*args, **kwargs):
        kwargs = {key:value for key, value in kwargs.items() if key in allowed}
        return fn(*args, **kwargs)
    return wrapped


def cast_if_there(dict, mappings):
    '''mappings: dict {key: conversion func}
    key is a string, either key of dict or 'expectedkey->newkey'.
    in the latter case, the old entry is preserved.
    conversion func: fn(string) -> something e.g. int
    '''
    for key, castfn in mappings.items():
        names = key.split('->')
        expectedkey = names[0]
        newkey = names[-1]
        if expectedkey in dict:
            try:
                dict[newkey] = castfn(dict[expectedkey])
            except:
                raise web.HTTPError(
                    status="400 Bad Request", 
                    data=u"Ungueltiges Argument fuer Parameter '%s': %s"%(expectedkey, dict[expectedkey])
                )


def intlist(s):
    '''parse CSV into list of ints, skipping empty values. s may be str or unicode.
    
    Also treats list of strings and list of ints as one would expect.'''
    if isinstance(s, basestring):
        s = s.split(',')
    if s and isinstance(s[0], basestring):
        s = [int(x.strip()) for x in s if x.strip()!='']
    return s


def as_is(s):
    '''returns input unchanged - for use in conversions'''
    return s

def find_classes_with_url(module):
    '''recursively finds all classes which have an "url" property, but only in
    modules in the root module's directory tree.

    returns list of classes.
    '''
    import types
    modcontent = [getattr(module, name) for name in dir(module)]
    urlclasses = set([cls for cls in modcontent if isinstance(cls, (types.TypeType, types.ClassType)) and hasattr(cls, "url")])
    submods = [mod for mod in modcontent if isinstance(mod, types.ModuleType)]
    modpath = os.path.split(module.__file__)[0]
    for submod in submods:
        if not hasattr(submod, "__file__"): continue
        # do not leave subdirectory!
        if not os.path.split(submod.__file__)[0].startswith(modpath): continue
        urlclasses.update(find_classes_with_url(submod))
    return urlclasses


def serve_file(path):
    '''Serve static file from the given path. Sets headers: Modified, Content-Type, Encoding'''
    import mimetypes
    from datetime import datetime
    if not os.path.exists(path):
        raise web.notfound()
    mdate = datetime.fromtimestamp(os.stat(path).st_mtime)
    web.modified(date=mdate, etag='')
    fh = open(path, 'rb')
    s = fh.read()
    fh.close()
    mime, enc = mimetypes.guess_type(path, strict=False)
    if mime:
        web.header('Content-Type', mime)
    if enc:
        web.header('Content-Encoding', enc)
    return s



import re

class UrlDirError(Exception): pass

class CachedTemplate(object):
    template = None
    timestamp = 0
    path = ''
    def __init__(o, template, timestamp, path):
        o.template = template
        o.timestamp = timestamp
        o.path = path

class UrlDir(object):
    def __init__(o, modulepath, base_path=''):
        o._path = os.path.split(modulepath)[0]
        o.base_path = base_path
        o._cache = {}

    def staticfile(o, filename):
        '''serves the static file given by filename (in module dir)'''
        if not re.match('^[a-zA-Z0-9_.]*$', filename):
            warning( 'UrlDir.staticfile got suspicious filename: %s'%filename)
            web.badrequest()
        return serve_file(os.path.join(o._path, filename))

    def template(o, filename, append_html=True):
        '''returns webpy template given by filename. 
        if append_html=True, '.html' is appended to filename.
        Looks first in modulepath, then in base_path.
        uses cache.'''
        if append_html: 
            filename += '.html'
        mtime = 0
        path = o._find(filename)

        if filename in o._cache:
            mtime = os.stat(path).st_mtime
            if path != o._cache[filename].path or mtime != o._cache[filename].timestamp:
                del o._cache[filename]

        if filename not in o._cache:
            o._cache[filename] = CachedTemplate(
                template = web.template.frender(path),
                timestamp=mtime,
                path = path,
            )
        result = o._cache[filename].template
        return result

    def _find(o, filename):
        if os.path.exists(os.path.join(o._path, filename)):
            path = os.path.join(o._path, filename)
        elif o.base_path and os.path.exists(os.path.join(o.base_path, filename)):
            path = os.path.join(o.base_path, filename)
        else:
            raise UrlDirError('template not found: %s'%filename)
        return path

    def __getattr__(o, name):
        return o.template(name, True)