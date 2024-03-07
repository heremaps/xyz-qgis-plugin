# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2019 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

import os
import platform
import time
import shutil
import gzip
import sysconfig
from typing import List

from qgis.PyQt.uic import loadUiType
from . import config


def get_current_millis_time():
    return int(round(time.time() * 1000))


def disconnect_silent(signal, fn=None):
    ok = True
    try:
        if fn is None:
            signal.disconnect()
        else:
            signal.disconnect(fn)
    except TypeError:
        ok = False
    return ok


def get_ui_class(ui_file):
    """return class object of a uifile"""
    ui_file_full = os.path.join(config.PLUGIN_DIR, "xyz_qgis", "gui", "ui", ui_file)
    return loadUiType(ui_file_full)[0]


def get_qml_full_path(qml_file):
    return os.path.join(config.PLUGIN_DIR, "xyz_qgis", "gui", "qml", qml_file)


def add_qml_import_path(qml_engine):
    # Setup for the MAC OS X platform:
    # return
    if platform.system() == "Darwin" or os.name == "mac":
        install_qml_dependencies()
        qml_engine.addImportPath(os.path.join(get_qml_import_base_path(), "qml"))
        qml_engine.addImportPath(os.path.join(get_qml_import_base_path(), "bin"))
    elif platform.system() == "Linux" or os.name == "posix":
        install_qml_dependencies()
        qml_engine.addImportPath(os.path.join(get_qml_import_base_path(), "qml"))
        qml_engine.addImportPath(os.path.join(get_qml_import_base_path(), "bin"))
    elif platform.system() == "Windows" or os.name == "nt":
        pass  # import only for outdated QGIS

    print(qml_engine.importPathList())
    print(qml_engine.pluginPathList())


def make_unique_full_path(ext="json"):
    return os.path.join(config.TMP_DIR, "%s.%s" % (time.time(), ext))


def make_fixed_full_path(name="temp", ext="json"):
    return os.path.join(config.TMP_DIR, "%s.%s" % (name, ext))


def clear_cache():
    files = [os.path.join(config.TMP_DIR, f) for f in os.listdir(config.TMP_DIR)]
    files.append(config.LOG_FILE)
    for f in files:
        try:
            os.remove(f)
        except OSError:
            pass  # files in used


def archive_log_file():
    if not os.path.exists(config.LOG_FILE):
        return
    threshold = 5 * 1024 * 1024
    if os.path.getsize(config.LOG_FILE) < threshold:
        return
    base, _ = os.path.split(config.LOG_FILE)
    idx = len([s for s in os.listdir(base) if s.endswith(".gz")])
    archive_path = os.path.join(base, "qgis.%s.log.gz" % idx)
    with open(config.LOG_FILE, "rb") as f_in:
        with gzip.open(archive_path, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)
    with open(config.LOG_FILE, "w") as f_in:
        pass


archive_log_file()


def read_properties_file(filepath, separator="=", commentcharacter="#") -> dict:
    """Read properties file in a dictionary.

    :param filepath: path of properties file
    :param separator: the separator of the properties file with default as '='
    :param commentcharacter: comment character in the properties file to be ignored. Default value
        is '#'.
    :return: the dictionary of properties
    :rtype: dict

    Example:

    >>> read_properties_file('credentials.properties')
    """
    credentials_properties = dict()
    with open(filepath, "rb") as file_handler:
        for line in file_handler:
            decoded_line = line.decode("utf-8").strip()
            if decoded_line and not decoded_line.startswith(commentcharacter):
                key_value = decoded_line.split(separator)
                key = key_value[0].strip()
                value = separator.join(key_value[1:]).strip()
                credentials_properties[key] = value
    return credentials_properties


def _confirm_with_dialog(package: str, extra_packages: List[str] = []) -> bool:
    from qgis.PyQt.QtWidgets import QMessageBox

    message = (
        "The following Python packages are required to use the plugin"
        f" {config.PLUGIN_NAME}:\n\n"
    )
    message += "\n".join([package, *extra_packages])
    message += "\n\nWould you like to install them now? After installation please restart QGIS."

    reply = QMessageBox.question(
        None,
        "Missing Dependencies",
        message,
        QMessageBox.Yes | QMessageBox.No,
        QMessageBox.No,
    )

    if reply == QMessageBox.Yes:
        return True
    return False


def install_package(
    package, module_name="", package_version="", target_path="", extra_packages=[]
):
    module_name = module_name or package
    do_install = False

    import importlib
    import importlib.metadata

    def _reload(module_name):
        importlib.invalidate_caches()
        base_module_name = module_name.split(".")[0]
        base_module = importlib.import_module(base_module_name)
        importlib.reload(base_module)
        importlib.import_module(module_name)

    try:

        _reload(module_name)  # require for PyQt5

        installed_version = importlib.metadata.version(package)
        print(package, installed_version)
        if package_version and package_version != installed_version:
            do_install = False
    except Exception as e:
        print(repr(e))
        do_install = True
    if do_install:
        do_install = _confirm_with_dialog(package, extra_packages)

    if do_install:
        pip_exec = os.path.join(sysconfig.get_path("scripts"), "pip3")
        args = (
            [
                "install",
                "-U",
                "--log",
                config.PYTHON_LOG_FILE,
                "--trusted-host",
                "pypi.org",
                "--trusted-host",
                "files.pythonhosted.org",
                f"{package}=={package_version}" if package_version else package,
            ]
            + extra_packages
            + (["-t", target_path] if target_path else [])
        )
        py_exec = os.path.join(sysconfig.get_path("scripts"), "..", "python3")
        py_args = ["-m", "pip", *args]

        with open(config.PYTHON_LOG_FILE, "w") as f:
            pass

        installed = False
        try:
            cmd = f'"{pip_exec}" {" ".join(args)}'
            # cmd = f'"{py_exec}" {" ".join(py_args)}'
            # print(cmd); cmd += " && pause || pause" # debug
            # print(cmd); cmd += "; read -n 1" # debug
            ret = os.system(cmd)
            print(ret)
            if ret == 0:
                installed = True
        except Exception as e:
            print(e)
        if not installed:
            try:
                import subprocess

                subprocess.check_call([pip_exec, *args])
                # subprocess.check_call([py_exec, *py_args])
            except Exception as e:
                print(e)

        if ret > 0:
            with open(config.PYTHON_LOG_FILE, "r") as f:
                txt = f.read()
            raise Exception(txt)

        # _reload(module_name)


def install_qml_dependencies():
    package_version = config.get_plugin_setting("PyQtWebEngine_version")
    # install_package(
    #     "PyQtWebEngine", "PyQt5.QtWebEngine", package_version, config.EXTERNAL_LIB_DIR
    # )  # , "5.15.2")
    install_package(
        "PyQtWebEngine",
        "PyQt5.QtWebEngine",  # "PyQt5.QtWebEngineWidgets"
        package_version,
        config.EXTERNAL_LIB_DIR,
        extra_packages=["PyQt5-Qt5"],
    )


def get_qml_import_base_path():
    prefix = sysconfig.get_path("purelib")
    lib_path = f"{prefix}/PyQt5/Qt5"
    try:
        import importlib.metadata

        lib_path = os.path.join(
            importlib.metadata.distribution("PyQtWebEngine").locate_file("PyQt5"), "Qt5"
        )
    except Exception as e:
        print(repr(e))
        # lib_path = config.get_external_os_lib()

    print(lib_path)
    return lib_path


def is_here_system():
    return config.is_here_system()
