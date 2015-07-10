import sys

import gi
gi.require_version('Gst', '1.0')
from gi.repository import GObject, Gst

class GstTracerLineParsingException(Exception): pass

global element_names
element_names = {}

global pad_names
pad_names = {}

def get_element_name(n):
    if n in element_names:
        return element_names[n]
    else: return '--%s--' % str(n)

def get_pad_name(n):
    if n in pad_names:
        return pad_names[n]
    else: return '--%s--' % str(n)

class GstTracerLine(object):
    def __init__(self, line):
        self.line = line
        tokens = line.split()
        if len(tokens) < 8:
            raise GstTracerLineParsingException
        if 'TRACE' not in tokens[3]:
            raise GstTracerLineParsingException
        if 'GST_TRACER' != tokens[6]:
            raise GstTracerLineParsingException

        self.time = tokens[0]

        #FIXME some structures fail parsing
        self.structure = Gst.Structure.from_string(' '.join(tokens[8:]))[0]

    def get_thread(self):
        return self.structure.get_value('thread-id')

    def is_query(self):
        return self.structure and self.structure.get_name() == 'query'

    def is_new_element(self):
        return self.structure and self.structure.get_name() == 'new-element'

    def is_new_pad(self):
        return self.structure and self.structure.get_name() == 'new-pad'

    # QUERY RELATED FUNCTIONS
    def is_query_type(self, name):
        return self.structure.get_value('name') == name

    def query_between_elements(self):
        return self.structure.get_value('elem-ix') != 4294967295 and \
               self.structure.get_value('peer-elem-ix') != 4294967295

    def get_query_origin(self):
        return self.structure.get_value('elem-ix')

    def get_query_origin_pad(self):
        return self.structure.get_value('pad-ix')

    def get_query_peer(self):
        return self.structure.get_value('peer-elem-ix')

    def get_query_peer_pad(self):
        return self.structure.get_value('peer-pad-ix')

    def get_query_structure(self):
        return self.structure.get_value('structure')

    def is_post_query(self):
        return self.structure.has_field('res')

    # END OF QUERY RELATED FUNCTIONS

    def __str__(self):
        return self.line

class GstCapsQueryTree(object):
    def __init__(self, root):
        self.root = root
        self.current = root

    def add_node(self, node):
        if node.queryline.is_post_query():
#            assert self.current.queryline == node.queryline
            self.current.queryline = node.queryline
            self.current.close()
            self.current = self.current.parent
        else:
            self.current.add_child(node)
            self.current = node

    def is_closed(self):
        return self.current == None

    def get_pretty_string(self):
        lines = []
        self.root.get_pretty_string(lines, 0)
        return '\n'.join(lines)

class GstCapsQueryTreeNode(object):
    def __init__(self, queryline):
        self.children = []
        self.state = 'open'
        self.queryline = queryline
        self.parent = None

    def close(self):
        self.state = 'closed'

    def add_child(self, node):
        self.children.append(node)
        node.parent = self

    def get_pretty_string(self, lines, indent=0):
        structure = self.queryline.get_query_structure()
        x = '%s%s : %s(%s):%s(%s) - filter: %s : res: %s' % (
            ' ' * indent, str(self.queryline.time),
            get_element_name(self.queryline.get_query_origin()),
            str(self.queryline.get_query_origin()),
            get_pad_name(self.queryline.get_query_origin_pad()),
            str(self.queryline.get_query_origin_pad()),
            structure.get_value('filter').to_string(),
            structure.get_value('caps').to_string())
        lines.append(x)
        for c in self.children:
            c.get_pretty_string(lines, indent+4)

def process_file(input_file):

    # Each thread will maintain the current GstCapsQueryTree running in it
    # until it is closed, then it is removed
    threads = {}
    query_trees = []
    elements = {}
    pads = {}

    with open(input_file, 'r') as f:
        for line in f:
            try:
                tracer_line = GstTracerLine(line)
            except GstTracerLineParsingException:
                continue

            if tracer_line.is_new_element():
                elements[tracer_line.structure.get_value('ix')] = \
                    tracer_line.structure.get_value('name')
            elif tracer_line.is_new_pad():
                pads[tracer_line.structure.get_value('ix')] = \
                    tracer_line.structure.get_value('name')
            elif tracer_line.is_query():
                if not tracer_line.is_query_type('caps'): continue

                thread = tracer_line.get_thread()
                if thread in threads:
                    tree = threads[thread]
                    tree.add_node(GstCapsQueryTreeNode(tracer_line))
                    if tree.is_closed():
                        query_trees.append(tree)
                        del threads[thread]
                else:
                    tree = GstCapsQueryTree(GstCapsQueryTreeNode(tracer_line))
                    threads[thread] = tree

    return {'elements' : elements, 'pads' : pads, 'queries' : query_trees}

if __name__ == '__main__':
    Gst.init()

    input_file = sys.argv[1]

    data = process_file (input_file)
    element_names.update(data['elements'])
    pad_names.update(data['pads'])
    queries = data['queries']
    for t in queries:
        print t.get_pretty_string()
        print
