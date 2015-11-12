import sys

class ElementStateChange(object):
    VALUES = {'null' : 1, 'ready' : 2, 'ready-async': 3, 'paused' : 4, 'playing' : 5}

    def __init__(self, initial_state, final_state, transition_start_ts, transition_end_ts):
        self.initial_state = initial_state
        self.final_state = final_state
        self.transition_start_ts = transition_start_ts
        self.transition_end_ts = transition_end_ts

    def __str__(self):
        return '%s -> %s : %d' % (self.initial_state, self.final_state, self.duration)

    def get_transition_name(self):
        return self.initial_state + ' -> ' + self.final_state

    def is_upwards(self):
        return ElementStateChange.VALUES[self.final_state] > ElementStateChange.VALUES[self.initial_state]

    @property
    def duration(self):
        return self.transition_end_ts - self.transition_start_ts


class ElementStateChangeTiming(object):
    def __init__(self, ptr, element, ts):
        self.ptr = ptr
        self.element = element
        self.ts = ts
        self.state = 'null'
        self.pending_state = None
        self.async_pending = False
        self.transition_start = None
        self.transitions = []
        self.parent = None
        self.children = []

    def start_state_change(self, ts, initial_state, final_state):
        assert self.state == initial_state or (self.async_pending and self.pending_state == initial_state), '%s: %s/%s != %s' % (self.element, self.state, self.pending_state, initial_state)
        assert self.pending_state == None or (self.async_pending and self.pending_state == initial_state)
        if self.async_pending:
            self.async_done(ts)
        self.pending_state = final_state
        self.transition_start = ts

    def finish_state_change(self, ts, initial_state, final_state, result):
        if result != 'failure':
            assert final_state == self.pending_state
            if result == 'async':
                self.state = initial_state + '-async'
                self.transitions.append(ElementStateChange (initial_state, self.state, self.transition_start, ts))
                self.transition_start = ts
                self.async_pending = True
            else:
                self.state = final_state
                self.transitions.append(ElementStateChange (initial_state, final_state, self.transition_start, ts))
                self.pending_state = None
                self.transition_start = None

    def async_done(self, ts):
        if self.async_pending:
            self.async_pending = False
            self.finish_state_change(ts, self.state, self.pending_state, 'success')

    def add_child(self, ptr, element):
        self.children.append((ptr, element))

    def set_parent(self, ptr, element):
        assert self.parent == None
        self.parent = (ptr, element)

def parse_entry(entry):
    tokens = entry.split('$')
    timestamp = int(tokens[0])
    event = tokens[1]
    ptr = tokens[2]
    element = tokens[3][1:-1] #remove < > around element name

    return timestamp, event, ptr, element, tokens[4:]

def process_file(input_file):
    old_elements = []
    elements = {}

    pending_parent_relations = []

    def set_parent(parent_ptr, child_ptr, child_name):
        child_name = child_name[1:-1]
        elements[parent_ptr].add_child(child_ptr, child_name)
        # We can't trust the bin's element name (it is uppercase and has the memaddress
        elements[child_ptr].set_parent(parent_ptr, elements[parent_ptr].element)

    with open(input_file, 'r') as f:
        for line in f:
            # Get the last token
            entry = line.split(' ')[-1].strip()

            try:
                ts, event, ptr, element, data = parse_entry(entry)
            except:
                #TODO use a proper exception
                continue

            if event == 'element-new':
                data = ElementStateChangeTiming(ptr, element, ts)
                if ptr in elements:
                    old_elements.append(elements[ptr])
                elements[ptr] = data

                #handle the pending parents (reversed will create a copy)
                for pp in reversed(pending_parent_relations):
                    if pp[2] in elements:
                        pending_parent_relations.remove(pp)
                        set_parent(pp[2], pp[4][0], pp[4][1]) #FIXME this is ugly


            elif event == 'element-state-change-pre':
                elements[ptr].start_state_change(ts, data[0], data[1])
            elif event == 'element-state-change-post':
                elements[ptr].finish_state_change(ts, data[0], data[1], data[2])
            elif event == 'element-async-done':
                elements[ptr].async_done(ts)
            elif event == 'bin-add-post':
                # Some elements will add their children in the _init() so the element-new hook
                # will be called after the bin-add
                if ptr not in elements:
                    pending_parent_relations.append((ts,event, ptr, element, data))
                else:
                    set_parent(ptr, data[0], data[1])

    return sorted(old_elements + elements.values(), key=lambda x: x.ts)

