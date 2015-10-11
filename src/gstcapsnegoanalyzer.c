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

static gint
query_tree_compare_thread (gconstpointer a, gconstpointer b)
{
  const GstQueryTree *ta = a;
  const GThread *thread = b;

  if (ta->thread == thread)
    return 0;

  return 1;
}

static GstQueryTree *
get_incomplete_tree (GstCapsNegoAnalyzerTracer * tracer, GThread * thread)
{
  GstQueryTree *tree = NULL;
  GList *tree_node = g_queue_find_custom (&tracer->incomplete_trees, thread,
      query_tree_compare_thread);

  GST_DEBUG_OBJECT (tracer, "Found tree node for thread %p : %p", thread,
      tree_node);

  if (tree_node)
    tree = tree_node->data;

  if (!tree) {
    tree = g_slice_alloc0 (sizeof (GstQueryTree));
    tree->thread = thread;
    tree->root = NULL;
    g_queue_push_tail (&tracer->incomplete_trees, tree);
  }

  return tree;
}

#define INDENT_STRING "  "

static gboolean
gst_query_tree_node_traverse_print (GNode * node, gpointer udata)
{
  GstQueryTreeNode *n = node->data;
  gint depth = g_node_depth (node);
  GString *string = g_string_new (NULL);

  /* add indent */
  while (depth--) {
    g_string_append (string, INDENT_STRING);
  }

  g_string_append (string, GST_QUERY_TYPE_NAME (n->result_query));
  g_print ("%s\n", string->str);
  g_string_free (string, TRUE);
  return FALSE;
}

static void
gst_query_tree_print (GstQueryTree * tree)
{
  g_node_traverse (tree->root, G_PRE_ORDER, G_TRAVERSE_ALL, -1,
      gst_query_tree_node_traverse_print, NULL);
  g_print ("\n");
}

static GstQueryTreeNode *
create_tree_node (GstQuery * q)
{
  GstQueryTreeNode *tree_node = g_slice_alloc (sizeof (GstQuery));
  tree_node->query = q;
  tree_node->result_query = NULL;

  return tree_node;
}

static void
gst_query_tree_node_set_complete (GstQueryTreeNode * node, GstQuery * q,
    gboolean result)
{
  /* TODO verify proper closing and if the fields are the same */

  g_return_if_fail (GST_QUERY_TYPE (node->query) == GST_QUERY_TYPE (q));

  node->result_query = q;
  node->result = result;
}

static gboolean
gst_query_tree_node_free (GNode * n, gpointer udata)
{
  g_slice_free (GstQueryTreeNode, n->data);
  return FALSE;
}

static void
gst_query_tree_free (GstQueryTree * tree)
{
  if (tree->root) {
    g_node_traverse (tree->root, G_IN_ORDER, G_TRAVERSE_ALL, -1,
        gst_query_tree_node_free, NULL);
    g_node_destroy (tree->root);
  }
  g_slice_free (GstQueryTree, tree);
}

static void
gst_caps_nego_analyzer_tracer_complete_tree (GstCapsNegoAnalyzerTracer * self,
    GstQueryTree * tree)
{
  g_queue_remove (&self->incomplete_trees, tree);

  gst_query_tree_print (tree);

  gst_query_tree_free (tree);
}

static void
gst_query_tree_append_query (GstCapsNegoAnalyzerTracer * tracer,
    GstQueryTree * tree, GstQuery * q)
{
  GstQueryTreeNode *tree_node = create_tree_node (q);

  if (tree->root) {
    g_node_append_data (tree->current, tree_node);
    tree->current = g_node_last_child (tree->current);
  } else {
    tree->root = g_node_new (tree_node);
    tree->current = tree->root;
  }
}

static gboolean
gst_query_tree_append_query_result (GstCapsNegoAnalyzerTracer * tracer,
    GstQueryTree * tree, GstQuery * q, gboolean res)
{
  gst_query_tree_node_set_complete (tree->current->data, q, res);
  tree->current = tree->current->parent;

  if (tree->current == NULL)
    return TRUE;

  return FALSE;
}

static void
do_query_pre (GstCapsNegoAnalyzerTracer * self, guint64 ts, GstPad * this_pad,
    GstQuery * qry)
{
  GThread *thread;
  GstQueryTree *tree;

  switch (GST_QUERY_TYPE (qry)) {
    case GST_QUERY_CAPS:
    case GST_QUERY_ACCEPT_CAPS:
      break;
    default:
      return;
  }

  GST_DEBUG_OBJECT (self, "%" GST_PTR_FORMAT " - pre query", this_pad);

  thread = g_thread_self ();
  tree = get_incomplete_tree (self, thread);
  gst_query_tree_append_query (self, tree, qry);
}

static void
do_query_post (GstCapsNegoAnalyzerTracer * self, guint64 ts, GstPad * this_pad,
    gboolean res, GstQuery * qry)
{
  GThread *thread;
  GstQueryTree *tree;

  switch (GST_QUERY_TYPE (qry)) {
    case GST_QUERY_CAPS:
    case GST_QUERY_ACCEPT_CAPS:
      break;
    default:
      return;
  }

  GST_DEBUG_OBJECT (self, "%" GST_PTR_FORMAT " - post query", this_pad);

  thread = g_thread_self ();
  tree = get_incomplete_tree (self, thread);
  if (gst_query_tree_append_query_result (self, tree, qry, res))
    gst_caps_nego_analyzer_tracer_complete_tree (self, tree);
}

static void
gst_caps_nego_analyzer_tracer_class_init (GstCapsNegoAnalyzerTracerClass *
    klass)
{
}

static void
gst_caps_nego_analyzer_tracer_init (GstCapsNegoAnalyzerTracer * self)
{
  GstTracer *tracer = GST_TRACER (self);

  gst_tracing_register_hook (tracer, "pad-query-pre",
      G_CALLBACK (do_query_pre));
  gst_tracing_register_hook (tracer, "pad-query-post",
      G_CALLBACK (do_query_post));
}

static gboolean
plugin_init (GstPlugin * plugin)
{
  if (!gst_tracer_register (plugin, "capsnegoanalyzer",
          gst_caps_nego_analyzer_tracer_get_type ()))
    return FALSE;
  return TRUE;
}

#define PACKAGE "capsnegoanalyzer"
GST_PLUGIN_DEFINE (GST_VERSION_MAJOR, GST_VERSION_MINOR, capsnegocanalyzer,
    "GStreamer caps nego tracer", plugin_init, "0.1", "LGPL",
    "capsnegoanalyzer", "http://github.com/thiagoss/gst-tracer-stats-tools");
