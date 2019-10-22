import re


class Minutes(object):
    '''Parse a Word doc formatted by 'Minutes' grammar to build context for web template.'''
    def __init__(self, reader, grammar, init_state, init_map):
        self.reader = self._minutes_reader(reader)()
        self.tracer = None
        self.last_match = None  # contains results of last successful re match
        self.last_token = None  # contains the token actually matched
        self.current_state = init_state
        self.fsm_map = init_map
        self.group_current_level = 0
        self.grammar = grammar
        self.current_read_string = ''
        self.has_rule = re.compile(r'^\s*[ A-Za-z]+:')
        self.has_top_rule = re.compile(r'^[ A-Za-z]+:')
        self.context = dict()
        self.input_doc = []
        self.starting_lines = []
        self.components = []

    def _minutes_reader(self, file_reader):
        '''Wrap file reader to allow a line to be broken into multiple parts if needed.'''
        def local():
            for tmp in file_reader():
                self.current_read_string = tmp
                while self.current_read_string:
                    yield self.current_read_string
                    self.current_read_string = ''
        return local

    def run(self):
        self.process_whole_doc()
        self.create_context()
        return self.context

    def create_context(self):
        '''Convert derived components to context for template.'''
        for element in self.components:
            jinja_name, element_kind, element_type, content, subcontent = element
            if element_type == 'Centered':
                self.context[jinja_name] = (element_kind, content)
            elif element_type == 'Multiline':
                self.context[jinja_name] = (element_kind, content)
            elif element_type == 'Sublevel':
                self.context[jinja_name] = (element_kind, content)
            else:
                res = dict()
                for el in element[3]:
                    res[el[0]] = el[3]                                          # VERIFY THIS _ not there now
                self.context[jinja_name] = res

    def process_whole_doc(self):
        # Import document - all work occurs in memory
        for doc_line in self.reader:
            self.input_doc.append(doc_line.rstrip())

        # Find starting point of each entry in the grammar (that exists)
        for rule in self.grammar:           # Find line initiating each of the document elements
            for ndx, doc_line in enumerate(self.input_doc):
                res = re.match(rule[0], doc_line)
                if res:
                    self.starting_lines.append((res[1], rule, ndx))
                    break
        self.starting_lines.append(('DOCEND', None, len(self.input_doc) + 1))
        self.starting_lines.sort(key=lambda x: x[2])

        # Process each item group building components suitable for constructing template context
        try:
            for pos, val in enumerate(self.starting_lines):
                heading, rule, ndx = val
                if heading == 'DOCEND':
                    break
                res = re.match(rule[0], self.input_doc[ndx])
                self.input_doc[ndx] = res[2]            # Remove heading from first line
                if rule[1]:                             # Has second level of Headings
                    local_positions = self.process_level_two(rule, ndx, self.starting_lines[pos + 1][2])
                    local_substructure = []

                    if rule[3] == 'NameTitle':
                        stuff = self.process_level_two(rule, ndx, self.starting_lines[pos + 1][2])
                        local_substructure.append((heading, rule[3], stuff))
                    elif rule[3] == 'Multiline':
                        stuff = self.process_multi_line_collection(rule, ndx, self.starting_lines[pos + 1][2])
                        local_substructure.append((heading, rule[3], stuff))
                    else:
                        stuff = self.process_single_line_collection(rule, ndx, self.starting_lines[pos + 1][2])
                        local_substructure.append((heading, rule[3], stuff))
                        print('SET Else Clause')                                #  DEBUG _ SHOULD NOT GET HERE
                        for x in [y[2] for y in self.starting_lines[0:-1]]:
                            print(self.input_doc[x][0:30])
                    self.components.append((heading.replace(' ', ''), heading, 'Sublevel', local_positions, local_substructure))
                else:
                    stuff = self.process_single_line_collection(rule, ndx, self.starting_lines[pos + 1][2])
                    self.components.append((heading.replace(' ', ''), heading, rule[3], stuff, None))
        except Exception as e:
            raise e
        return

    def process_level_two(self, outer_rule, start, end):
        l2_starting_lines = []
        for rule in outer_rule[1]:           # Find line initiating each of the document elements
            for ndx, doc_line in enumerate(self.input_doc[start:end]):
                res = re.match(rule[0], doc_line)
                if res:
                    header = res[1].strip()
                    self.input_doc[ndx+start] = res[2].strip()                # Is this right?????????
                    l2_starting_lines.append((header, rule, ndx))
                    break
        l2_starting_lines.sort(key=lambda x: x[2])
        if l2_starting_lines:
            l2_starting_lines.append(('SECEND', None, l2_starting_lines[-1][2] + 1))
        else:
            l2_starting_lines.append(('SECEND', None, None))
        this_content = []
        for ndx, item in enumerate(l2_starting_lines):
            header, rule, loc = item
            if header != 'SECEND':
                if 'Christmas' in header:
                    foo = 3
                loc_start = loc + start
                loc_end = l2_starting_lines[ndx+1][2] + start
                res = self.process_single_line_collection(rule, loc_start, loc_end)
                this_content.append((header, res))
        return this_content

    def process_single_line_collection(self, outer_rule, start, end):
        this_content = []
        for doc_line in self.input_doc[start:end]:
            this_content.append(doc_line.strip())
        return this_content

    def process_multi_line_collection(self, outer_rule, start, end):
        this_content = []
        this_entry = ''
        for doc_line in self.input_doc[start:end]:
            doc_line = doc_line.strip()
            if doc_line:
                this_entry += doc_line + ' '
            else:
                if this_entry:
                    this_content.append(this_entry)
                    this_entry = ''
        if this_entry:
            this_content.append(this_entry)
        return this_content

