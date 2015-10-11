/* GStreamer
 * Copyright (C) 2015 Thiago Santos <thiagoss@osg.samsung.com>
 *
 * gstcapsnegoananalyzer.h: tracing module that analyses caps negotiation
 *
 * This library is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Library General Public
 * License as published by the Free Software Foundation; either
 * version 2 of the License, or (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Library General Public License for more details.
 *
 * You should have received a copy of the GNU Library General Public
 * License along with this library; if not, write to the
 * Free Software Foundation, Inc., 51 Franklin St, Fifth Floor,
 * Boston, MA 02110-1301, USA.
 */
/**
 * SECTION:gstcapsnegoananalyzer
 * @short_description: TODO
 */

#ifdef HAVE_CONFIG_H
#  include "config.h"
#endif

#include "gstcapsnegoanalyzer.h"

#include <stdio.h>

GST_DEBUG_CATEGORY_STATIC (gst_caps_nego_analyzer_debug);
#define GST_CAT_DEFAULT gst_caps_nego_analyzer_debug

#define _do_init \
    GST_DEBUG_CATEGORY_INIT (gst_caps_nego_analyzer_debug, "capsnegoanalyzer", \
        0, "capsnegoanalyzer tracer");

#define gst_caps_nego_analyzer_tracer_parent_class parent_class
G_DEFINE_TYPE_WITH_CODE (GstCapsNegoAnalyzerTracer,
    gst_caps_nego_analyzer_tracer, GST_TYPE_TRACER, _do_init);

static void
gst_caps_nego_analyzer_tracer_class_init (GstCapsNegoAnalyzerTracerClass *
    klass)
{
}

static void
gst_caps_nego_analyzer_tracer_init (GstCapsNegoAnalyzerTracer * self)
{
}
