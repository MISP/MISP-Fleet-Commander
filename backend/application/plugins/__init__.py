import os
import fnmatch
import inspect
import importlib
from application import flaskApp

def loadPlugins():
    phandlers = {}
    plugins = []
    cwd = os.getcwd()
    os.chdir(os.path.dirname(__file__))
    for root, dirnames, filenames in os.walk('.'):
        if os.path.basename(root) == '__pycache__':
            continue
        for filename in fnmatch.filter(filenames, '*.py'):
            if root.split('/')[-1].startswith('_'):
                continue
            if filename == '__init__.py':
                continue
            modulename = filename.split(".")[0]
            try:
                phandlers[modulename] = importlib.import_module('application.plugins.' + modulename)
            except Exception as e:
                flaskApp.logger.warning('Plugin {0} failed due to {1}'.format(modulename, e))
                continue
            plugins.append(modulename)
            flaskApp.logger.debug('Plugin {0} imported'.format(modulename))
    os.chdir(cwd)
    return phandlers, plugins

def loadAvailablePlugins(enabledPlugins = ['*']):
    phandlers, _ = loadPlugins()
    plugins = []
    for name, _ in phandlers.items():
        pluginClasses = inspect.getmembers(phandlers[name], inspect.isclass)
        for pluginClassName, pluginClass in pluginClasses:
            if pluginClassName == name:
                instantiatedPlugin = pluginClass()
                plugin = {
                    'id': instantiatedPlugin.id,
                    'name': instantiatedPlugin.name,
                    'description': instantiatedPlugin.description,
                    'icon': instantiatedPlugin.icon,
                    'action_parameters': instantiatedPlugin.action_parameters,
                    'filename': name,
                    'features': instantiatedPlugin.introspection(),
                    'instance': instantiatedPlugin
                }
                if (isPluginEnabled(enabledPlugins, instantiatedPlugin.id)):
                    plugins.append(plugin)
    return plugins

def isPluginEnabled(enabledPlugins, pluginName):
    print(pluginName)
    if '*' in enabledPlugins:
        return True
    for plugin in enabledPlugins:
        if pluginName == plugin:
            return True
    return False