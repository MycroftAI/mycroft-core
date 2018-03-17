# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et
#
# Python MPV library module
# Copyright (C) 2017 Sebastian Götte <code@jaseg.net>
#
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General
# Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more
# details.
#
# You should have received a copy of the GNU Affero General Public License along with this program.  If not, see
# <http://www.gnu.org/licenses/>.
#

from __future__ import unicode_literals
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
from builtins import int
# from builtins import super
from builtins import range
from builtins import str
from future import standard_library
standard_library.install_aliases()
from builtins import object
from ctypes import *
import ctypes.util
import threading
import os
import sys
from warnings import warn
from functools import partial, wraps
import collections
import re
import traceback

# from builtins import *

if os.name == 'nt':
    backend = CDLL('mpv-1.dll')
    fs_enc = 'utf-8'
else:
    import locale
    lc, enc = locale.getlocale(locale.LC_NUMERIC)
    # libmpv requires LC_NUMERIC to be set to "C". Since messing with global variables everyone else relies upon is
    # still better than segfaulting, we are setting LC_NUMERIC to "C".
    locale.setlocale(locale.LC_NUMERIC, 'C')

    sofile = ctypes.util.find_library('mpv')
    if sofile is None:
        raise OSError("Cannot find libmpv in the usual places. Depending on your distro, you may try installing an "
                "mpv-devel or mpv-libs package. If you have libmpv around but this script can't find it, maybe consult "
                "the documentation for ctypes.util.find_library which this script uses to look up the library "
                "filename.")
    backend = CDLL(sofile)
    fs_enc = sys.getfilesystemencoding()


class MpvHandle(c_void_p):
    pass

class MpvOpenGLCbContext(c_void_p):
    pass


class PropertyUnavailableError(AttributeError):
    pass

class ErrorCode(object):
    """For documentation on these, see mpv's libmpv/client.h."""
    SUCCESS                 = 0
    EVENT_QUEUE_FULL        = -1
    NOMEM                   = -2
    UNINITIALIZED           = -3
    INVALID_PARAMETER       = -4
    OPTION_NOT_FOUND        = -5
    OPTION_FORMAT           = -6
    OPTION_ERROR            = -7
    PROPERTY_NOT_FOUND      = -8
    PROPERTY_FORMAT         = -9
    PROPERTY_UNAVAILABLE    = -10
    PROPERTY_ERROR          = -11
    COMMAND                 = -12

    EXCEPTION_DICT = {
             0:     None,
            -1:     lambda *a: MemoryError('mpv event queue full', *a),
            -2:     lambda *a: MemoryError('mpv cannot allocate memory', *a),
            -3:     lambda *a: ValueError('Uninitialized mpv handle used', *a),
            -4:     lambda *a: ValueError('Invalid value for mpv parameter', *a),
            -5:     lambda *a: AttributeError('mpv option does not exist', *a),
            -6:     lambda *a: TypeError('Tried to set mpv option using wrong format', *a),
            -7:     lambda *a: ValueError('Invalid value for mpv option', *a),
            -8:     lambda *a: AttributeError('mpv property does not exist', *a),
            # Currently (mpv 0.18.1) there is a bug causing a PROPERTY_FORMAT error to be returned instead of
            # INVALID_PARAMETER when setting a property-mapped option to an invalid value.
            -9:     lambda *a: TypeError('Tried to get/set mpv property using wrong format, or passed invalid value', *a),
            -10:    lambda *a: PropertyUnavailableError('mpv property is not available', *a),
            -11:    lambda *a: RuntimeError('Generic error getting or setting mpv property', *a),
            -12:    lambda *a: SystemError('Error running mpv command', *a) }

    @staticmethod
    def default_error_handler(ec, *args):
        return ValueError(_mpv_error_string(ec).decode('utf-8'), ec, *args)

    @classmethod
    def raise_for_ec(kls, ec, func, *args):
        ec = 0 if ec > 0 else ec
        ex = kls.EXCEPTION_DICT.get(ec , kls.default_error_handler)
        if ex:
            raise ex(ec, *args)


class MpvFormat(c_int):
    NONE        = 0
    STRING      = 1
    OSD_STRING  = 2
    FLAG        = 3
    INT64       = 4
    DOUBLE      = 5
    NODE        = 6
    NODE_ARRAY  = 7
    NODE_MAP    = 8
    BYTE_ARRAY  = 9

    def __eq__(self, other):
        return self is other or self.value == other or self.value == int(other)

    def __repr__(self):
        return ['NONE', 'STRING', 'OSD_STRING', 'FLAG', 'INT64', 'DOUBLE', 'NODE', 'NODE_ARRAY', 'NODE_MAP',
                'BYTE_ARRAY'][self.value]

    def __hash__(self):
        return self.value


