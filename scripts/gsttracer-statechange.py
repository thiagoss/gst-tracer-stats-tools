import sys

class ElementStateChange(object):
    def __init__(self, initial_state, final_state, transition_start_ts, transition_end_ts):
        self.initial_state = initial_state
        self.final_state = final_state
        self.transition_start_ts = transition_start_ts
        self.transition_end_ts = transition_end_ts

    def __str__(self):
        return '%s -> %s : %d' % (self.initial_state, self.final_state, (self.transition_end_ts - self.transition_start_ts))


class ElementStateChangeTiming(object):
    def __init__(self, ptr, element, ts):
        self.ptr = ptr
        self.element = element
        self.ts = ts
        self.state = 'null'
        self.pending_state = None
        self.transition_start = None
        self.transitions = []

    def start_state_change(self, ts, initial_state, final_state):
        assert self.state == initial_state, '%s: %s != %s' % (self.element, self.state, initial_state)
        assert self.pending_state == None
        self.pending_state = final_state
        self.transition_start = ts

    def finish_state_change(self, ts, initial_state, final_state, result):
        if result != 'failure':
            assert final_state == self.pending_state
            self.state = final_state
            self.transitions.append(ElementStateChange (initial_state, final_state, self.transition_start, ts))
            self.pending_state = None
            self.transition_start = None


old_elements = []
elements = {}

def parse_entry(entry):
    tokens = entry.split('$')
    timestamp = int(tokens[0])
    event = tokens[1]
    ptr = tokens[2]
    element = tokens[3][1:-1] #remove < > around element name

    return timestamp, event, ptr, element, tokens[4:]

def process_file(input_file):

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
            elif event == 'element-state-change-pre':
                elements[ptr].start_state_change(ts, data[0], data[1])
            elif event == 'element-state-change-post':
                elements[ptr].finish_state_change(ts, data[0], data[1], data[2])

    for e in old_elements + elements.values():
        print e.element
        print '  Created at: %d' % e.ts
        for t in e.transitions:
            print '  Transition: %s' % str(t)

if __name__ == '__main__':
    input_file = sys.argv[1]

    data = process_file (input_file)
