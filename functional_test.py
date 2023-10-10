import logging
import os
import shutil
import unittest
import tempfile
import pathlib
import manager


class FunctionalTest(unittest.TestCase):
    def setUp(self) -> None:
        self.__tempdir = tempfile.mkdtemp()
        self.__test_config_dir = pathlib.Path(self.__tempdir) / "config"
        self.__test_config_dir.mkdir()
        logging.debug(f"Using tempdir {self.__tempdir}")
        self.__config_dir_args = ["--config-dir", str(self.__test_config_dir)]

    def tearDown(self) -> None:
        shutil.rmtree(self.__tempdir)

    def testConfigChangeManagementDir(self):
        arguments = self.__config_dir_args + [
            "config",
            "-m",
            os.path.join(self.__tempdir, "manage"),
        ]
        manager.main(arguments)
        with open(self.__test_config_dir / "management_dir", "r") as f:
            content = f.read().strip()
            self.assertEquals(os.path.join(self.__tempdir, "manage"), content)
