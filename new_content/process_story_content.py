import sys
import os
import shutil
import yaml
from system_control.manage_google_drive import ManageGoogleDrive as mgd
import tempfile as tf
import pathlib as pl


class ProcessStoryContent(object):
    def __init__(self, logger, folder_path, temp_directory, docx_directory, sst_directory,
                 image_directory, gallery_directory):
        self.logger = logger
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
        # Note, downloading to max-depth=2 downloads contents of any galleries.
        self.drive.download_directory(self.logger, self.folder_path, mgd.add_slash(self.story_directory.name), max_depth=2)


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
        if "photos.txt" in self.filenames:
            has_photos = True
            with open(pl.Path(self.story_directory.name) / 'photos.txt') as stream:
                path_dict = dict()
                for path in stream.readlines():
                    if path.endswith('\n'):
                        path = path[0:-1]
                    photo_name = path.split('/')[-1]
                    path_dict[photo_name] = path
        else:
            has_photos = False

        for file in self.filenames:
            file_parts = file.split(".")
            ext = file_parts[-1].lower()
            if ext == 'docx':
                if not has_meta:
                    raise ValueError(f"Folder: {self.folder_path} has no file meta.txt")
                # copy docx file ensuring file corresponds to slug
                source = pl.Path(self.story_directory.name) / file
                target = self.docx_directory + story_meta['slug'] + ".docx"
                if os.path.exists(target):
                    os.remove(target)
                shutil.copy(source, target)
                # Copy meta file with proper renaming
                source = pl.Path(self.story_directory.name) / 'meta.txt'
                target = self.docx_directory + story_meta['slug'] + ".meta"
                if os.path.exists(target):
                    os.remove(target)
                shutil.copy(source, target)
            elif ext == 'jpg':
                if not has_photos:
                    self.logger.make_error_entry(f"Photo {file} found in folder  without having a photos.txt")
                    raise ValueError("Photos without photos.txt")
                try:
                    image_path = self.sst_directory + path_dict[file][1:]
                    os.makedirs(os.path.dirname(image_path), exist_ok=True)
                    source = pl.Path(self.story_directory.name) / file
                    if os.path.exists(image_path):
                        os.remove(image_path)
                    shutil.copy(source, image_path)
                except:
                    self.logger.make_error_entry("No path in photos.txt for photo: {file}")
                    raise ValueError(f"No path in photos.txt for photo: {file}")

            elif ext == 'txt':
                if file == 'meta.txt' or file == 'photos.txt' or 'commands.txt':
                    pass
                else:
                    self.logger.make_error_entry(f"Unrecognized text file {file} in {self.folder_path}")
                    raise ValueError(f"Unrecognized text file {file} in {self.folder_path}")
            else:
                self.logger.make_error_entry(f"Unrecognized file type {ext} in {self.folder_path}")
                raise ValueError(f"Unrecognized file type {ext} in {self.folder_path}")
        for dirname in self.galleries:
            # A directory represents a gallery and cannot be nested.
            self.process_gallery(pl.Path(self.story_directory.name) / dirname)

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
                create_empty_dirpath(gal_path)                              # THIS IS ONLY OCCURRENCE - make linux tempdir
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
