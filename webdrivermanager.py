# -*- coding: utf-8 -*-

import abc
import logging
import os
import os.path
import platform
import shutil
import stat
import sys
import tarfile
import zipfile

import requests
import tqdm
from appdirs import AppDirs

LOGGER = logging.getLogger(__name__)


def _inside_virtualenv():
    return hasattr(sys, "real_prefix") or hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix


def raise_runtime_error(msg):
    LOGGER.error(msg)
    raise RuntimeError(msg)


def versiontuple(v):
    return tuple(map(int, (v.split("."))))


class WebDriverManagerBase:
    """Abstract Base Class for the different web driver downloaders
    """

    __metaclass__ = abc.ABCMeta
    fallback_url = None
    driver_filenames = None

    def _get_basepath(self):
        if self.os_name in ["mac", "linux"] and os.geteuid() == 0:
            return self.dirs.site_data_dir
        if _inside_virtualenv():
            return os.path.join(sys.prefix, "WebDriverManager")
        return self.dirs.user_data_dir

    def __init__(self, download_root=None, link_path=None, os_name=None, bitness=None):
        """
        Initializer for the class.  Accepts two optional parameters.

        :param download_root: Path where the web driver binaries will be downloaded.  If running as root in macOS or
                              Linux, the default will be '/usr/local/webdriver', otherwise python appdirs module will
                              be used to determine appropriate location if no value given.
        :param link_path: Path where the link to the web driver binaries will be created.  If running as root in macOS
                          or Linux, the default will be 'usr/local/bin', otherwise appdirs python module will be used
                          to determine appropriate location if no value give. If set "AUTO", link will be created into
                          first writeable directory in PATH. If set "SKIP", no link will be created.
        """

        if not bitness:
            self.bitness = "64" if sys.maxsize > 2 ** 32 else "32"  # noqa: KEK100
        else:
            self.bitness = bitness

        self.os_name = os_name or self.get_os_name()
        self.dirs = AppDirs("WebDriverManager", "salabs_")
        base_path = self._get_basepath()
        self.download_root = download_root or base_path

        if link_path in [None, "AUTO"]:
            bin_location = "bin"
            if _inside_virtualenv():
                if self.os_name == "win" and "CYGWIN" not in platform.system():
                    bin_location = "Scripts"
                self.link_path = os.path.join(sys.prefix, bin_location)
            else:
                if self.os_name in ["mac", "linux"] and os.geteuid() == 0:
                    self.link_path = "/usr/local/bin"
                else:
                    dir_in_path = None
                    if link_path == "AUTO":
                        dir_in_path = self._find_bin()
                    self.link_path = dir_in_path or os.path.join(base_path, bin_location)
        elif link_path == "SKIP":
            self.link_path = None
        else:
            self.link_path = link_path

        try:
            os.makedirs(self.download_root)
            LOGGER.info("Created download root directory: %s", self.download_root)
        except OSError:
            pass

        if self.link_path is not None:
            try:
                os.makedirs(self.link_path)
                LOGGER.info("Created symlink directory: %s", self.link_path)
            except OSError:
                pass

    def _find_bin(self):
        dirs = os.environ["PATH"].split(os.pathsep)
        for directory in dirs:
            if os.access(directory, os.W_OK):
                return directory
        return None

    def get_os_name(self):
        platform_name = platform.system()
        namelist = {"Darwin": "mac", "Windows": "win", "Linux": "linux"}
        if "CYGWIN" in platform_name:
            return "win"

        return namelist[platform_name]

    @abc.abstractmethod
    def get_download_path(self, version="latest"):
        """
        Method for getting the download path for a web driver binary.

        :param version: String representing the version of the web driver binary to download.  For example, "2.38".
                        Default if no version is specified is "latest".  The version string should match the version
                        as specified on the download page of the webdriver binary.

        :returns: The download path of the web driver binary.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get_download_url(self, version="latest"):
        """
        Method for getting the download URL for a web driver binary.

        :param version: String representing the version of the web driver binary to download.  For example, "2.38".
                        Default if no version is specified is "latest".  The version string should match the version
                        as specified on the download page of the webdriver binary.
        :returns: The download URL for the web driver binary.
        """
        raise NotImplementedError

    def get_driver_filename(self):
        return self.driver_filenames[self.os_name]

    def download(
        self, version="latest", show_progress_bar=True, dl_path=None
    ):  # pylint: disable=inconsistent-return-statements
        """
        Method for downloading a web driver binary.

        :param version: String representing the version of the web driver binary to download.  For example, "2.38".
                        Default if no version is specified is "latest".  The version string should match the version
                        as specified on the download page of the webdriver binary.  Prior to downloading, the method
                        will check the local filesystem to see if the driver has been downloaded already and will
                        skip downloading if the file is already present locally.
        :param show_progress_bar: Boolean (default=install_requires) indicating if a progress bar should be shown in the console.
        :returns: The path + filename to the downloaded web driver binary.
        """
        (download_url, filename) = self.get_download_url(version)

        if not dl_path:
            dl_path = self.get_download_path(version)
        filename_with_path = os.path.join(dl_path, filename)
        if not os.path.isdir(dl_path):
            os.makedirs(dl_path)
        if os.path.isfile(filename_with_path):
            LOGGER.info("Skipping download. File %s already on filesystem.", filename_with_path)
            return filename_with_path
        data = requests.get(download_url, stream=True)
        if data.status_code == 200:
            LOGGER.debug("Starting download of %s to %s", download_url, filename_with_path)
            with open(filename_with_path, mode="wb") as fileobj:
                chunk_size = 1024
                if show_progress_bar:
                    expected_size = int(data.headers["Content-Length"])
                    for chunk in tqdm.tqdm(
                        data.iter_content(chunk_size), total=int(expected_size / chunk_size), unit="kb"
                    ):
                        fileobj.write(chunk)
                else:
                    for chunk in data.iter_content(chunk_size):
                        fileobj.write(chunk)
            LOGGER.debug("Finished downloading %s to %s", download_url, filename_with_path)
            return filename_with_path

        raise_runtime_error("Error downloading file {0}, got status code: {1}".format(filename, data.status_code))
        return None

    def download_and_install(self, version="latest", show_progress_bar=True, dl_path=None, extract_dir=None):
        """
        Method for downloading a web driver binary, extracting it into the download directory and creating a symlink
        to the binary in the link directory.

        :param version: String representing the version of the web driver binary to download.  For example, "2.38".
                        Default if no version is specified is "latest".  The version string should match the version
                        as specified on the download page of the webdriver binary.
        :param show_progress_bar: Boolean (default=install_requires) indicating if a progress bar should be shown in
                                  the console.
        :returns: Tuple containing the path + filename to [0] the extracted binary, and [1] the symlink to the
                  extracted binary.
        """
        driver_filename = self.get_driver_filename()
        if driver_filename is None:
            raise_runtime_error("Error, unable to find appropriate drivername for {0}.".format(self.os_name))

        filename_with_path = self.download(version, show_progress_bar=show_progress_bar, dl_path=dl_path)
        filename = os.path.split(filename_with_path)[1]
        if not dl_path:
            dl_path = self.get_download_path(version)
        if not extract_dir:
            if filename.lower().endswith(".tar.gz"):
                extract_dir = os.path.join(dl_path, filename[:-7])
            elif filename.lower().endswith(".zip"):
                extract_dir = os.path.join(dl_path, filename[:-4])
            elif filename.lower().endswith(".exe"):
                extract_dir = os.path.join(dl_path, filename[:-4])
            else:
                raise_runtime_error("Unknown archive format: {0}".format(filename))

        if not os.path.isdir(extract_dir):
            os.makedirs(extract_dir)
            LOGGER.debug("Created directory: %s", extract_dir)
        if filename.lower().endswith(".tar.gz"):
            with tarfile.open(os.path.join(dl_path, filename), mode="r:*") as tar:
                tar.extractall(extract_dir)
                LOGGER.debug("Extracted files: %s", ", ".join(tar.getnames()))
        elif filename.lower().endswith(".zip"):
            with zipfile.ZipFile(os.path.join(dl_path, filename), mode="r") as driver_zipfile:
                driver_zipfile.extractall(extract_dir)
        elif filename.lower().endswith(".exe"):
            shutil.copy2(os.path.join(dl_path, filename), os.path.join(extract_dir, filename))

        os.remove(os.path.join(dl_path, filename))
        os.chmod(os.path.join(extract_dir, self.driver_filenames[self.os_name]), 755)

        actual_driver_filename = None
        for root, _, files in os.walk(extract_dir):
            for curr_file in files:
                if curr_file in driver_filename:
                    actual_driver_filename = os.path.join(root, curr_file)
                    break

        if not actual_driver_filename:
            LOGGER.warning("Cannot locate binary %s from the archive", driver_filename)
            return None

        if not self.link_path:
            return (actual_driver_filename, None)

        if self.os_name in ["mac", "linux"]:
            symlink_src = actual_driver_filename
            symlink_target = os.path.join(self.link_path, driver_filename)
            if os.path.islink(symlink_target) or os.path.exists(symlink_target):
                if os.path.samefile(symlink_src, symlink_target):
                    LOGGER.info("Symlink already exists: %s -> %s", symlink_target, symlink_src)
                    return (symlink_src, symlink_target)

                LOGGER.warning("Symlink target %s already exists and will be overwritten.", symlink_target)
                os.unlink(symlink_target)

            os.symlink(symlink_src, symlink_target)
            LOGGER.info("Created symlink: %s -> %s", symlink_target, symlink_src)
            symlink_stat = os.stat(symlink_src)
            os.chmod(symlink_src, symlink_stat.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
            return (symlink_src, symlink_target)
        # self.os_name == 'win':
        src_file = actual_driver_filename
        dest_file = os.path.join(self.link_path, os.path.basename(actual_driver_filename))
        try:
            if os.path.isfile(dest_file):
                LOGGER.info("File %s already exists and will be overwritten.", dest_file)
        except OSError:
            pass
        shutil.copy2(src_file, dest_file)
        dest_stat = os.stat(dest_file)
        os.chmod(dest_file, dest_stat.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        return (src_file, dest_file)


class ChromeDriverManager(WebDriverManagerBase):
    """Class for downloading the Google Chrome WebDriver.
    """

    # chrome_driver_base_url = 'https://www.googleapis.com/storage/v1/b/chromedriver'
    chrome_driver_base_url = "https://chromedriver.storage.googleapis.com"

    def _get_latest_version_number(self):
        # resp = requests.get(self.chrome_driver_base_url + '/o/LATEST_RELEASE')
        resp = requests.get(self.chrome_driver_base_url + "/LATEST_RELEASE")
        if resp.status_code != 200:
            raise_runtime_error(
                "Error, unable to get version number for latest release, got code: {0}".format(resp.status_code)
            )

        # latest_release = requests.get(resp.json()['mediaLink'])
        return resp.text

    driver_filenames = {
        "win": "chromedriver.exe",
        "mac": "chromedriver",
        "linux": "chromedriver",
    }

    driver_zipfilenames = {
        "win": "chromedriver_win32.zip",
        "mac": "chromedriver_mac64.zip",
        "linux": "chromedriver_linux64.zip",
    }

    def get_version_number(self, version="latest"):
        if version == "latest":
            resp = requests.get(self.chrome_driver_base_url + "/LATEST_RELEASE")
        else:
            resp = requests.get(self.chrome_driver_base_url + "/LATEST_RELEASE_" + version)
        if resp.status_code != 200:
            print(self.chrome_driver_base_url + "/LATEST_RELEASE_" + version)
            raise_runtime_error(
                "Error, unable to get version number for latest release, got code: {}".format(resp.status_code)
            )
        return resp.text

    def get_download_url(self, version="latest"):
        """
        Method for getting the download URL for the Google Chome driver binary.

        :param version: String representing the version of the web driver binary to download.  For example, "2.39".
                        Default if no version is specified is "latest".  The version string should match the version
                        as specified on the download page of the webdriver binary.
        :returns: The download URL for the Google Chrome driver binary.
        """
        version_number = self.get_version_number(version)
        zipfilename = self.driver_zipfilenames[self.os_name]
        url = os.path.join(self.chrome_driver_base_url, version_number, zipfilename)
        return (url, zipfilename)


AVAILABLE_DRIVERS = {"chrome": ChromeDriverManager}
