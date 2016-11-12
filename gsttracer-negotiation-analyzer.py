import sys

import gi
gi.require_version('Gst', '1.0')
from gi.repository import GObject, Gst

class GstTracerLineParsingException(Exception): pass

global element_names
element_names = {}

global pad_names
pad_names = {}

# From http://stackoverflow.com/questions/3696430/print-colorful-string-out-to-console-with-python
CODE={
    'ENDC':0,  # RESET COLOR
    'BOLD':1,
    'UNDERLINE':4,
    'BLINK':5,
    'INVERT':7,
    'CONCEALD':8,
    'STRIKE':9,
    'GREY30':90,
    'GREY40':2,
    'GREY65':37,
    'GREY70':97,
    'GREY20_BG':40,
    'GREY33_BG':100,
    'GREY80_BG':47,
    'GREY93_BG':107,
    'DARK_RED':31,
    'RED':91,
    'RED_BG':41,
    'LIGHT_RED_BG':101,
    'DARK_YELLOW':33,
    'YELLOW':93,
    'YELLOW_BG':43,
    'LIGHT_YELLOW_BG':103,
    'DARK_BLUE':34,
    'BLUE':94,
    'BLUE_BG':44,
    'LIGHT_BLUE_BG':104,
    'DARK_MAGENTA':35,
    'PURPLE':95,
    'MAGENTA_BG':45,
    'LIGHT_PURPLE_BG':105,
    'DARK_CYAN':36,
    'AUQA':96,
    'CYAN_BG':46,
    'LIGHT_AUQA_BG':106,
    'DARK_GREEN':32,
    'GREEN':92,
    'GREEN_BG':42,
    'LIGHT_GREEN_BG':102,
    'BLACK':30,
}

def termcode(num):
    return '\033[%sm'%num

def colorstr(astr,color):
    return termcode(CODE[color])+astr+termcode(CODE['ENDC'])

def get_element_name(n):
    if n in element_names:
        return element_names[n]
    else: return '--%s--' % str(n)

def get_pad_name(n):
    if n in pad_names:
        return pad_names[n]
    else: return '--%s--' % str(n)

def element_is_pipeline(line, elements):
    elem = line.get_element_ix()
    if elem in elements and elements[elem]:
        return 'pipeline' in elements[elem] or 'playbin' in elements[elem]
    return False

# Issues list

# An accept-caps has ended up doing a downstream caps query
PERFORMANCE_ACCEPT_CAPS = 'performance/accept-caps'

class GstTracerLine(object):
    def __init__(self, line):
        self.line = line
        tokens = line.split()
        if len(tokens) < 9:
            raise GstTracerLineParsingException, 'Not enough tokens'
        base_index = -1
        for i in range(len(tokens)):
            if 'TRACE' in tokens[i]:
                base_index = i
                break
        if base_index == -1:
            raise GstTracerLineParsingException, 'not a TRACE debug message'
        if 'GST_TRACER' != tokens[base_index + 3]:
            raise GstTracerLineParsingException, 'not a GST_TRACER line'

        self.time = tokens[0]

        #FIXME some structures fail parsing
        self.structure = Gst.Structure.from_string(' '.join(tokens[base_index+5:]))[0]

    def get_thread(self):
        return self.structure.get_value('thread-id')

    def get_element_ix(self):
        return self.structure.get_value('element-ix')

    def is_query(self):
        return self.structure and self.structure.get_name() == 'query'

    def is_new_element(self):
        return self.structure and self.structure.get_name() == 'new-element'

    def is_new_pad(self):
        return self.structure and self.structure.get_name() == 'new-pad'

    def is_message(self):
        return self.structure and self.structure.get_name() == 'message'

    @property
    def ts(self):
        return int(self.structure.get_value('ts'))

    # QUERY RELATED FUNCTIONS
    def is_query_type(self, name):
        return self.structure.get_value('name') == name

    def query_between_elements(self):
        return self.structure.get_value('element-ix') != 4294967295 and \
               self.structure.get_value('peer-element-ix') != 4294967295

    def get_query_origin(self):
        return self.structure.get_value('element-ix')

    def get_query_origin_pad(self):
        return self.structure.get_value('pad-ix')

    def get_query_peer(self):
        return self.structure.get_value('peer-element-ix')

    def get_query_peer_pad(self):
        return self.structure.get_value('peer-pad-ix')

    def get_query_structure(self):
        return self.structure.get_value('structure')

    def is_post_query(self):
        return self.structure.get_value('have-res')

    # END OF QUERY RELATED FUNCTIONS

    # MESSAGE RELATED FUNCTIONS

    def is_message_type(self, name):
        return self.structure.get_value('name') == name

    # END OF MESSAGE_RELATED_FUNCTIONS

    def __str__(self):
        return self.line

