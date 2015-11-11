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

#ifndef __GST_CAPS_NEGO_ANALYZER_TRACER_H__
#define __GST_CAPS_NEGO_ANALYZER_TRACER_H__

#include <gst/gst.h>
#include <gst/gsttracer.h>

G_BEGIN_DECLS

#define GST_TYPE_CAPS_NEGO_ANALYZER_TRACER \
  (gst_caps_nego_analyzer_tracer_get_type())
#define GST_CAPS_NEGO_ANALYZER_TRACER(obj) \
  (G_TYPE_CHECK_INSTANCE_CAST((obj),GST_TYPE_CAPS_NEGO_ANALYZER_TRACER,GstCapsNegoAnalyzerTracer))
#define GST_CAPS_NEGO_ANALYZER_TRACER_CLASS(klass) \
  (G_TYPE_CHECK_CLASS_CAST((klass),GST_TYPE_CAPS_NEGO_ANALYZER_TRACER,GstCapsNegoAnalyzerTracerClass))
#define GST_IS_CAPS_NEGO_ANALYZER_TRACER(obj) \
  (G_TYPE_CHECK_INSTANCE_TYPE((obj),GST_TYPE_CAPS_NEGO_ANALYZER_TRACER))
#define GST_IS_CAPS_NEGO_ANALYZER_TRACER_CLASS(klass) \
  (G_TYPE_CHECK_CLASS_TYPE((klass),GST_TYPE_CAPS_NEGO_ANALYZER_TRACER))
#define GST_CAPS_NEGO_ANALYZER_TRACER_CAST(obj) ((GstCapsNegoAnalyzerTracer *)(obj))

typedef struct _GstCapsNegoAnalyzerTracer GstCapsNegoAnalyzerTracer;
typedef struct _GstCapsNegoAnalyzerTracerClass GstCapsNegoAnalyzerTracerClass;

typedef struct _GstQueryTree
{
  GThread *thread;

  GNode *root;
  GNode *current;
} GstQueryTree;

typedef struct _GstQueryTreeNode
{
  GstQueryType query_type;
  GstPad *pad;
  GstPad *peer;

  GstCaps *caps; /* filter caps or accept caps */

  /* caps query result */
  GstCaps *caps_result;

  /* accept_caps result */
  gboolean accepted_caps;

  /* query result */
  gboolean result;

  guint64 start;
  guint64 end;
} GstQueryTreeNode;

#define GST_QUERY_TREE_NODE_IS_COMPLETE(n) ((n)->end != -1)

/**
 * GstCapsNegoAnalyzerTracer:
 *
 * Opaque #GstCapsNegoAnalyzerTracer data structure
 */
struct _GstCapsNegoAnalyzerTracer {
  GstTracer	 parent;

  /*< private >*/
  GQueue incomplete_trees;
};

struct _GstCapsNegoAnalyzerTracerClass {
  GstTracerClass parent_class;

  /* signals */
};

G_GNUC_INTERNAL GType gst_caps_nego_analyzer_tracer_get_type (void);

G_END_DECLS

#endif /* __GST_CAPS_NEGO_ANALYZER_TRACER_H__ */
