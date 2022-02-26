import sys
import os
import shutil
import yaml
from system_control.manage_google_drive import ManageGoogleDrive as mgd
import tempfile as tf
import pathlib as pl
from mako.template import Template
from mako.lookup import TemplateLookup
from mako.runtime import Context


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
        foo = 3

    def process_content(self):
        if "meta.txt" in self.filenames:
            has_meta = True
            with open(pl.Path(self.story_directory.name) / 'meta.txt') as stream:
                try:
                    story_meta_tmp = yaml.safe_load(stream)
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
        # if "photos.txt" in self.filenames:
        #     has_photos = True
        #     with open(pl.Path(self.story_directory.name) / 'photos.txt') as stream:
        #         path_dict = dict()
        #         for path in stream.readlines():
        #             if path.endswith('\n'):
        #                 path = path[0:-1]
        #             photo_name = path.split('/')[-1]
        #             path_dict[photo_name] = path
        # else:
        #     has_photos = False

        for file in self.filenames:
            file_parts = file.split(".")
            ext = file_parts[-1].lower()
            if ext == 'docx':
                if not has_meta:
                    raise ValueError(f"Folder: {self.folder_path} has no file meta.txt")
                self.process_docx(story_meta, file)
            elif ext == 'jpg':
                # if not has_photos:
                #     self.logger.make_error_entry(f"Photo {file} found in folder  without having a photos.txt")
                #     raise ValueError("Photos without photos.txt")
                try:
                    if 'photo_path' not in story_meta.keys():
                        self.logger.make_error_entry(f"There is no photo_path in meta.txt")
                        raise ValueError(f"Missing photo_path")
                    self.process_photo(story_meta['photo_path'], file)
                except:
                    self.logger.make_error_entry("No path in photos.txt for photo: {file}")
                    raise ValueError(f"No path in photos.txt for photo: {file}")

            elif ext == 'txt':
                if file == 'meta.txt' or file == 'photos.txt' or file == 'commands.txt':
                    pass
                elif 'template_mako' in story_meta.keys():
                    template = story_meta['template_mako']
                    if "file" not in story_meta or file != story_meta["file"]:
                        self.logger.make_error_entry(f"Unrecognized text file {file} not mentioned in meta.txt")
                        raise ValueError(f"Unrecognized text file {file} in {self.folder_path}")
                    self.process_template(story_meta, file)
                else:
                    self.logger.make_error_entry(f"Unrecognized text file {file} in {self.folder_path}")
                    raise ValueError(f"Unrecognized text file {file} in {self.folder_path}")
            else:
                self.logger.make_error_entry(f"Unrecognized file type {ext} in {self.folder_path}")
                raise ValueError(f"Unrecognized file type {ext} in {self.folder_path}")
        for dirname in self.galleries:
            # A directory represents a gallery and cannot be nested.
            self.process_gallery(pl.Path(self.story_directory.name) / dirname)

    def process_docx(self, story_meta, file):
        # copy docx file ensuring file corresponds to slug
        source = pl.Path(self.story_directory.name) / file
        target = self.docx_directory + story_meta['slug'] + ".docx"
        if os.path.exists(target):
            os.remove(target)
        shutil.copy(source, target)
        self._copy_meta_file(story_meta)

    def _copy_meta_file(self, story_meta, out_dir=None):
        if not out_dir:
            out_dir = pl.Path(self.docx_directory)
        # Copy meta file with proper renaming
        source = pl.Path(self.story_directory.name) / 'meta.txt'
        target = out_dir / (story_meta['slug'] + ".meta")
        if os.path.exists(target):
            os.remove(target)
        shutil.copy(source, target)

    def process_template(self, story_meta, file):
        template_name = story_meta['template_mako']
        file_path = pl.Path(self.story_directory.name) / file
        with open(file_path) as stream:
            try:
                story_content = yaml.safe_load_all(stream)
                story_content = [x for x in story_content]
                stream.close()
            except yaml.YAMLError as exc:
                self.logger.make_error_entry(f"YAML error encountered in {self.folder_path} with error {exc.args}")
                raise exc
        filename = 'new_content/templates/' + template_name + '.mako'
        template = Template(filename=filename)
        context = dict()
        context["head"] = story_content[0]
        context["body"] = []
        for el in story_content[1:]:
            if el:
                el['picture'] = story_meta['photo_path'] + el['picture']
                context["body"].append(el)
        results = template.render(**context)
        results = results.replace('\n\n', '\n')     # somehow, md ignores html following two blank lines.
        out_dir = pl.Path(self.sst_directory + story_meta['path'] + '/')
        os.makedirs(out_dir, exist_ok=True)
        with open(out_dir / (story_meta['slug'] + '.md'), 'w') as outfile:
            outfile.write(results)
            outfile.close()

        self._copy_meta_file(story_meta, out_dir=out_dir)

    def process_photo(self, path, file):
        ndx = 0
        if path[0] == '/':
            ndx = 1
        image_path = self.sst_directory + path[ndx:]
        source = pl.Path(self.story_directory.name) / file
        if self.first_photo:
            self.first_photo = False
            if os.path.exists(image_path):
                if os.path.isdir(image_path):
                    shutil.rmtree(image_path)
                else:
                    os.remove(image_path)
            os.makedirs(os.path.dirname(image_path))
        shutil.copy(source, image_path)

    def process_gallery(self, path_to_gallery):
        photo_files = os.listdir(path_to_gallery)
        resolved_gallery_path = pl.Path(path_to_gallery)
        if 'metadata.yml' in photo_files:
            with open(resolved_gallery_path / 'metadata.yml') as stream:
                try:
                    # Note: yaml is small and we convert to list so it can be reused
                    gallery_meta = [x for x in yaml.safe_load_all(stream)]
                except yaml.YAMLError as exc:
                    self.logger.make_error_entry(f"YAML error encountered in {path_to_gallery} with error {exc.args}")
                    raise exc
                # First - locate gallery path and gallery name
                gallery_path = None
                for doc in gallery_meta:
                    if doc:
                        keys = [key.lower() for key in doc.keys()]
                        vals = list(doc.values())
                        if 'gallery path' in keys:
                            gallery_path = vals[keys.index('gallery path')]
                if not gallery_path:
                    raise (f"Missing gallery path in {gallery_path}")
                gal_path = self.sst_directory + gallery_path[1:]
                create_empty_dirpath(gal_path)
                shutil.copy(resolved_gallery_path / 'metadata.yml', gal_path)
                for doc in gallery_meta:
                    if doc:
                        shutil.copy(resolved_gallery_path / doc['name'], gal_path + doc['name'])
        else:
            self.logger.make_error_entry(f"No metadata.yml file in {path_to_gallery}")
            raise ValueError(f"No metadata.yml file in {path_to_gallery}")


def create_empty_dirpath(path):
    """Create an empty directory and make any intermediate directories."""
    if os.path.exists(path):
        if not os.path.isdir(path):
            raise ValueError(f"Specified path, {path}, is not a directory in call to create_empty_dirpath.")
        shutil.rmtree(path)
        os.mkdir(path)
    else:
        os.makedirs(os.path.dirname(path), exist_ok=True)
