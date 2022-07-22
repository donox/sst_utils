#!/usr/bin/env python3
import os
import shutil
import yaml
from system_control.manage_google_drive import ManageGoogleDrive as mgd
import tempfile as tf
import pathlib as pl
from mako.template import Template
from new_content import validate_shortcodes as vs
from mako.lookup import TemplateLookup
from mako.runtime import Context
from config_private import test_run
from system_control.exceptions import SstCommandDefinitionException as CDEx


class ProcessStoryContent(object):
    def __init__(self, logger, folder_path, temp_directory, docx_directory, sst_directory,
                 image_directory, gallery_directory):
        self.logger = logger
        self.first_photo = True  # switch to detect processing of first photo
        self.drive = mgd()
        self.folder_path = mgd.add_slash(folder_path)
        self.galleries = self.drive.directory_list_directories(self.logger, self.folder_path)
        self.filenames = self.drive.directory_list_files(self.logger, self.folder_path)
        self.temp_directory = temp_directory
        self.story_directory = tf.TemporaryDirectory(prefix='story', dir=temp_directory)
        self.docx_directory = docx_directory
        self.sst_directory = sst_directory
        self.image_directory = image_directory
        self.gallery_directory = gallery_directory
        self.template_processors = {'resident_clubs': self.resident_clubs_template}
        self.pages_directory = pl.Path(self.sst_directory) / 'pages/'
        # Note, downloading to max-depth=2 downloads contents of any galleries.
        self.drive.download_directory(self.logger, self.folder_path, mgd.add_slash(self.story_directory.name),
                                      max_depth=2)

    def process_content(self):
        if "meta.txt" in self.filenames:
            has_meta = True
            with open(pl.Path(self.story_directory.name) / 'meta.txt') as stream:
                try:
                    story_meta_tmp = yaml.safe_load(stream.read().replace('\t', ' '))
                    story_meta = dict()
                    for key in story_meta_tmp:  # the meta data_file may have leading periods on the attributes, remove them
                        ky = key
                        if ky.startswith(".."):
                            ky = ky[2:].strip()
                        story_meta[ky] = story_meta_tmp[key]
                    stream.close()
                except yaml.YAMLError as exc:
                    self.logger.make_error_entry(f"YAML error encountered in {self.folder_path} with error {exc.args}")
                    raise exc
        else:
            has_meta = False

        for file in self.filenames:
            file_parts = file.split(".")
            ext = file_parts[-1].lower()
            if ext == 'docx':
                if not has_meta:
                    self.logger.make_error_entry(f"Folder: {self.folder_path} has no data_file meta.txt")
                    raise CDEx(f"Folder: {self.folder_path} has no data_file meta.txt")
                self.process_docx(story_meta, file)
            elif ext == 'jpg' or ext == 'jpeg':
                # if not has_photos:
                #     self.logger.make_error_entry(f"Photo {data_file} found in folder  without having a photos.txt")
                #     raise ValueError("Photos without photos.txt")
                try:
                    if 'photo_path' not in story_meta.keys():
                        self.logger.make_error_entry(f"There is no photo_path in meta.txt")
                        raise CDEx(f"Missing photo_path")
                    self.process_photo(story_meta['photo_path'], file)
                except Exception as exc:
                    self.logger.make_error_entry(f"Error in processing photo: {exc.args}")
                    raise exc
            elif ext == 'txt':
                if file == 'meta.txt' or file == 'photos.txt' or file == 'commands.txt':
                    pass
                elif 'template_mako' in story_meta.keys():
                    template = story_meta['template_mako']
                    if "file" not in story_meta or file != story_meta["file"]:
                        self.logger.make_error_entry(f"Unrecognized text data_file {file} in {self.folder_path}")
                        raise CDEx(f"Unrecognized text data_file {file} in {self.folder_path}")
                    self.process_template(story_meta, file)
                else:
                    self.logger.make_error_entry(f"Unrecognized text data_file {file} in {self.folder_path}")
                    raise CDEx(f"Unrecognized text data_file {file} in {self.folder_path}")
            elif ext == 'md':
                # Markdown files are copied without further evaluation just as is done in the command transfer files
                out_dir = pl.Path(self.sst_directory + story_meta['path'] + '/')
                out_file = self.story_directory.name + '/' + file
                try:
                    if not test_run:
                        os.makedirs(out_dir, exist_ok=True)
                        shutil.copy(out_file, out_dir)
                except NameError:
                    pass
                self._copy_meta_file(story_meta, out_dir=out_dir)
            else:
                self.logger.make_error_entry(f"Unrecognized data_file type {ext} in {self.folder_path}")
                raise CDEx(f"Unrecognized data_file type {ext} in {self.folder_path}")
        for dirname in self.galleries:
            # A directory represents a gallery and cannot be nested.
            self.process_gallery(pl.Path(self.story_directory.name) / dirname)

    def process_docx(self, story_meta, file):
        # copy docx data_file ensuring data_file corresponds to slug
        source = pl.Path(self.story_directory.name) / file
        val_sc = vs.ValidateShortcodes(source, 'docx', self.logger)
        val_sc.clean_docx()  # Already duplicated in nikola command
        val_sc.process_shortcodes()
        target = self.docx_directory + story_meta['slug'] + ".docx"
        try:
            if not test_run:
                if os.path.exists(target):
                    os.remove(target)
                shutil.copy(source, target)
        except NameError:
            pass
        if not test_run:
            self._copy_meta_file(story_meta)

    def _copy_meta_file(self, story_meta, out_dir=None):
        if not out_dir:
            out_dir = pl.Path(self.docx_directory)
        # Copy meta data_file with proper renaming
        source = pl.Path(self.story_directory.name) / 'meta.txt'
        target = out_dir / (story_meta['slug'] + ".meta")
        try:
            if not test_run:
                if os.path.exists(target):
                    os.remove(target)
                shutil.copy(source, target)
        except NameError:
            pass

    def process_photo(self, path, file):
        ndx = 0
        if path[0] == '/':
            ndx = 1
        image_path = self.sst_directory + path[ndx:]
        source = pl.Path(self.story_directory.name) / file
        try:
            if not test_run:
                os.makedirs(image_path, exist_ok=True)
                shutil.copy(source, image_path)
        except NameError:
            pass

    def process_pdf(self, path, file):
        ndx = 0
        if path[0] == '/':
            ndx = 1
        pdf_path = self.sst_directory + path[ndx:]
        source = pl.Path(self.story_directory.name) / file
        try:
            if not test_run:
                os.makedirs(pdf_path, exist_ok=True)
                shutil.copy(source, pdf_path)
        except NameError:
            pass

    def process_gallery(self, path_to_gallery):
        if os.path.exists(path_to_gallery):  # can be empty if there was an ignore folder
            photo_files = os.listdir(path_to_gallery)
            resolved_gallery_path = pl.Path(path_to_gallery)
            if 'metadata.yml' in photo_files:
                with open(resolved_gallery_path / 'metadata.yml') as stream:
                    try:
                        # Note: yaml is small and we convert to list so it can be reused
                        gallery_meta = [x for x in yaml.safe_load_all(stream)]
                    except yaml.YAMLError as exc:
                        self.logger.make_error_entry(
                            f"YAML error encountered in {path_to_gallery} with error {exc.args}")
                        raise CDEx(f"YAML Error: {exc.args}")
                    # First - locate gallery path and gallery name
                    gallery_path = None
                    for doc in gallery_meta:
                        if doc:
                            keys = [key.lower() for key in doc.keys()]
                            vals = list(doc.values())
                            if 'gallery path' in keys:
                                gallery_path = vals[keys.index('gallery path')]
                    if not gallery_path:
                        self.logger.make_error_entry(f"Missing gallery path.  Gallery meta: {gallery_meta}")
                        raise CDEx(f"Missing gallery path")
                    gal_path = self.sst_directory + gallery_path[1:]
                    try:
                        if not test_run:
                            create_empty_dirpath(gal_path)
                            shutil.copy(resolved_gallery_path / 'metadata.yml', gal_path)
                            if not gal_path.endswith('/'):
                                gal_path += '/'
                            for doc in gallery_meta:
                                if doc:
                                    shutil.copy(resolved_gallery_path / doc['name'], gal_path + doc['name'])
                    except NameError:
                        pass
                    except Exception as e:
                        foo = 3
            else:
                self.logger.make_error_entry(f"No metadata.yml data_file in {path_to_gallery}")
                raise CDEx(f"No metadata.yml data_file in {path_to_gallery}")

    def process_template(self, story_meta, data_file):
        """
        Take a meta_file and a data_file and build a page with a mako template.

        This is a high level processor that can manages the process with data in the story_meta file.  If
        there is no need for deeper processing outside the template, the template may be called with the
        data_file as the context.  In cases where it is useful to create a richer context for the template,
        the story_meta file can contain the name of a routine to build the context.  Any such routine is
        found in the template_processors dictionary in the object.

        The first yaml dictionary in the data_file is considered the "head" and is passed to the template
        as context "head".  For normal templates (those not specifically identified), the remainder of the
        data_file (list of yaml dictionaries) are passed in the context as "body"

        :param story_meta: A standard nikola meta_file possibly with template identification information.
        :param data_file:  A YAML file containing the data for the template.
        :return: None - the created page is saved at the path / slug in the story_meta file.
        """

        self.logger.make_info_entry(f"Start processing template on data_file: {data_file}")
        template_name = story_meta['template_mako']
        file_path = pl.Path(self.story_directory.name) / data_file
        with open(file_path) as stream:
            try:
                story_content = yaml.safe_load_all(stream)
                story_content = [x for x in story_content]
                stream.close()
            except yaml.YAMLError as exc:
                self.logger.make_error_entry(f"YAML error encountered in {self.folder_path} with error {exc.args}")
                raise CDEx(f"YAML error {exc.args}")
        if not template_name.endswith('.mako'):      # Defend against forgetting the extension
            filename = 'new_content/templates/' + template_name + '.mako'
        else:
            filename = 'new_content/templates/' + template_name
        template = Template(filename=filename)
        context = dict()
        context["head"] = story_content[0]
        context["body"] = []
        context['has_clubs'] = False
        on_campus_list = []
        context['has_on_campus'] = False
        off_campus_list = []
        context['has_off_campus'] = False
        if 'template_processor' in story_meta.keys():
            template_processor = story_meta['template_processor']
            if template_processor not in self.template_processors.keys():
                self.logger.make_error_entry(f"meta.txt file contains unrecognized template processor{template_processor}")
                raise CDEx(f"Invalid template processor: {template_processor}")
            self.template_processors[template_processor](story_meta, story_content, context, on_campus_list, off_campus_list)
        else:
            # Process case with no special context building routine
            for el in story_content[1:]:
                if el and 'type' in el.keys():   # the 'type' check ensures we are looking at a club style entry
                    if 'photo_path' in story_meta.keys() and 'picture' in el.keys():  # support pictures - such as in Sunnybear
                        el['picture'] = story_meta['photo_path'] + el['picture']
                    try:
                        if el['type'] == 'on campus':
                            on_campus_list.append(el)
                            context['has_on_campus'] = True
                        elif el['type'] == 'off campus':
                            off_campus_list.append(el)
                            context['has_off_campus'] = True
                    except Exception as e:
                        foo = 3
                        context['has_off_campus'] = True
                else:
                    context['body'].append(el)
            context['on_campus'] = on_campus_list
            context['off_campus'] = off_campus_list
        try:
            results = template.render(**context)
        except KeyError as e:
            self.logger.make_error_entry(f"Render failed with KeyError: {e.args}")
            raise CDEx(f"Render Failure on file: {file_path}")
        except Exception as e:
            foo = 3
            raise e
        results = results.replace('\n\n', '\n')  # somehow, md ignores html following two blank lines.
        out_dir = pl.Path(self.sst_directory + story_meta['path'] + '/')
        try:
            if not test_run:
                os.makedirs(out_dir, exist_ok=True)
                with open(out_dir / (story_meta['slug'] + '.md'), 'w') as outfile:
                    outfile.write(results)
                    outfile.close()
        except NameError:
            pass

        self._copy_meta_file(story_meta, out_dir=out_dir)

    def resident_clubs_template(self, story_meta, story_content, context, on_campus_list, off_campus_list):
        # story_content is loaded yaml file
        # There are two cases to handle:
        #    -- no buttons needed
        #    -- buttons needed to select subset of entries to display
        # This restructures the context into groups so that the template
        # can place button list (including empty) and generate button info without
        # having to scan/sort all entries.  Entries are themselves grouped by button group
        errors_found= False
        head_list = []
        button_list = []
        context['has_buttons'] = False
        button_names = []
        club_dict = dict()
        club_caption = dict()
        required_keys = set(['group', 'updated', 'type', 'phone', 'schedule', 'location', 'URL'])
        required_key_count = len(required_keys)
        for entry in story_content:
            if not entry:
                pass
            else:
                entry_keys = set(entry.keys())
                if 'title' in entry_keys:
                    head_list.append(entry)
                elif 'button' in entry_keys:
                    if 'photo_path' in story_meta.keys() and 'picture' in entry.keys():  # support pictures - such as in Sunnybear
                        entry['picture'] = story_meta['photo_path'] + entry['picture']
                    button_list.append(entry)
                    if 'group' not in entry_keys:
                        self.logger.make_error_entry(f"Button specified with no assigned group: {entry}")
                        raise CDEx(f"Button specified with no assigned group: {entry}")
                    else:
                        button_names.append(entry['group'])
                elif 'type' in entry_keys:
                    et = entry['type']
                    if et == 'club':
                        if 'group' not in entry_keys:
                            self.logger.make_error_entry(f"No group specified for club type entry: {entry}")
                            errors_found = True
                        else:
                            if len(required_keys.intersection(entry_keys)) != required_key_count:
                                self.logger.make_error_entry(f"missing required key in {entry}")
                                errors_found = True
                            grp = entry['group']
                            if grp not in button_names:
                                err_string = f"Club group not in list of available buttons: {grp}"
                                self.logger.make_error_entry(err_string)
                                errors_found = True
                            elif grp not in club_dict.keys():
                                club_dict[grp] = [entry]
                                for btn in button_list:
                                    if btn['group'] == grp:
                                        club_caption[grp] = btn['caption']
                                        break
                            else:
                                club_dict[grp].append(entry)
                elif et == 'off-campus':
                    off_campus_list.append(entry)
                elif et == 'on-campus':
                    on_campus_list.append(entry)
                else:
                    self.logger.make_error_entry(f"Unrecognized resident clubs data entry: {entry}")
                    errors_found = True
        if len(head_list) != 1:
            self.logger.make_error_entry(f"Data has {len(head_list)} head entries.  One expected.")
            errors_found = True
        else:
            context['head'] = head_list[0]
        context['buttons'] = button_list
        if button_list:
            context['has_buttons'] = True
        context['clubs'] = club_dict
        if club_dict.keys():
            context['has_clubs'] = True
        context['captions'] = club_caption
        context['on_campus'] = on_campus_list
        if on_campus_list:
            context['has_on_campus'] = True
        context['off_campus'] = off_campus_list
        if off_campus_list:
            context['has_off_campus'] = True
        if errors_found:
            raise CDEx(f"Errors found in resident template data.  See logs for details.")



def create_empty_dirpath(path):
    """Create an empty directory and make any intermediate directories."""
    try:
        if not test_run:
            if os.path.exists(path):
                if not os.path.isdir(path):
                    raise CDEx(f"Specified path, {path}, is not a directory in call to create_empty_dirpath.")
                shutil.rmtree(path)
                os.mkdir(path)
            else:
                os.makedirs(path, exist_ok=True)
    except NameError:
        pass