def output_html_timeline_chart(elements):
    def find_element(ptr):
        for e in elements:
            if e.ptr == ptr:
                return e
        return None

    def generate_elements_menu(element_list):
        menu = '<ul>\n'
        for e in element_list:
            menu += '<li>\n'
            menu += '<a href="#" onclick="drawChart(\'%s:%s\')">%s:%s</a>' % (e[0], e[1], e[0], e[1])
            element = find_element(e[0])
            if element and element.children:
                menu += generate_elements_menu(element.children)
            menu += '</li>\n'
        menu += '</ul>\n'
        return menu

    maxtime = max([x.ts for x in elements])
    for e in elements:
        if e.transitions:
            maxtime = max(maxtime, max([x.transition_end_ts for x in [t for t in e.transitions]]))

    html = """
<html>
  <head>
    <script type="text/javascript" src="https://www.google.com/jsapi"></script>
    <script type="text/javascript">
      google.load("visualization", "1.1", {packages:["timeline"]});

      var data = {
%(data)s
      };

      function addTransitions(dataTable, element) {
          for (var i = 0; i < element['transitions'].length; i++) {
              var t = element['transitions'][i];
              dataTable.addRow([element['name'], t['transition'], t['transition'] + ' ' + (t['end'] - t['start']), t['start'], t['end']])
          }
      }

      function drawChart(element) {
        var container = document.getElementById('timeline-tooltip');
        var chart = new google.visualization.Timeline(container);
        var dataTable = new google.visualization.DataTable();

        dataTable.addColumn({ type: 'string', id: 'Element' });
        dataTable.addColumn({ type: 'string', id: 'dummy bar label' });
        dataTable.addColumn({ type: 'string', role: 'tooltip' });
        dataTable.addColumn({ type: 'number', id: 'Start' });
        dataTable.addColumn({ type: 'number', id: 'End' });

        if(element === undefined) {
          return;
        }

        var e = data[element];
        addTransitions(dataTable, e);
        for (var i = 0; i < e['children'].length; i++) {
            var c = data[e['children'][i]];
            addTransitions(dataTable, c);
        }

        chart.draw(dataTable);
      }

    </script>
  </head>
  <body>
    <div id="left-panel" style="float: left;">
      <h2>Elements</h2>
      <div id="menu">
%(menu)s
      </div>
    </div>
    <div id="timeline-tooltip" style="height: 1080px; width: 1200px; float: right;"></div>
  </body>
</html>
    """
    data = []
    toplevel = []
    for e in elements:
        if e.parent is None:
            toplevel.append((e.ptr, e.element))
        data.append("'%s:%s' : {'name' : '%s', 'children' : [%s], 'transitions' : [%s]}" \
                            % (e.ptr, e.element, e.element,
                            ','.join(["'"+x[0]+':'+x[1]+"'" for x in e.children]),
                            ','.join(["{'transition': '%s', 'start' : %d, 'end' : %d}" % \
                                     (t.get_transition_name(), t.transition_start_ts, t.transition_end_ts) \
                                     for t in e.transitions if t.is_upwards()])))

    menu = generate_elements_menu (toplevel)

    return html % {'data': ',\n'.join(data),
                   'menu' : menu}

if __name__ == '__main__':
    input_file = sys.argv[1]

    data = process_file (input_file)

    output_mode = 'timeline'
    if output_mode == 'timeline':
        print output_html_timeline_chart(data)
    else:
        for e in sorted(old_elements + elements.values(), key=lambda x: x.ts):
            print e.element
            print '  Created at: %d' % e.ts
            for t in e.transitions:
                print '  Transition: %s' % str(t)
