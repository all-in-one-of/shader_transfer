import os
import getpass

# Axis Shader preserver
_axis_appnet_drive_letter = 'C:\\'
_axis_base_drive_letter = 'M:\\'
AXIS_APPNET = os.environ.get('AXIS_APPNET') or os.path.join(_axis_appnet_drive_letter, 'appnet', 'applications')
AXIS_BASE = os.environ.get('AXIS_BASE') or os.path.join(_axis_base_drive_letter, 'software')
AXIS_PROJECT_FOLDER_DRIVE = 'P:\\'
AXIS_CACHE_FOLDER_DRIVE = 'T:\\'

_here = os.path.dirname(os.path.normpath(__file__))
SHADERS_SETTINGS_LOGGING = os.path.join(_here, 'settings_logging.json')
SHADERS_SAVE_BASE = os.environ.get('SHADER_SAVE_BASE', '').strip() or os.path.join(
    os.environ['PROJECT'], 'data', 'user', getpass.getuser())
SHADERS_LOG_FILENAME = os.path.join(os.path.expanduser("~"), '.shadersaver', 'shadersaver.log')

SPECIAL_PARMS = {'mainDoOpacity': 'OpacEnable'}

SPECIAL_TYPES = {'AXIS_Shading_Model_V3': ' AXIS_Shading_Model_V4'}
