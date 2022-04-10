#!/usr/bin/env python3
import os
import re
import subprocess


class ValidateShortcodes(object):
    """Validate shortcodes used in a given file."""

    def __init__(self, filepath, filetype, logger):
        self.logger = logger
        self.filepath = filepath
        self.filetype = filetype
        self.shortcode_re = re.compile(r'(\{\{% +(?P<sc_name>((\w|:|\-|;|_)+)\s+))')
        self.sc_attr = re.compile(r'(?P<attribute>\w+)="(?P<value>(\w|_|\-|:|;|/|\.)+)"')
        # Translate table for non-ascii chars we might use.
        self.transl_table = dict([(ord(x), ord(y)) for x, y in zip(u"‘’´“”–-", u"'''\"\"--")])
        self.singlepic_attributes = ['image', 'width', 'height', 'alignment', 'caption', 'title', 'has_borders']
        self.singlepic_required_attributes = ['image']
        self.meta_info_attributes = ['info_type']
        self.box_attributes = ['name', 'direction', '*']             # Need to add support for arbitrary attributes
        self.box_required_attributes = ['name']
        self.shortcodes = {'meta_info': (self._generic, self.meta_info_attributes, None),
                           'disposition': (self._generic, None, None),
                           'links': (self._generic, None, None),
                           'gallery': (self._generic, None, None),
                           'singlepic': (self._singlepic, self.singlepic_attributes, self.singlepic_required_attributes),
                           'build_links_to_children': (self._generic, None, None),
                           'box': (self._generic, None, None)}


    def clean_docx(self):
        """Remove smart quotes, long dashes from file."""
        try:
            if self.filetype != 'docx':
                self.logger.make_error_entry(f"File {self.filepath} is not of type docx")
                return
            self.logger.make_info_entry(f"Checking document {self.filepath}")
            ml_filename = os.path.abspath(self.filepath)[:-4] + 'md'
            ml_filename_copy = ml_filename
            command = ["pandoc", f"{self.filepath}", "-o", f"{ml_filename} -t markdown-simple_tables+pipe_tables "]
            try:
                res = subprocess.run(command, check=True)
            except Exception as e:
                self.logger.make_error_entry(f'Error running pandoc with command: {command} and error: {e}')
                return
            file_base = ml_filename.split('.')[0]
            dirpath = '/'.join(file_base.split('/')[:-1])
            dir_files = os.listdir(dirpath)
            for file_nm in dir_files:
                if file_nm.strip().endswith('markdown-simple_tables+pipe_tables'):
                    # This is the file that has been misnamed
                    os.rename(dirpath + '/' + file_nm, ml_filename_copy)
            with open(ml_filename_copy, "r") as fd:
                file_content = fd.readlines()
                fd.close()
            file_content_x = ''.join(file_content).translate(self.transl_table)
            with open(ml_filename_copy, 'w') as fd:
                fd.write(file_content_x)
                fd.close()
            self.filepath = ml_filename_copy
        except Exception as e:
            self.logger.make_error_entry(f"An error: {e.args} occurred processing {self.filepath}")

    def process_shortcodes(self):
        try:
            with open(self.filepath, "r") as fd:
                file_content = fd.readlines()
                fd.close()
            rest_of_file = ''.join(file_content)
            while True:
                next_shortcode = re.search(self.shortcode_re, rest_of_file)
                if next_shortcode:
                    sc_name = next_shortcode.group('sc_name').strip()
                    if sc_name.lower() in self.shortcodes.keys():
                        if sc_name != sc_name.lower():
                            self.logger.make_error_entry(f'Invalid capitalization in shortcode {sc_name}')
                            sc_name = sc_name.lower()
                        start = next_shortcode.start('sc_name')
                        end = rest_of_file[start:].find(r'%}}')
                        if end == -1:
                            self.logger.make_error_entry(f'Shortcode {sc_name} has not been terminated (no "%}}"')
                            rest_of_file = rest_of_file[start + 3:]
                        else:
                            sc_text = rest_of_file[start:start + end].strip()
                            rest_of_file = rest_of_file[start + end:]
                            if sc_text:
                                processor, attrs_valid, attrs_required = self.shortcodes[sc_name]
                                if processor != self._xx:
                                    processor(sc_name, sc_text, attrs_valid, attrs_required)

                    else:
                        self.logger.make_error_entry(f'Shortcode {sc_name} is not a recognized shortcode.')

                else:
                    break
        except FileNotFoundError as e:
            self.logger.make_error_entry(f'File {self.filepath} not found - does the actual filename contain spaces? ')
        except Exception as e:
            self.logger.make_error_entry(f'Error: {e.args}')

    def _make_attribute_dictionary(self, sc_text):
        """Create dictionary of attributes/values for shortcode. """
        attr_dict = dict()
        while True:
            next_attr = re.search(self.sc_attr, sc_text)
            if not next_attr:
                break
            else:
                attr_dict[next_attr.group('attribute')] = next_attr.group('value')
                sc_text = sc_text[next_attr.end('value'):]
        return attr_dict

    def _verify_attribute_names(self, attr_dict, valid_attributes, required_attributes, sc_name):
        """Verify that attributes exist and are spelled correctly."""
        if not valid_attributes:
            return
        if '*' not in valid_attributes:
            for key in attr_dict.keys():
                if key.lower() not in valid_attributes:
                    self.logger.make_error_entry(f"Unrecognized attribute {key} in {sc_name}.")
                elif key not in valid_attributes:
                    self.logger.make_error_entry(f"Improper capitalization for attribute {key} in {sc_name}.")
        else:
            # Check capitalization on any that happen to be in valid_attributes as any other must be assumed valid
            for key in attr_dict.keys():
                if key.lower() in valid_attributes and key not in valid_attributes:
                    self.logger.make_error_entry(f"Improper capitalization for attribute {key} in {sc_name}.")
        if required_attributes:
            for attr_name in required_attributes:
                if attr_name not in attr_dict.keys():
                    self.logger.make_error_entry(f"Required attribute {attr_name} not found in shortcode {sc_name}")

    def _singlepic(self, sc_name, sc_text, attrs_valid, attrs_required):
        try:
            attr_dict = self._make_attribute_dictionary(sc_text)
            self._verify_attribute_names(attr_dict, attrs_valid, attrs_required, sc_name)

            for key in attr_dict.keys():
                attr_val = attr_dict[key]
                if key == 'image':
                    if not attr_val.startswith('/images') or attr_val.split('.')[-1] not in ['jpg', 'jpeg', 'tif']:
                        self.logger.make_error_entry(f"Image path: {attr_val} appears to be invalid.")
                elif key == 'alignment':
                    if attr_val and attr_val not in ['right', 'center', 'left', 'float-left', 'float-right']:
                        self.logger.make_error_entry(f"Invalid alignment value {attr_val} in {sc_name}.")
            for required_attr in attrs_required:
                if required_attr not in attr_dict.keys():
                    self.logger.make_error_entry(f"Missing required attribute {required_attr} in {sc_name}.")
        except Exception as e:
            self.logger.make_error_entry(f"Encountered exception {e.args} when validating singlepic.")

    def _xx(self):
        pass

    def _generic(self, sc_name, sc_text, attrs_valid, attrs_required):
        try:
            attr_dict = self._make_attribute_dictionary(sc_text)
            self._verify_attribute_names(attr_dict, attrs_valid, attrs_required, sc_name)
        except Exception as e:
            self.logger.make_error_entry(f"Encountered exception {e.args} when validating {sc_name}.")


    def _xx(self):
        pass

    def _xx(self):
        pass
