# Copyright 2009-2011 Steven Robertson, Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import pygst
pygst.require("0.10")

import gst
import gobject

from quodlibet import util

def GStreamerSink(pipeline):
    """Try to create a GStreamer pipeline:
    * Try making the pipeline (defaulting to gconfaudiosink or
      autoaudiosink on Windows).
    * If it fails, fall back to autoaudiosink.
    * If that fails, return None

    Returns the pipeline's description and a list of disconnected elements."""

    if not pipeline and not gst.element_factory_find('gconfaudiosink'):
        pipeline = "autoaudiosink"
    elif not pipeline or pipeline == "gconf":
        pipeline = "gconfaudiosink profile=music"

    try: pipe = [gst.parse_launch(element) for element in pipeline.split('!')]
    except gobject.GError, err:
        print_w(_("Invalid GStreamer output pipeline, trying default."))
        try: pipe = [gst.parse_launch("autoaudiosink")]
        except gobject.GError: pipe = None
        else: pipeline = "autoaudiosink"

    if pipe:
        # In case the last element is linkable with a fakesink
        # it is not an audiosink, so we append the default pipeline
        fake = gst.element_factory_make('fakesink')
        try:
            gst.element_link_many(pipe[-1], fake)
        except gst.LinkError: pass
        else:
            gst.element_unlink_many(pipe[-1], fake)
            default, default_text = GStreamerSink("")
            if default:
                return pipe + default, pipeline + " ! "  + default_text
    else:
        print_w(_("Could not create default GStreamer pipeline."))

    return pipe, pipeline


def parse_gstreamer_taglist(tags):
    """Takes a GStreamer taglist and returns a dict containing only
    numeric and unicode values and str keys."""

    merged = {}
    for key in tags.keys():
        value = tags[key]
        # extended-comment sometimes containes a single vorbiscomment or
        # a list of them ["key=value", "key=value"]
        if key == "extended-comment":
            if not isinstance(value, list):
                value = [value]
            for val in value:
                if not isinstance(val, unicode): continue
                split = val.split("=", 1)
                sub_key = util.decode(split[0])
                val = split[-1]
                if sub_key in merged:
                    if val not in merged[sub_key].split("\n"):
                        merged[sub_key] += "\n" + val
                else:
                    merged[sub_key] = val
        elif isinstance(value, gst.Date):
                try: value = u"%d-%d-%d" % (value.year, value.month, value.day)
                except (ValueError, TypeError): continue
                merged[key] = value
        elif isinstance(value, list):
            # there are some lists for id3 containing gst.Buffer (binary data)
            continue
        else:
            if isinstance(value, str):
                value = util.decode(value)

            if not isinstance(value, unicode) and \
                not isinstance(value, (int, long, float)):
                value = unicode(value)

            merged[key] = value

    return merged
