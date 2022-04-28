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
        self.first_photo = True     # switch to detect processing of first photo
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
        self.pages_directory = pl.Path(self.sst_directory) / 'pages/'
        # Note, downloading to max-depth=2 downloads contents of any galleries.
        self.drive.download_directory(self.logger, self.folder_path, mgd.add_slash(self.story_directory.name), max_depth=2)

    def process_content(self):
        if "meta.txt" in self.filenames:
            has_meta = True
            with open(pl.Path(self.story_directory.name) / 'meta.txt') as stream:
                try:
                    story_meta_tmp = yaml.safe_load(stream.read().replace('\t', ' '))
                    story_meta = dict()
                    for key in story_meta_tmp:  # the meta file may have leading periods on the attributes, remove them
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
                    self.logger.make_error_entry(f"Folder: {self.folder_path} has no file meta.txt")
                    raise CDEx(f"Folder: {self.folder_path} has no file meta.txt")
                self.process_docx(story_meta, file)
            elif ext == 'jpg':
                # if not has_photos:
                #     self.logger.make_error_entry(f"Photo {file} found in folder  without having a photos.txt")
                #     raise ValueError("Photos without photos.txt")
                try:
                    if 'photo_path' not in story_meta.keys():
                        self.logger.make_error_entry(f"There is no photo_path in meta.txt")
                        raise CDEx(f"Missing photo_path")
                    self.process_photo(story_meta['photo_path'], file)
                except:
                    self.logger.make_error_entry("No path in photos.txt for photo: {file}")
                    raise CDEx(f"No path in photos.txt for photo: {file}")

            elif ext == 'txt':
                if file == 'meta.txt' or file == 'photos.txt' or file == 'commands.txt':
                    pass
                elif 'template_mako' in story_meta.keys():
                    template = story_meta['template_mako']
                    if "file" not in story_meta or file != story_meta["file"]:
                        self.logger.make_error_entry(f"Unrecognized text file {file} in {self.folder_path}")
                        raise CDEx(f"Unrecognized text file {file} in {self.folder_path}")
                    self.process_template(story_meta, file)
                else:
                    self.logger.make_error_entry(f"Unrecognized text file {file} in {self.folder_path}")
                    raise CDEx(f"Unrecognized text file {file} in {self.folder_path}")
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
                self.logger.make_error_entry(f"Unrecognized file type {ext} in {self.folder_path}")
                raise CDEx(f"Unrecognized file type {ext} in {self.folder_path}")
        for dirname in self.galleries:
            # A directory represents a gallery and cannot be nested.
            self.process_gallery(pl.Path(self.story_directory.name) / dirname)

    def process_docx(self, story_meta, file):
        # copy docx file ensuring file corresponds to slug
        source = pl.Path(self.story_directory.name) / file
        val_sc = vs.ValidateShortcodes(source, 'docx', self.logger)
        val_sc.clean_docx()           # Already duplicated in nikola command
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
        # Copy meta file with proper renaming
        source = pl.Path(self.story_directory.name) / 'meta.txt'
        target = out_dir / (story_meta['slug'] + ".meta")
        try:
            if not test_run:
                if os.path.exists(target):
                    os.remove(target)
                shutil.copy(source, target)
        except NameError:
            pass

    def process_template(self, story_meta, file):
        self.logger.make_info_entry(f"Start processing template on file: {file}")
        template_name = story_meta['template_mako']
        file_path = pl.Path(self.story_directory.name) / file
        with open(file_path) as stream:
            try:
                story_content = yaml.safe_load_all(stream)
                story_content = [x for x in story_content]
                stream.close()
            except yaml.YAMLError as exc:
                self.logger.make_error_entry(f"YAML error encountered in {self.folder_path} with error {exc.args}")
                raise CDEx(f"YAML error {exc.args}")
        if not template_name.endswith('.mako'):
            filename = 'new_content/templates/' + template_name + '.mako'
        else:
            filename = 'new_content/templates/' + template_name
        template = Template(filename=filename)
        context = dict()
        context["head"] = story_content[0]
        context["body"] = []
        for el in story_content[1:]:
            if el:
                if 'photo_path' in story_meta.keys():     # support pictures - such as in Sunnybear
                    el['picture'] = story_meta['photo_path'] + el['picture']
                context["body"].append(el)
        results = template.render(**context)
        results = results.replace('\n\n', '\n')     # somehow, md ignores html following two blank lines.
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

    def process_gallery(self, path_to_gallery):
        if os.path.exists(path_to_gallery):     # can be empty if there was an ignore folder
            photo_files = os.listdir(path_to_gallery)
            resolved_gallery_path = pl.Path(path_to_gallery)
            if 'metadata.yml' in photo_files:
                with open(resolved_gallery_path / 'metadata.yml') as stream:
                    try:
                        # Note: yaml is small and we convert to list so it can be reused
                        gallery_meta = [x for x in yaml.safe_load_all(stream)]
                    except yaml.YAMLError as exc:
                        self.logger.make_error_entry(f"YAML error encountered in {path_to_gallery} with error {exc.args}")
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
                self.logger.make_error_entry(f"No metadata.yml file in {path_to_gallery}")
                raise CDEx(f"No metadata.yml file in {path_to_gallery}")


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
