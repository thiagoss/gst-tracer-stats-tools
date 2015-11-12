/* GStreamer
 * Copyright (C) 2015 Thiago Santos <thiagoss@osg.samsung.com>
 *
 * gststatechange.c: tracing module that logs state change related
 *                   events
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
 * SECTION:gststatechange
 * @short_description: TODO
 */

#ifdef HAVE_CONFIG_H
#  include "config.h"
#endif

#include "gststatechange.h"

#include <stdio.h>

GST_DEBUG_CATEGORY_STATIC (gst_state_change_debug);
#define GST_CAT_DEFAULT gst_state_change_debug

#define _do_init \
    GST_DEBUG_CATEGORY_INIT (gst_state_change_debug, "statechange", \
        0, "statechange tracer");

#define gst_state_change_tracer_parent_class parent_class
G_DEFINE_TYPE_WITH_CODE (GstStateChangeTracer,
    gst_state_change_tracer, GST_TYPE_TRACER, _do_init);

static const gchar *
gst_state_get_name (GstState s)
{
  if (s == GST_STATE_NULL)
    return "null";
  if (s == GST_STATE_READY)
    return "ready";
  if (s == GST_STATE_PAUSED)
    return "paused";
  if (s == GST_STATE_PLAYING)
    return "playing";
  if (s == GST_STATE_VOID_PENDING)
    return "void-pending";

  GST_ERROR ("State: %d", (gint) s);

  g_assert_not_reached ();
  return "ERROR";
}

static const gchar *
gst_state_change_return_get_name (GstStateChangeReturn ret)
{
  if (ret == GST_STATE_CHANGE_FAILURE)
    return "failure";
  if (ret == GST_STATE_CHANGE_SUCCESS)
    return "success";
  if (ret == GST_STATE_CHANGE_ASYNC)
    return "async";
  if (ret == GST_STATE_CHANGE_NO_PREROLL)
    return "no-preroll";

  g_assert_not_reached ();
  return "ERROR";
}

static void
do_element_new (GstTracer * tracer, GstClockTime ts, GstElement * element)
{
  GST_INFO ("%" G_GUINT64_FORMAT "$element-new$%p$%" GST_PTR_FORMAT, (guint64) ts,
      element, element);
}

static void
do_change_state_pre (GstTracer * tracer, GstClockTime ts, GstElement * element,
    GstStateChange change)
{
  GST_INFO ("%" G_GUINT64_FORMAT "$element-state-change-pre$%p$%" GST_PTR_FORMAT
      "$%s$%s", (guint64) ts, element, element,
      gst_state_get_name (GST_STATE_TRANSITION_CURRENT (change)),
      gst_state_get_name (GST_STATE_TRANSITION_NEXT (change)));
}

static void
do_change_state_post (GstTracer * tracer, GstClockTime ts, GstElement * element,
    GstStateChange change, GstStateChangeReturn ret)
{
  GST_INFO ("%" G_GUINT64_FORMAT "$element-state-change-post$%p$%" GST_PTR_FORMAT
      "$%s$%s$%s", (guint64) ts, element, element,
      gst_state_get_name (GST_STATE_TRANSITION_CURRENT (change)),
      gst_state_get_name (GST_STATE_TRANSITION_NEXT (change)),
      gst_state_change_return_get_name (ret));
}

static void
do_post_message_pre (GstTracer * tracer, GstClockTime ts, GstElement * element,
    GstMessage * msg)
{
  if (GST_MESSAGE_TYPE (msg) == GST_MESSAGE_ASYNC_DONE) {
    GST_INFO ("%" G_GUINT64_FORMAT "$element-async-done$%p$%" GST_PTR_FORMAT,
        (guint64) ts, element, element);
  }
}

static void
gst_state_change_tracer_class_init (GstStateChangeTracerClass * klass)
{
}

static void
gst_state_change_tracer_init (GstStateChangeTracer * self)
{
  GstTracer *tracer = GST_TRACER (self);

  gst_tracing_register_hook (tracer, "element-new",
      G_CALLBACK (do_element_new));
  gst_tracing_register_hook (tracer, "element-change-state-pre",
      G_CALLBACK (do_change_state_pre));
  gst_tracing_register_hook (tracer, "element-change-state-post",
      G_CALLBACK (do_change_state_post));
  gst_tracing_register_hook (tracer, "element-post-message-pre",
      G_CALLBACK (do_post_message_pre));
}

static gboolean
plugin_init (GstPlugin * plugin)
{
  if (!gst_tracer_register (plugin, "statechange",
          gst_state_change_tracer_get_type ()))
    return FALSE;
  return TRUE;
}

#define PACKAGE "statechange"
GST_PLUGIN_DEFINE (GST_VERSION_MAJOR, GST_VERSION_MINOR, statechange,
    "GStreamer state change tracer", plugin_init, "0.1", "LGPL",
    "statechange", "http://github.com/thiagoss/gst-tracer-stats-tools");