class GstCapsQueryTree(object):
    def __init__(self, root):
        self.root = root
        self.current = root

    def add_node(self, node):
        if node.queryline.is_post_query():
#            assert self.current.queryline == node.queryline
            self.current.close(node.queryline)
            self.current = self.current.parent
        else:
            self.current.add_child(node)
            self.current = node

    def is_closed(self):
        return self.current == None

    @property
    def node_count(self):
        return self.root.node_count

    def get_total_time(self):
        return self.root.get_total_time()

    def get_pretty_string(self):
        lines = []
        self.root.get_pretty_string(lines, 0)
        return '\n'.join(lines)

    def traverse(self):
        if self.root:
            return self.root.traverse()
        return []

class GstCapsQueryTreeNode(object):
    def __init__(self, queryline):
        self.children = []
        self.queryline = queryline
        self.res_queryline = None
        self.parent = None
        self.issues = []

    def close(self, queryline):
        self.res_queryline = queryline

    def get_total_time(self):
        return self.res_queryline.ts - self.queryline.ts

    @property
    def node_count(self):
        return 1 + sum([x.node_count for x in self.children])

    def _check_child(self, child):
        # assumes self is parent of child

        # Accept-caps shouldn't lead to downstream/upstream
        # caps queries. It should only check the current element
        if child.queryline.is_query_type('caps'):
            parent_accept = None
            if self.queryline.is_query_type('accept-caps'):
                parent_accept = self
            elif self.parent and self.parent.queryline.is_query_type('accept-caps'):
                parent_accept = self.parent
            if parent_accept and child.queryline.get_element_ix() != parent_accept.queryline.get_element_ix():
                child.issues.append(PERFORMANCE_ACCEPT_CAPS)

    def add_child(self, node):
        self.children.append(node)
        node.parent = self

        self._check_child(node)


    def is_caps_query(self):
        return self.queryline.is_query_type('caps')

    def is_accept_caps_query(self):
        return self.queryline.is_query_type('accept-caps')

    @property
    def query_name(self):
        if self.is_caps_query(): return 'query-caps'
        elif self.is_accept_caps_query(): return 'accept-caps'
        else: return '-'

    def traverse(self):
        yield self
        for c in self.children:
            for c_node in c.traverse():
                yield c_node

    def get_pretty_string(self, lines, indent=0):
        structure = self.queryline.get_query_structure()
        if self.res_queryline:
            res_structure = self.res_queryline.get_query_structure()
        else:
            res_structure = None
        x = '%s%s : %s : %s(%s):%s(%s) ' % (
            ' ' * indent, str(self.queryline.time),
            self.query_name,
            get_element_name(self.queryline.get_query_origin()),
            str(self.queryline.get_query_origin()),
            get_pad_name(self.queryline.get_query_origin_pad()),
            str(self.queryline.get_query_origin_pad()))
        if self.is_caps_query():
            x += '- filter: %s : res: %s' % (
                structure.get_value('filter').to_string(),
                res_structure.get_value('caps').to_string() if res_structure else \
                structure.get_value('caps').to_string())
        else:
            x += '- caps: %s : res: %s' % (
                structure.get_value('caps').to_string(),
                res_structure.get_value('result') if res_structure else '')

        if self.issues:
            x += ' : Issues:%s' % str(self.issues)
            x = colorstr(x,'RED')

        lines.append(x)
        for c in self.children:
            c.get_pretty_string(lines, indent+4)
        if self.res_queryline:
            end = '%s%s' % (' ' * indent, str(self.res_queryline.time))
        else:
            end = '%s-' % (' ' * indent)
        lines.append(end)