class MpvEventID(c_int):
    NONE                    = 0
    SHUTDOWN                = 1
    LOG_MESSAGE             = 2
    GET_PROPERTY_REPLY      = 3
    SET_PROPERTY_REPLY      = 4
    COMMAND_REPLY           = 5
    START_FILE              = 6
    END_FILE                = 7
    FILE_LOADED             = 8
    TRACKS_CHANGED          = 9
    TRACK_SWITCHED          = 10
    IDLE                    = 11
    PAUSE                   = 12
    UNPAUSE                 = 13
    TICK                    = 14
    SCRIPT_INPUT_DISPATCH   = 15
    CLIENT_MESSAGE          = 16
    VIDEO_RECONFIG          = 17
    AUDIO_RECONFIG          = 18
    METADATA_UPDATE         = 19
    SEEK                    = 20
    PLAYBACK_RESTART        = 21
    PROPERTY_CHANGE         = 22
    CHAPTER_CHANGE          = 23

    ANY = ( SHUTDOWN, LOG_MESSAGE, GET_PROPERTY_REPLY, SET_PROPERTY_REPLY, COMMAND_REPLY, START_FILE, END_FILE,
            FILE_LOADED, TRACKS_CHANGED, TRACK_SWITCHED, IDLE, PAUSE, UNPAUSE, TICK, SCRIPT_INPUT_DISPATCH,
            CLIENT_MESSAGE, VIDEO_RECONFIG, AUDIO_RECONFIG, METADATA_UPDATE, SEEK, PLAYBACK_RESTART, PROPERTY_CHANGE,
            CHAPTER_CHANGE )

    def __repr__(self):
        return ['NONE', 'SHUTDOWN', 'LOG_MESSAGE', 'GET_PROPERTY_REPLY', 'SET_PROPERTY_REPLY', 'COMMAND_REPLY',
                'START_FILE', 'END_FILE', 'FILE_LOADED', 'TRACKS_CHANGED', 'TRACK_SWITCHED', 'IDLE', 'PAUSE', 'UNPAUSE',
                'TICK', 'SCRIPT_INPUT_DISPATCH', 'CLIENT_MESSAGE', 'VIDEO_RECONFIG', 'AUDIO_RECONFIG',
                'METADATA_UPDATE', 'SEEK', 'PLAYBACK_RESTART', 'PROPERTY_CHANGE', 'CHAPTER_CHANGE'][self.value]

    @classmethod
    def from_str(kls, s):
        return getattr(kls, s.upper().replace('-', '_'))


identity_decoder = lambda b: b
strict_decoder = lambda b: b.decode('utf-8')
def lazy_decoder(b):
    try:
        return b.decode('utf-8')
    except UnicodeDecodeError:
        return b

class MpvNodeList(Structure):
    def array_value(self, decoder=identity_decoder):
        return [ self.values[i].node_value(decoder) for i in range(self.num) ]

    def dict_value(self, decoder=identity_decoder):
        return { self.keys[i].decode('utf-8'):
                self.values[i].node_value(decoder) for i in range(self.num) }

class MpvByteArray(Structure):
    _fields_ = [('data', c_void_p),
                ('size', c_size_t)]

    def bytes_value(self):
        return cast(self.data, POINTER(c_char))[:self.size]

class MpvNode(Structure):
    _fields_ = [('val', c_longlong),
                ('format', MpvFormat)]

    def node_value(self, decoder=identity_decoder):
        print(self.val)
        # return MpvNode.node_cast_value(byref(c_void_p(self.val)), self.format.value, decoder)
        return MpvNode.node_cast_value(byref(c_int64(self.val)), self.format.value, decoder)

    @staticmethod
    def node_cast_value(v, fmt=MpvFormat.NODE, decoder=identity_decoder):
        return {
            MpvFormat.NONE:         lambda v: None,
            MpvFormat.STRING:       lambda v: decoder(cast(v, POINTER(c_char_p)).contents.value),
            MpvFormat.OSD_STRING:   lambda v: cast(v, POINTER(c_char_p)).contents.value.decode('utf-8'),
            MpvFormat.FLAG:         lambda v: bool(cast(v, POINTER(c_int)).contents.value),
            MpvFormat.INT64:        lambda v: cast(v, POINTER(c_longlong)).contents.value,
            MpvFormat.DOUBLE:       lambda v: cast(v, POINTER(c_double)).contents.value,
            MpvFormat.NODE:         lambda v: cast(v, POINTER(MpvNode)).contents.node_value(decoder),
            MpvFormat.NODE_ARRAY:   lambda v: cast(v, POINTER(POINTER(MpvNodeList))).contents.contents.array_value(decoder),
            MpvFormat.NODE_MAP:     lambda v: cast(v, POINTER(POINTER(MpvNodeList))).contents.contents.dict_value(decoder),
            MpvFormat.BYTE_ARRAY:   lambda v: cast(v, POINTER(POINTER(MpvByteArray))).contents.contents.bytes_value(),
            }[fmt](v)

MpvNodeList._fields_ = [('num', c_int),
                        ('values', POINTER(MpvNode)),
                        ('keys', POINTER(c_char_p))]

class MpvSubApi(c_int):
    MPV_SUB_API_OPENGL_CB   = 1

class MpvEvent(Structure):
    _fields_ = [('event_id', MpvEventID),
                ('error', c_int),
                ('reply_userdata', c_ulonglong),
                ('data', c_void_p)]

    def as_dict(self, decoder=identity_decoder):
        dtype = {MpvEventID.END_FILE:               MpvEventEndFile,
                MpvEventID.PROPERTY_CHANGE:         MpvEventProperty,
                MpvEventID.GET_PROPERTY_REPLY:      MpvEventProperty,
                MpvEventID.LOG_MESSAGE:             MpvEventLogMessage,
                MpvEventID.SCRIPT_INPUT_DISPATCH:   MpvEventScriptInputDispatch,
                MpvEventID.CLIENT_MESSAGE:          MpvEventClientMessage
            }.get(self.event_id.value, None)
        return {'event_id': self.event_id.value,
                'error': self.error,
                'reply_userdata': self.reply_userdata,
                'event': cast(self.data, POINTER(dtype)).contents.as_dict(decoder=decoder) if dtype else None}

class MpvEventProperty(Structure):
    _fields_ = [('name', c_char_p),
                ('format', MpvFormat),
                ('data', c_void_p)]
    def as_dict(self, decoder=identity_decoder):
        value = MpvNode.node_cast_value(self.data, self.format.value, decoder)
        return {'name': self.name.decode('utf-8'),
                'format': self.format,
                'data': self.data,
                'value': value}

class MpvEventLogMessage(Structure):
    _fields_ = [('prefix', c_char_p),
                ('level', c_char_p),
                ('text', c_char_p)]

    def as_dict(self, decoder=identity_decoder):
        return { 'prefix': self.prefix.decode('utf-8'),
                 'level':  self.level.decode('utf-8'),
                 'text':   decoder(self.text).rstrip() }

