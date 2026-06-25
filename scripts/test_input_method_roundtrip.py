from __future__ import annotations

from copy import deepcopy
from itertools import product
from pathlib import Path
import sys


ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / 'src' / 'backend'

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from unattend_generator import UnattendGenerator, config_dict_to_configuration  # noqa: E402


def build_base_config() -> dict:
    return {
        'languageSettings': {
            'mode': 'preset',
            'uiLanguage': 'en-US',
            'userLocale': 'en-US',
            'keyboardLayout': '0409:00000409',
        },
        'processorArchitectures': ['amd64'],
        'setupSettings': {
            'bypassRequirements': False,
            'bypassNetwork': False,
            'disableOobePrivacyPrompts': False,
            'useConfigurationSet': False,
            'hidePowerShell': False,
            'keepSensitiveFiles': False,
            'useNarrator': False,
        },
        'computerName': {'mode': 'random'},
        'timeZone': {'mode': 'implicit'},
        'partitioning': {'mode': 'interactive'},
        'windowsEdition': {'mode': 'interactive'},
        'peSettings': {'mode': 'default'},
        'accountSettings': {'mode': 'interactive-local', 'obscurePasswords': True},
        'passwordExpiration': {'mode': 'default'},
        'lockoutSettings': {'mode': 'default'},
        'fileExplorer': {
            'showFileExtensions': False,
            'hideFiles': 'hidden',
            'launchToThisPC': False,
            'classicContextMenu': False,
            'showEndTask': False,
            'hideRecentInQuickAccess': False,
            'hideFrequentInQuickAccess': False,
            'hideCloudFilesInQuickAccess': False,
            'hideRecommendations': False,
            'navigationPane': {},
            'folderDialog': {},
        },
        'startMenuTaskbar': {
            'leftTaskbar': False,
            'hideTaskViewButton': False,
            'taskbarSearch': 'box',
            'disableWidgets': False,
            'showAllTrayIcons': False,
            'disableBingResults': False,
            'startTilesMode': 'default',
            'startPinsMode': 'default',
        },
        'systemTweaks': {},
        'visualEffects': {'mode': 'default'},
        'desktopIcons': {'mode': 'default', 'deleteEdgeDesktopIcon': False},
        'startFolders': {'mode': 'default'},
        'vmSupport': {},
        'wifi': {'mode': 'skip'},
        'expressSettings': 'disableAll',
        'lockKeys': {'mode': 'skip'},
        'stickyKeys': {'mode': 'default'},
        'personalization': {
            'wallpaper': {'mode': 'default'},
            'lockScreen': {'mode': 'default'},
            'color': {'mode': 'default'},
            'inputMethod': {
                'englishSwitchKeyCtrl': False,
                'englishSwitchKeyCtrlSpace': True,
                'englishSwitchKeyShift': True,
                'enableFullHalfWidthSwitchKey': False,
                'enableSimplifiedTraditionalOutputSwitch': True,
                'enableCloudCandidate': True,
            },
        },
        'bloatware': {'items': []},
        'scripts': {
            'system': [],
            'defaultUser': [],
            'firstLogon': [],
            'userOnce': [],
            'restartExplorer': False,
        },
        'appLocker': {'mode': 'skip'},
        'xmlMarkup': {'components': []},
    }


def assert_equal(actual, expected, message: str) -> None:
    if actual != expected:
        raise AssertionError(f'{message}: expected={expected!r}, actual={actual!r}')


def _english_switch_key_reg_value(input_method: dict) -> int:
    value = 0
    if input_method.get('englishSwitchKeyCtrlSpace'):
        value |= 1
    if input_method.get('englishSwitchKeyCtrl'):
        value |= 2
    if input_method.get('englishSwitchKeyShift'):
        value |= 4
    return value


def run_case(generator: UnattendGenerator, case_name: str, input_method: dict) -> None:
    config_dict = build_base_config()
    config_dict['personalization']['inputMethod'] = deepcopy(input_method)

    configuration = config_dict_to_configuration(config_dict, generator)
    xml_bytes = generator.generate_xml(configuration)
    xml_text = xml_bytes.decode('utf-8')
    parsed = generator.parse_xml(xml_bytes)
    parsed_input_method = parsed['personalization']['inputMethod']

    assert_equal(parsed_input_method, input_method, f'{case_name} roundtrip mismatch')

    for registry_root in (
        r'HKU\DefaultUser\Software\Microsoft\InputMethod\Settings\CHS',
        r'HKCU\Software\Microsoft\InputMethod\Settings\CHS',
    ):
        if registry_root not in xml_text:
            raise AssertionError(f'{case_name} missing registry root in XML: {registry_root}')

    required_value_names = [
        'English Switch Key',
        'EnableFullHalfWidthSwitchKey',
        'EnableSimplifiedTraditionalOutputSwitch',
        'Enable Cloud Candidate',
    ]
    for value_name in required_value_names:
        if value_name not in xml_text:
            raise AssertionError(f'{case_name} missing registry value in XML: {value_name}')

    # Verify English Switch Key DWORD is the correct bitwise OR
    expected_value = _english_switch_key_reg_value(input_method)
    expected_value_str = str(expected_value)
    import re
    for root_path in (
        r'HKU\\DefaultUser\\Software\\Microsoft\\InputMethod\\Settings\\CHS',
        r'HKCU\\Software\\Microsoft\\InputMethod\\Settings\\CHS',
    ):
        pattern = rf'reg\.exe add "{root_path}" /v "English Switch Key" /t REG_DWORD /d (\d+) /f;'
        match = re.search(pattern, xml_text)
        if match and match.group(1) != expected_value_str:
            raise AssertionError(
                f'{case_name} English Switch Key mismatch in {root_path}: '
                f'expected={expected_value}, actual={match.group(1)}'
            )

    print(f'[PASS] {case_name}')


def main() -> int:
    generator = UnattendGenerator(data_dir=BACKEND_DIR, lang='en')

    boolean_options = [False, True]
    case_count = 0

    for ctrl_space, ctrl, shift, fhw, sto, cloud in product(boolean_options, repeat=6):
        im = {
            'englishSwitchKeyCtrl': ctrl,
            'englishSwitchKeyCtrlSpace': ctrl_space,
            'englishSwitchKeyShift': shift,
            'enableFullHalfWidthSwitchKey': fhw,
            'enableSimplifiedTraditionalOutputSwitch': sto,
            'enableCloudCandidate': cloud,
        }
        case_name = (
            f'input_method_ctrlSpace_{int(ctrl_space)}_ctrl_{int(ctrl)}_shift_{int(shift)}_'
            f'fhw_{int(fhw)}_sto_{int(sto)}_cloud_{int(cloud)}'
        )
        run_case(generator, case_name, im)
        case_count += 1

    print(f'All input method roundtrip tests passed. Total cases: {case_count}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