class GstCapsQueryPadStats(object):
    class QueryMapKey(object):
        def __init__(self, filtercaps, caps, result):
            self.filtercaps = filtercaps
            self.caps = caps
            self.result = result

        def __hash__(self):
            return hash(0) #TODO always collide

        def __eq__(self, o):
            return self.filtercaps.is_equal(o.filtercaps) and \
                   self.caps.is_equal(o.caps) and \
                   self.result == o.result

    def __init__(self, elem, pad):
        self.elem = elem
        self.pad = pad
        self.queries_map = {} #the key is the filter/result
                              #to know how many time the same caps
                              #query was repeated on this pad

    def add_node(self, node):
        # TODO verify this node belongs to the stats

        # TODO what to do with open queries?
        if not node.res_queryline:
            return

        if not node.is_caps_query():
            return

        structure = node.res_queryline.structure.get_value('structure')
        key = GstCapsQueryPadStats.QueryMapKey(structure.get_value('filter'), \
               structure.get_value('caps'), node.res_queryline.structure.get_value('res'))
        data = self.queries_map.get(key, [])
        data.append(node)
        self.queries_map[key] = data

    def get_pretty_string(self, indent):
        lines = []
        for k,v in self.queries_map.iteritems():
            lines.append(indent * ' ' + 'filter: ' + (k.filtercaps.to_string() if k.filtercaps else '--'))
            lines.append(indent * ' ' + 'caps: ' + k.caps.to_string())
            lines.append(indent * ' ' + 'res: ' + str(k.result))
            lines.append(indent * ' ' + 'Repeated: %d (total time: %dns)' % \
                         (len(v), sum([x.get_total_time() for x in v])))
            lines.append('')
        return '\n'.join(lines)

def gen_element_pad_name(elem,pad):
    return '%s(%s):%s(%s)' % (
            get_element_name(elem), str(elem),
            get_pad_name(pad), str(pad))

def process_file(input_file):

    # Each thread will maintain the current GstCapsQueryTree running in it
    # until it is closed, then it is removed
    threads = {}
    query_trees = []
    elements = {}
    pads = {}
    preroll_time = 0

    with open(input_file, 'r') as f:
        for line in f:
            try:
                tracer_line = GstTracerLine(line)
            except GstTracerLineParsingException, e:
                continue

            if tracer_line.is_new_element():
                elements[tracer_line.structure.get_value('ix')] = \
                    tracer_line.structure.get_value('name')
            elif tracer_line.is_new_pad():
                pads[tracer_line.structure.get_value('ix')] = \
                    tracer_line.structure.get_value('name')
            elif tracer_line.is_query():
                if not (tracer_line.is_query_type('caps') or \
                        tracer_line.is_query_type('accept-caps')): continue

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

            elif tracer_line.is_message():
                if tracer_line.is_message_type('async-done') and element_is_pipeline(tracer_line, elements):
                    preroll_time = tracer_line.ts

    return {'elements' : elements, 'pads' : pads, 'queries' : query_trees,
            'preroll-time' : preroll_time}

def generate_per_pad_caps_query_summary(queries):
    summary = {}
    for q in queries:
       for node in q.traverse():
           elem = node.queryline.get_query_origin()
           pad = node.queryline.get_query_origin_pad()
           if (elem,pad) not in summary:
               summary[(elem,pad)] = GstCapsQueryPadStats(elem,pad)
	   data = summary[(elem,pad)]
           data.add_node(node)
    return summary

if __name__ == '__main__':
    Gst.init()

    input_file = sys.argv[1]

    data = process_file (input_file)
    element_names.update(data['elements'])
    pad_names.update(data['pads'])
    queries = data['queries']

    statistics = generate_per_pad_caps_query_summary (queries)

    for t in queries:
        print t.get_pretty_string()
        print

    print
    print '=== STATS ==='
    for k in statistics.keys():
        print gen_element_pad_name(k[0], k[1])
        print statistics[k].get_pretty_string(4)
        print

    print '=== TOTALS ==='
    print 'Total query trees:', len(queries)
    print 'Total queries:', sum([q.node_count for q in queries])
    print 'Total time: %dns' % sum([q.get_total_time() for q in queries])
    print 'Preroll time: %dns' % data['preroll-time']