class MpvEventEndFile(c_int):
    EOF_OR_INIT_FAILURE = 0
    RESTARTED           = 1
    ABORTED             = 2
    QUIT                = 3

    def as_dict(self, decoder=identity_decoder):
        return {'reason': self.value}

class MpvEventScriptInputDispatch(Structure):
    _fields_ = [('arg0', c_int),
                ('type', c_char_p)]

    def as_dict(self, decoder=identity_decoder):
        pass # TODO

class MpvEventClientMessage(Structure):
    _fields_ = [('num_args', c_int),
                ('args', POINTER(c_char_p))]

    def as_dict(self, decoder=identity_decoder):
        return { 'args': [ self.args[i].decode('utf-8') for i in range(self.num_args) ] }

WakeupCallback = CFUNCTYPE(None, c_void_p)

OpenGlCbUpdateFn = CFUNCTYPE(None, c_void_p)
OpenGlCbGetProcAddrFn = CFUNCTYPE(None, c_void_p, c_char_p)

def _handle_func(name, args, restype, errcheck, ctx=MpvHandle):
    func = getattr(backend, name)
    func.argtypes = [ctx] + args if ctx else args
    if restype is not None:
        func.restype = restype
    if errcheck is not None:
        func.errcheck = errcheck
    globals()['_'+name] = func

def bytes_free_errcheck(res, func, *args):
    notnull_errcheck(res, func, *args)
    rv = cast(res, c_void_p).value
    _mpv_free(res)
    return rv

def notnull_errcheck(res, func, *args):
    if res is None:
        raise RuntimeError('Underspecified error in MPV when calling {} with args {!r}: NULL pointer returned.'\
                'Please consult your local debugger.'.format(func.__name__, args))
    return res

ec_errcheck = ErrorCode.raise_for_ec

def _handle_gl_func(name, args=[], restype=None):
    _handle_func(name, args, restype, errcheck=None, ctx=MpvOpenGLCbContext)

backend.mpv_client_api_version.restype = c_ulong
def _mpv_client_api_version():
    ver = backend.mpv_client_api_version()
    return ver>>16, ver&0xFFFF

backend.mpv_free.argtypes = [c_void_p]
_mpv_free = backend.mpv_free

backend.mpv_free_node_contents.argtypes = [c_void_p]
_mpv_free_node_contents = backend.mpv_free_node_contents

backend.mpv_create.restype = MpvHandle
_mpv_create = backend.mpv_create

_handle_func('mpv_create_client',           [c_char_p],                                 MpvHandle, notnull_errcheck)
_handle_func('mpv_client_name',             [],                                         c_char_p, errcheck=None)
_handle_func('mpv_initialize',              [],                                         c_int, ec_errcheck)
_handle_func('mpv_detach_destroy',          [],                                         None, errcheck=None)
_handle_func('mpv_terminate_destroy',       [],                                         None, errcheck=None)
_handle_func('mpv_load_config_file',        [c_char_p],                                 c_int, ec_errcheck)
_handle_func('mpv_get_time_us',             [],                                         c_ulonglong, errcheck=None)

_handle_func('mpv_set_option',              [c_char_p, MpvFormat, c_void_p],            c_int, ec_errcheck)
_handle_func('mpv_set_option_string',       [c_char_p, c_char_p],                       c_int, ec_errcheck)

_handle_func('mpv_command',                 [POINTER(c_char_p)],                        c_int, ec_errcheck)
_handle_func('mpv_command_string',          [c_char_p, c_char_p],                       c_int, ec_errcheck)
_handle_func('mpv_command_async',           [c_ulonglong, POINTER(c_char_p)],           c_int, ec_errcheck)
_handle_func('mpv_command_node',            [POINTER(MpvNode), POINTER(MpvNode)],       c_int, ec_errcheck)
_handle_func('mpv_command_async',           [c_ulonglong, POINTER(MpvNode)],            c_int, ec_errcheck)

_handle_func('mpv_set_property',            [c_char_p, MpvFormat, c_void_p],            c_int, ec_errcheck)
_handle_func('mpv_set_property_string',     [c_char_p, c_char_p],                       c_int, ec_errcheck)
_handle_func('mpv_set_property_async',      [c_ulonglong, c_char_p, MpvFormat,c_void_p],c_int, ec_errcheck)
_handle_func('mpv_get_property',            [c_char_p, MpvFormat, c_void_p],            c_int, ec_errcheck)
_handle_func('mpv_get_property_string',     [c_char_p],                                 c_void_p, bytes_free_errcheck)
_handle_func('mpv_get_property_osd_string', [c_char_p],                                 c_void_p, bytes_free_errcheck)
_handle_func('mpv_get_property_async',      [c_ulonglong, c_char_p, MpvFormat],         c_int, ec_errcheck)
_handle_func('mpv_observe_property',        [c_ulonglong, c_char_p, MpvFormat],         c_int, ec_errcheck)
_handle_func('mpv_unobserve_property',      [c_ulonglong],                              c_int, ec_errcheck)

_handle_func('mpv_event_name',              [c_int],                                    c_char_p, errcheck=None, ctx=None)
_handle_func('mpv_error_string',            [c_int],                                    c_char_p, errcheck=None, ctx=None)

_handle_func('mpv_request_event',           [MpvEventID, c_int],                        c_int, ec_errcheck)
_handle_func('mpv_request_log_messages',    [c_char_p],                                 c_int, ec_errcheck)
_handle_func('mpv_wait_event',              [c_double],                                 POINTER(MpvEvent), errcheck=None)
_handle_func('mpv_wakeup',                  [],                                         None, errcheck=None)
_handle_func('mpv_set_wakeup_callback',     [WakeupCallback, c_void_p],                 None, errcheck=None)
_handle_func('mpv_get_wakeup_pipe',         [],                                         c_int, errcheck=None)

_handle_func('mpv_get_sub_api',             [MpvSubApi],                                c_void_p, notnull_errcheck)

