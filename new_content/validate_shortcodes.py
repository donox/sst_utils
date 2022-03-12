import sys
import os
import re


class ValidateShortcodes(object):
    """Validate shortcodes used in a given file."""

    def __init__(self, filepath, filetype):
        self.filepath = filepath
        self.filetype = filetype
        self.shortc__re = re.compile(r'(\{\{% +(?P<sc_name>((\w|:|\-|;|_)+)\s+))')
        self.sc_attr = re.compile(r'(?P<attribute>\w+)="(?P<value>(\w|_|\-|:|;)+)"')
        # Translate table for non-ascii chars we might use.
        self.transl_table = dict([(ord(x), ord(y)) for x, y in zip(u"‘’´“”–-", u"'''\"\"--")])
        self.shortcodes = {'meta_info': self._xx,
                           'disposition': self._xx,
                           'links': self._xx,
                           'gallery': self._xx,
                           'singlepic': self._xx,
                           'build_links_to_children': self._xx,
                           'box': self._xx}

    def clean_docx(self):
        """Remove smart quotes, long dashes from file."""
        try:
            with open(self.filepath, "r") as fd:
                file_content = fd.readlines()
                fd.close()
            file_content = ''.join(file_content).translate(self.transl_table)
            # remove non-ascii chars (some) from doc
            with open(self.filepath, "w") as fd:
                fd.write()
                fd.close()
        except Exception as e:
            foo = 3
            pass

    def process_shortcodes(self):
        try:
            with open(self.filepath, "r") as fd:
                file_content = fd.readlines()
                fd.close()
            rest_of_file = ''.join(file_content)
            while True:
                next_shortcode = re.search(self.shortc__re, rest_of_file)
                if next_shortcode:
                    sc_name = next_shortcode.group('sc_name')
                    if sc_name.lower() in self.shortcodes:
                        if sc_name != sc_name.lower():
                            print(f'Invalid capitalization in shortcode {sc_name}')
                            sc_name = sc_name.lower()
                            start = next_shortcode.start('sc_name')
                            end = rest_of_file.find(r'%}}')
                            if end == -1:
                                print(f'Shortcode {sc_name} has not been terminated (no "%}}"')
                                rest_of_file = rest_of_file[start + 3:]
                            else:
                                sc_text = rest_of_file[start, end].strip()
                                rest_of_file = rest_of_file[end:]
                                if sc_text:
                                    processor = self.shortcodes[sc_name]
                                    processor(sc_text)

                    else:
                        print(f'Shortcode {sc_name} is not a recognized shortcode.')

                else:
                    break
        except Exception as e:
            foo = 3

    def _singlepic(self, sc_text):
        while True:
            next_attr = re.search(self.sc_attr, sc_text)
            if not next_attr:
                return


    def _xx(self):
        pass

    def _xx(self):
        pass

    def _xx(self):
        pass

    def _xx(self):
        pass
