import os
import fnmatch
import inspect
import importlib

def load_modules():
    mhandlers = {}
    helpers = []
    cwd = os.getcwd()
    os.chdir(os.path.dirname(__file__))
    for root, dirnames, filenames in os.walk('helpers'):
        if os.path.basename(root) == '__pycache__':
            continue
        if os.path.basename(root).startswith("."):
            continue
        for filename in fnmatch.filter(filenames, '*.py'):
            if root.split('/')[-1].startswith('_'):
                continue
            if filename == '__init__.py':
                continue
            modulename = filename.split(".")[0]
            if modulename == 'baseAdministrationHelper':
                continue
            try:
                mhandlers[modulename] = importlib.import_module('application.plugins.server_administration.helpers.' + modulename)
            except Exception as e:
                print('Helper {0} failed due to {1}'.format(modulename, e))
                continue
            helpers.append(modulename)
            print('Helper {0} imported'.format(modulename))
    os.chdir(cwd)
    return mhandlers, helpers

def loadAvailableHelpers():
    mhandlers, helpers = load_modules()
    helpers = []
    for name, module in mhandlers.items():
        moduleClasses = inspect.getmembers(mhandlers[name], inspect.isclass)
        for moduleClassName, moduleClass in moduleClasses:
            if moduleClassName == name:
                instantiatedHelper = moduleClass()
                helper = {
                    'name': instantiatedHelper.name,
                    'filename': name,
                    'features': instantiatedHelper.introspection(),
                    'instance': instantiatedHelper
                }
                helpers.append(helper)
    return helpers