_handle_gl_func('mpv_opengl_cb_set_update_callback',    [OpenGlCbUpdateFn, c_void_p])
_handle_gl_func('mpv_opengl_cb_init_gl',                [c_char_p, OpenGlCbGetProcAddrFn, c_void_p],    c_int)
_handle_gl_func('mpv_opengl_cb_draw',                   [c_int, c_int, c_int],                          c_int)
_handle_gl_func('mpv_opengl_cb_render',                 [c_int, c_int],                                 c_int)
_handle_gl_func('mpv_opengl_cb_report_flip',            [c_ulonglong],                                  c_int)
_handle_gl_func('mpv_opengl_cb_uninit_gl',              [],                                             c_int)


def _mpv_coax_proptype(value, proptype=str):
    """Intelligently coax the given python value into something that can be understood as a proptype property."""
    if type(value) is bytes:
        return value;
    elif type(value) is bool:
        return b'yes' if value else b'no'
    elif proptype in (str, int, float):
        return str(proptype(value)).encode('utf-8')
    else:
        raise TypeError('Cannot coax value of type {} into property type {}'.format(type(value), proptype))

def _make_node_str_list(l):
    """Take a list of python objects and make a MPV string node array from it.

    As an example, the python list ``l = [ "foo", 23, false ]`` will result in the following MPV node object::

        struct mpv_node {
            .format = MPV_NODE_ARRAY,
            .u.list = *(struct mpv_node_array){
                .num = len(l),
                .keys = NULL,
                .values = struct mpv_node[len(l)] {
                    { .format = MPV_NODE_STRING, .u.string = l[0] },
                    { .format = MPV_NODE_STRING, .u.string = l[1] },
                    ...
                }
            }
        }
    """
    char_ps = [ c_char_p(_mpv_coax_proptype(e, str)) for e in l ]
    node_list = MpvNodeList(
        num=len(l),
        keys=None,
        values=( MpvNode * len(l))( *[ MpvNode(
                format=MpvFormat.STRING,
                val=cast(pointer(p), POINTER(c_longlong)).contents) # NOTE: ctypes is kinda crappy here
            for p in char_ps ]))
    node = MpvNode(
        format=MpvFormat.NODE_ARRAY,
        val=addressof(node_list))
    return char_ps, node_list, node, cast(pointer(node), c_void_p)


def _event_generator(handle):
    while True:
        event = _mpv_wait_event(handle, -1).contents
        if event.event_id.value == MpvEventID.NONE:
            raise StopIteration()
        yield event


def _event_loop(event_handle, playback_cond, event_callbacks, message_handlers, property_handlers, log_handler):
    for event in _event_generator(event_handle):
        try:
            devent = event.as_dict(decoder=lazy_decoder) # copy data from ctypes
            eid = devent['event_id']
            for callback in event_callbacks:
                callback(devent)
            if eid in (MpvEventID.SHUTDOWN, MpvEventID.END_FILE):
                with playback_cond:
                    playback_cond.notify_all()
            if eid == MpvEventID.PROPERTY_CHANGE:
                pc = devent['event']
                name, value, _fmt = pc['name'], pc['value'], pc['format']

                for handler in property_handlers[name]:
                    handler(name, value)
            if eid == MpvEventID.LOG_MESSAGE and log_handler is not None:
                ev = devent['event']
                log_handler(ev['level'], ev['prefix'], ev['text'])
            if eid == MpvEventID.CLIENT_MESSAGE:
                # {'event': {'args': ['key-binding', 'foo', 'u-', 'g']}, 'reply_userdata': 0, 'error': 0, 'event_id': 16}
                _3to2list = list(devent['event']['args'])
                target, args, = _3to2list[:1] + [_3to2list[1:]]
                if target in message_handlers:
                    message_handlers[target](*args)
            if eid == MpvEventID.SHUTDOWN:
                _mpv_detach_destroy(event_handle)
                return
        except Exception as e:
            traceback.print_exc()

_py_to_mpv = lambda name: name.replace('_', '-')
_mpv_to_py = lambda name: name.replace('-', '_')

class _Proxy(object):
    def __init__(self, mpv):
        super(_Proxy, self).__setattr__('mpv', mpv)

class _PropertyProxy(_Proxy):
    def __dir__(self):
        return super(_PropertyProxy, self).__dir__() + [ name.replace('-', '_') for name in self.mpv.property_list ]

class _FileLocalProxy(_Proxy):
    def __getitem__(self, name):
        return self.mpv.__getitem__(name, file_local=True)

    def __setitem__(self, name, value):
        return self.mpv.__setitem__(name, value, file_local=True)

    def __iter__(self):
        return iter(self.mpv)

class _OSDPropertyProxy(_PropertyProxy):
    def __getattr__(self, name):
        return self.mpv._get_property(_py_to_mpv(name), fmt=MpvFormat.OSD_STRING)

    def __setattr__(self, _name, _value):
        raise AttributeError('OSD properties are read-only. Please use the regular property API for writing.')

class _DecoderPropertyProxy(_PropertyProxy):
    def __init__(self, mpv, decoder):
        super(_DecoderPropertyProxy, self).__init__(mpv)
        super(_DecoderPropertyProxy, self).__setattr__('_decoder', decoder)

    def __getattr__(self, name):
        return self.mpv._get_property(_py_to_mpv(name), decoder=self._decoder)

    def __setattr__(self, name, value):
        setattr(self.mpv, _py_to_mpv(name), value)

class MPV(object):
    """See man mpv(1) for the details of the implemented commands. All mpv properties can be accessed as
    ``my_mpv.some_property`` and all mpv options can be accessed as ``my_mpv['some-option']``.

    By default, properties are returned as decoded ``str`` and an error is thrown if the value does not contain valid
    utf-8. To get a decoded ``str`` if possibly but ``bytes`` instead of an error if not, use
    ``my_mpv.lazy.some_property``. To always get raw ``bytes``, use ``my_mpv.raw.some_property``.  To access a
    property's decoded OSD value, use ``my_mpv.osd.some_property``.

    To get API information on an option, use ``my_mpv.option_info('option-name')``. To get API information on a
    property, use ``my_mpv.properties['property-name']``. Take care to use mpv's dashed-names instead of the
    underscore_names exposed on the python object.

    To make your program not barf hard the first time its used on a weird file system **always** access properties
    containing file names or file tags through ``MPV.raw``.  """
    def __init__(self, *extra_mpv_flags, **extra_mpv_opts):
        if 'loglevel' in extra_mpv_opts: loglevel = extra_mpv_opts['loglevel']; del extra_mpv_opts['loglevel']
        else: loglevel = None
        if 'start_event_thread' in extra_mpv_opts: start_event_thread = extra_mpv_opts['start_event_thread']; del extra_mpv_opts['start_event_thread']
        else: start_event_thread = True
        if 'log_handler' in extra_mpv_opts: log_handler = extra_mpv_opts['log_handler']; del extra_mpv_opts['log_handler']
        else: log_handler = None
        """Create an MPV instance.

        Extra arguments and extra keyword arguments will be passed to mpv as options.
        """

        self.handle = _mpv_create()
        self._event_thread = None

        _mpv_set_option_string(self.handle, b'audio-display', b'no')
        istr = lambda o: ('yes' if o else 'no') if type(o) is bool else str(o)
        try:
            for flag in extra_mpv_flags:
                _mpv_set_option_string(self.handle, flag.encode('utf-8'), b'')
            for k,v in extra_mpv_opts.items():
                _mpv_set_option_string(self.handle, k.replace('_', '-').encode('utf-8'), istr(v).encode('utf-8'))
        finally:
            _mpv_initialize(self.handle)

        self.osd = _OSDPropertyProxy(self)
        self.file_local = _FileLocalProxy(self)
        self.raw    = _DecoderPropertyProxy(self, identity_decoder)
        self.strict = _DecoderPropertyProxy(self, strict_decoder)
        self.lazy   = _DecoderPropertyProxy(self, lazy_decoder)

        self._event_callbacks = []
        self._property_handlers = collections.defaultdict(lambda: [])
        self._message_handlers = {}
        self._key_binding_handlers = {}
        self._playback_cond = threading.Condition()
        self._event_handle = _mpv_create_client(self.handle, b'py_event_handler')
        self._loop = partial(_event_loop, self._event_handle, self._playback_cond, self._event_callbacks,
                self._message_handlers, self._property_handlers, log_handler)
        if loglevel is not None or log_handler is not None:
            self.set_loglevel(loglevel or 'terminal-default')
        if start_event_thread:
            self._event_thread = threading.Thread(target=self._loop, name='MPVEventHandlerThread')
            self._event_thread.setDaemon(True)
            self._event_thread.start()
        else:
            self._event_thread = None

    def wait_for_playback(self):
        """Waits until playback of the current title is paused or done."""
        with self._playback_cond:
            self._playback_cond.wait()

    def wait_for_property(self, name, cond=lambda val: val, level_sensitive=True):
        """Waits until ``cond`` evaluates to a truthy value on the named property. This can be used to wait for
        properties such as ``idle_active`` indicating the player is done with regular playback and just idling around
        """
        sema = threading.Semaphore(value=0)
        def observer(name, val):
            if cond(val):
                sema.release()
        self.observe_property(name, observer)
        if not level_sensitive or not cond(getattr(self, name.replace('-', '_'))):
            sema.acquire()
        self.unobserve_property(name, observer)

    def __del__(self):
        if self.handle:
            self.terminate()

    def terminate(self):
        """Properly terminates this player instance. Preferably use this instead of relying on python's garbage
        collector to cause this to be called from the object's destructor.
        """
        self.handle, handle = None, self.handle
        if threading.current_thread() is self._event_thread:
            # Handle special case to allow event handle to be detached.
            # This is necessary since otherwise the event thread would deadlock itself.
            grim_reaper = threading.Thread(target=lambda: _mpv_terminate_destroy(handle))
            grim_reaper.start()
        else:
            _mpv_terminate_destroy(handle)
            if self._event_thread:
                self._event_thread.join()

    def set_loglevel(self, level):
        """Set MPV's log level. This adjusts which output will be sent to this object's log handlers. If you just want
        mpv's regular terminal output, you don't need to adjust this but just need to pass a log handler to the MPV
        constructur such as ``MPV(log_handler=print)``.

        Valid log levels are "no", "fatal", "error", "warn", "info", "v" "debug" and "trace". For details see your mpv's
        client.h header file.
        """
        _mpv_request_log_messages(self._event_handle, level.encode('utf-8'))

    def command(self, name, *args):
        """Execute a raw command."""
        args = [name.encode('utf-8')] + [ (arg if type(arg) is bytes else str(arg).encode('utf-8'))
                for arg in args if arg is not None ] + [None]
        _mpv_command(self.handle, (c_char_p*len(args))(*args))

    def node_command(self, name, *args, **_3to2kwargs):
        if 'decoder' in _3to2kwargs: decoder = _3to2kwargs['decoder']; del _3to2kwargs['decoder']
        else: decoder = strict_decoder
        _1, _2, _3, pointer = _make_node_str_list([name] + arg)
        out = cast(create_string_buffer(sizeof(MpvNode)), POINTER(MpvNode))
        outptr = out #byref(out)
        ppointer = cast(pointer, POINTER(MpvNode))
        _mpv_command_node(self.handle, ppointer, outptr)
        rv = MpvNode.node_cast_value(outptr, MpvFormat.NODE, decoder)
        _mpv_free_node_contents(outptr)
        return rv

    def seek(self, amount, reference="relative", precision="default-precise"):
        """Mapped mpv seek command, see man mpv(1)."""
        self.command('seek', amount, reference, precision)

    def revert_seek(self):
        """Mapped mpv revert_seek command, see man mpv(1)."""
        self.command('revert_seek');

    def frame_step(self):
        """Mapped mpv frame_step command, see man mpv(1)."""
        self.command('frame_step')

    def frame_back_step(self):
        """Mapped mpv frame_back_step command, see man mpv(1)."""
        self.command('frame_back_step')

    def property_add(self, name, value=1):
        """Add the given value to the property's value. On overflow or underflow, clamp the property to the maximum. If
        ``value`` is omitted, assume ``1``.
        """
        self.command('add', name, value)

    def property_multiply(self, name, factor):
        """Multiply the value of a property with a numeric factor."""
        self.command('multiply', name, factor)

    def cycle(self, name, direction='up'):
        """Cycle the given property. ``up`` and ``down`` set the cycle direction. On overflow, set the property back to
        the minimum, on underflow set it to the maximum. If ``up`` or ``down`` is omitted, assume ``up``.
        """
        self.command('cycle', name, direction)

    def screenshot(self, includes='subtitles', mode='single'):
        """Mapped mpv screenshot command, see man mpv(1)."""
        self.command('screenshot', includes, mode)

    def screenshot_to_file(self, filename, includes='subtitles'):
        """Mapped mpv screenshot_to_file command, see man mpv(1)."""
        self.command('screenshot_to_file', filename.encode(fs_enc), includes)

    def screenshot_raw(self, includes='subtitles'):
        """Mapped mpv screenshot_raw command, see man mpv(1). Returns a pillow Image object."""
        from PIL import Image
        res = self.node_command('screenshot-raw', includes)
        if res['format'] != 'bgr0':
            raise ValueError('Screenshot in unknown format "{}". Currently, only bgr0 is supported.'
                    .format(res['format']))
        img = Image.frombytes('RGBA', (res['w'], res['h']), res['data'])
        b,g,r,a = img.split()
        return Image.merge('RGB', (r,g,b))

    def playlist_next(self, mode='weak'):
        """Mapped mpv playlist_next command, see man mpv(1)."""
        self.command('playlist_next', mode)

    def playlist_prev(self, mode='weak'):
        """Mapped mpv playlist_prev command, see man mpv(1)."""
        self.command('playlist_prev', mode)

    def key_press(self, keyname):
        """Mapped mpv key_press command, see man mpv(1)."""
        self.command('key_press', keyname)

    def stop(self):
        """Mapped mpv stop command, see man mpv(1)."""
        self.command('stop')

    @staticmethod
    def _encode_options(options):
        return ','.join('{}={}'.format(str(key), str(val)) for key, val in options.items())

    def loadfile(self, filename, mode='replace', **options):
        """Mapped mpv loadfile command, see man mpv(1)."""
        self.command('loadfile', filename.encode(fs_enc), mode, MPV._encode_options(options))

    def loadlist(self, playlist, mode='replace'):
        """Mapped mpv loadlist command, see man mpv(1)."""
        self.command('loadlist', playlist.encode(fs_enc), mode)

    def playlist_clear(self):
        """Mapped mpv playlist_clear command, see man mpv(1)."""
        self.command('playlist_clear')

    def playlist_remove(self, index='current'):
        """Mapped mpv playlist_remove command, see man mpv(1)."""
        self.command('playlist_remove', index)

    def playlist_move(self, index1, index2):
        """Mapped mpv playlist_move command, see man mpv(1)."""
        self.command('playlist_move', index1, index2)

    def run(self, command, *args):
        """Mapped mpv run command, see man mpv(1)."""
        self.command('run', command, *args)

    def quit(self, code=None):
        """Mapped mpv quit command, see man mpv(1)."""
        self.command('quit', code)

    def quit_watch_later(self, code=None):
        """Mapped mpv quit_watch_later command, see man mpv(1)."""
        self.command('quit_watch_later', code)

    def sub_add(self, filename):
        """Mapped mpv sub_add command, see man mpv(1)."""
        self.command('sub_add', filename.encode(fs_enc))

    def sub_remove(self, sub_id=None):
        """Mapped mpv sub_remove command, see man mpv(1)."""
        self.command('sub_remove', sub_id)

    def sub_reload(self, sub_id=None):
        """Mapped mpv sub_reload command, see man mpv(1)."""
        self.command('sub_reload', sub_id)

    def sub_step(self, skip):
        """Mapped mpv sub_step command, see man mpv(1)."""
        self.command('sub_step', skip)

    def sub_seek(self, skip):
        """Mapped mpv sub_seek command, see man mpv(1)."""
        self.command('sub_seek', skip)

    def toggle_osd(self):
        """Mapped mpv osd command, see man mpv(1)."""
        self.command('osd')

    def show_text(self, string, duration='-', level=None):
        """Mapped mpv show_text command, see man mpv(1)."""
        self.command('show_text', string, duration, level)

    def show_progress(self):
        """Mapped mpv show_progress command, see man mpv(1)."""
        self.command('show_progress')

    def discnav(self, command):
        """Mapped mpv discnav command, see man mpv(1)."""
        self.command('discnav', command)

    def write_watch_later_config(self):
        """Mapped mpv write_watch_later_config command, see man mpv(1)."""
        self.command('write_watch_later_config')

    def overlay_add(self, overlay_id, x, y, file_or_fd, offset, fmt, w, h, stride):
        """Mapped mpv overlay_add command, see man mpv(1)."""
        self.command('overlay_add', overlay_id, x, y, file_or_fd, offset, fmt, w, h, stride)

    def overlay_remove(self, overlay_id):
        """Mapped mpv overlay_remove command, see man mpv(1)."""
        self.command('overlay_remove', overlay_id)

    def script_message(self, *args):
        """Mapped mpv script_message command, see man mpv(1)."""
        self.command('script_message', *args)

    def script_message_to(self, target, *args):
        """Mapped mpv script_message_to command, see man mpv(1)."""
        self.command('script_message_to', target, *args)

    def observe_property(self, name, handler):
        """Register an observer on the named property. An observer is a function that is called with the new property
        value every time the property's value is changed. The basic function signature is ``fun(property_name,
        new_value)`` with new_value being the decoded property value as a python object. This function can be used as a
        function decorator if no handler is given.

        To unregister the observer, call either of ``mpv.unobserve_property(name, handler)``,
        ``mpv.unobserve_all_properties(handler)`` or the handler's ``unregister_mpv_properties`` attribute::

            @player.observe_property('volume')
            def my_handler(new_volume, *):
                print("It's loud!", volume)

            my_handler.unregister_mpv_properties()
        """
        self._property_handlers[name].append(handler)
        _mpv_observe_property(self._event_handle, hash(name)&0xffffffffffffffff, name.encode('utf-8'), MpvFormat.NODE)

    def property_observer(self, name):
        """Function decorator to register a property observer. See ``MPV.observe_property`` for details."""
        def wrapper(fun):
            self.observe_property(name, fun)
            fun.unobserve_mpv_properties = lambda: self.unobserve_property(name, fun)
            return fun
        return wrapper

    def unobserve_property(self, name, handler):
        """Unregister a property observer. This requires both the observed property's name and the handler function that
        was originally registered as one handler could be registered for several properties. To unregister a handler
        from *all* observed properties see ``unobserve_all_properties``.
        """
        self._property_handlers[name].remove(handler)
        if not self._property_handlers[name]:
            _mpv_unobserve_property(self._event_handle, hash(name)&0xffffffffffffffff)

    def unobserve_all_properties(self, handler):
        """Unregister a property observer from *all* observed properties."""
        for name in self._property_handlers:
            self.unobserve_property(name, handler)

    def register_message_handler(self, target, handler=None):
        """Register a mpv script message handler. This can be used to communicate with embedded lua scripts. Pass the
        script message target name this handler should be listening to and the handler function.

        WARNING: Only one handler can be registered at a time for any given target.

        To unregister the message handler, call its ``unregister_mpv_messages`` function::

            player = mpv.MPV()
            @player.message_handler('foo')
            def my_handler(some, args):
                print(args)

            my_handler.unregister_mpv_messages()
        """
        self._register_message_handler_internal(target, handler)

    def _register_message_handler_internal(self, target, handler):
        self._message_handlers[target] = handler

    def unregister_message_handler(self, target_or_handler):
        """Unregister a mpv script message handler for the given script message target name.

        You can also call the ``unregister_mpv_messages`` function attribute set on the handler function when it is
        registered.
        """
        if isinstance(target_or_handler, str):
            del self._message_handlers[target_or_handler]
        else:
            for key, val in self._message_handlers.items():
                if val == target_or_handler:
                    del self._message_handlers[key]

    def message_handler(self, target):
        """Decorator to register a mpv script message handler.

        WARNING: Only one handler can be registered at a time for any given target.

        To unregister the message handler, call its ``unregister_mpv_messages`` function::

            player = mpv.MPV()
            @player.message_handler('foo')
            def my_handler(some, args):
                print(args)

            my_handler.unregister_mpv_messages()
        """
        def register(handler):
            self._register_message_handler_internal(target, handler)
            handler.unregister_mpv_messages = lambda: self.unregister_message_handler(handler)
            return handler
        return register

    def register_event_callback(self, callback):
        """Register a blanket event callback receiving all event types.

        To unregister the event callback, call its ``unregister_mpv_events`` function::

            player = mpv.MPV()
            @player.event_callback('shutdown')
            def my_handler(event):
                print('It ded.')

            my_handler.unregister_mpv_events()
        """
        self._event_callbacks.append(callback)

    def unregister_event_callback(self, callback):
        """Unregiser an event callback."""
        self._event_callbacks.remove(callback)

    def event_callback(self, *event_types):
        """Function decorator to register a blanket event callback for the given event types. Event types can be given
        as str (e.g.  'start-file'), integer or MpvEventID object.

        WARNING: Due to the way this is filtering events, this decorator cannot be chained with itself.

        To unregister the event callback, call its ``unregister_mpv_events`` function::

            player = mpv.MPV()
            @player.event_callback('shutdown')
            def my_handler(event):
                print('It ded.')

            my_handler.unregister_mpv_events()
        """
        def register(callback):
            types = [MpvEventID.from_str(t) if isinstance(t, str) else t for t in event_types] or MpvEventID.ANY
            @wraps(callback)
            def wrapper(event, *args, **kwargs):
                if event['event_id'] in types:
                    callback(event, *args, **kwargs)
            self._event_callbacks.append(wrapper)
            wrapper.unregister_mpv_events = partial(self.unregister_event_callback, wrapper)
            return wrapper
        return register

    @staticmethod
    def _binding_name(callback_or_cmd):
        return 'py_kb_{:016x}'.format(hash(callback_or_cmd)&0xffffffffffffffff)

    def on_key_press(self, keydef, mode='force'):
        """Function decorator to register a simplified key binding. The callback is called whenever the key given is
        *pressed*.

        To unregister the callback function, you can call its ``unregister_mpv_key_bindings`` attribute::

            player = mpv.MPV()
            @player.on_key_press('Q')
            def binding():
                print('blep')

            binding.unregister_mpv_key_bindings()

        WARNING: For a single keydef only a single callback/command can be registered at the same time. If you register
        a binding multiple times older bindings will be overwritten and there is a possibility of references leaking. So
        don't do that.

        The BIG FAT WARNING regarding untrusted keydefs from the key_binding method applies here as well.
        """
        def register(fun):
            @self.key_binding(keydef, mode)
            @wraps(fun)
            def wrapper(state='p-', name=None):
                if state[0] in ('d', 'p'):
                    fun()
            return wrapper
        return register

    def key_binding(self, keydef, mode='force'):
        """Function decorator to register a low-level key binding.

        The callback function signature is ``fun(key_state, key_name)`` where ``key_state`` is either ``'U'`` for "key
        up" or ``'D'`` for "key down".

        The keydef format is: ``[Shift+][Ctrl+][Alt+][Meta+]<key>`` where ``<key>`` is either the literal character the
        key produces (ASCII or Unicode character), or a symbolic name (as printed by ``mpv --input-keylist``).

        To unregister the callback function, you can call its ``unregister_mpv_key_bindings`` attribute::

            player = mpv.MPV()
            @player.key_binding('Q')
            def binding(state, name):
                print('blep')

            binding.unregister_mpv_key_bindings()

        WARNING: For a single keydef only a single callback/command can be registered at the same time. If you register
        a binding multiple times older bindings will be overwritten and there is a possibility of references leaking. So
        don't do that.

        BIG FAT WARNING: mpv's key binding mechanism is pretty powerful.  This means, you essentially get arbitrary code
        exectution through key bindings. This interface makes some limited effort to sanitize the keydef given in the
        first parameter, but YOU SHOULD NOT RELY ON THIS IN FOR SECURITY. If your input comes from config files, this is
        completely fine--but, if you are about to pass untrusted input into this parameter, better double-check whether
        this is secure in your case.
        """
        def register(fun):
            fun.mpv_key_bindings = getattr(fun, 'mpv_key_bindings', []) + [keydef]
            def unregister_all():
                for keydef in fun.mpv_key_bindings:
                    self.unregister_key_binding(keydef)
            fun.unregister_mpv_key_bindings = unregister_all

            self.register_key_binding(keydef, fun, mode)
            return fun
        return register

    def register_key_binding(self, keydef, callback_or_cmd, mode='force'):
        """Register a key binding. This takes an mpv keydef and either a string containing a mpv command or a python
        callback function.  See ``MPV.key_binding`` for details.
        """
        if not re.match(r'(Shift+)?(Ctrl+)?(Alt+)?(Meta+)?(.|\w+)', keydef):
            raise ValueError('Invalid keydef. Expected format: [Shift+][Ctrl+][Alt+][Meta+]<key>\n'
                    '<key> is either the literal character the key produces (ASCII or Unicode character), or a '
                    'symbolic name (as printed by --input-keylist')
        binding_name = MPV._binding_name(keydef)
        if callable(callback_or_cmd):
            self._key_binding_handlers[binding_name] = callback_or_cmd
            self.register_message_handler('key-binding', self._handle_key_binding_message)
            self.command('define-section',
                    binding_name, '{} script-binding py_event_handler/{}'.format(keydef, binding_name), mode)
        elif isinstance(callback_or_cmd, str):
            self.command('define-section', binding_name, '{} {}'.format(keydef, callback_or_cmd), mode)
        else:
            raise TypeError('register_key_binding expects either an str with an mpv command or a python callable.')
        self.command('enable-section', binding_name, 'allow-hide-cursor+allow-vo-dragging')

    def _handle_key_binding_message(self, binding_name, key_state, key_name=None):
        self._key_binding_handlers[binding_name](key_state, key_name)

    def unregister_key_binding(self, keydef):
        """Unregister a key binding by keydef."""
        binding_name = MPV._binding_name(keydef)
        self.command('disable-section', binding_name)
        self.command('define-section', binding_name, '')
        if binding_name in self._key_binding_handlers:
            del self._key_binding_handlers[binding_name]
            if not self._key_binding_handlers:
                self.unregister_message_handler('key-binding')

    # Convenience functions
    def play(self, filename):
        """Play a path or URL (requires ``ytdl`` option to be set)."""
        self.loadfile(filename)

    @property
    def playlist_filenames(self):
        """Return all playlist item file names/URLs as a list of strs."""
        return [element['filename'] for element in self.playlist]

    def playlist_append(self, filename, **options):
        """Append a path or URL to the playlist. This does not start playing the file automatically. To do that, use
        ``MPV.loadfile(filename, 'append-play')``."""
        self.loadfile(filename, 'append', **options)

    # Property accessors
    def _get_property(self, name, decoder=strict_decoder, fmt=MpvFormat.NODE):
        out = cast(create_string_buffer(sizeof(c_void_p)), c_void_p)
        outptr = byref(out)
        try:
            cval = _mpv_get_property(self.handle, name.encode('utf-8'), fmt, outptr)
            rv = MpvNode.node_cast_value(outptr, fmt, decoder)
            if fmt is MpvFormat.NODE:
                _mpv_free_node_contents(outptr)
            return rv
        except PropertyUnavailableError as ex:
            return None

    def _set_property(self, name, value):
        ename = name.encode('utf-8')
        if isinstance(value, (list, set, dict)):
            _1, _2, _3, pointer = _make_node_str_list(value)
            _mpv_set_property(self.handle, ename, MpvFormat.NODE, pointer)
        else:
            _mpv_set_property_string(self.handle, ename, _mpv_coax_proptype(value))

    def __getattr__(self, name):
        return self._get_property(_py_to_mpv(name), lazy_decoder)

    def __setattr__(self, name, value):
            try:
                if name != 'handle' and not name.startswith('_'):
                    self._set_property(_py_to_mpv(name), value)
                else:
                    super(MPV, self).__setattr__(name, value)
            except AttributeError:
                super(MPV, self).__setattr__(name, value)

    def __dir__(self):
        return super(MPV, self).__dir__() + [ name.replace('-', '_') for name in self.property_list ]

    @property
    def properties(self):
        return { name: self.option_info(name) for name in self.property_list }

    # Dict-like option access
    def __getitem__(self, name, file_local=False):
        """Get an option value."""
        prefix = 'file-local-options/' if file_local else 'options/'
        return self._get_property(prefix+name, lazy_decoder)

    def __setitem__(self, name, value, file_local=False):
        """Set an option value."""
        prefix = 'file-local-options/' if file_local else 'options/'
        return self._set_property(prefix+name, value)

    def __iter__(self):
        """Iterate over all option names."""
        return iter(self.options)

    def option_info(self, name):
        """Get information on the given option."""
        try:
            return self._get_property('option-info/'+name)
        except AttributeError:
            return None