import os
import sys
import shutil
import tempfile
import yaml
from pathlib import Path
from importlib.abc import MetaPathFinder

_DEBUG = os.environ.get('ESP_BMGR_DEBUG', '0') == '1'
_MAIN_EXECUTED = False

# Constants
MANIFEST_NAMES = ["idf_component.yml", "idf_component.yaml"]
BMGR_KEYS = ["espressif/esp_board_manager", "esp_board_manager"]


def _find_manifest_file(project_path: Path) -> Path | None:
    """Find manifest file in main directory."""
    for name in MANIFEST_NAMES:
        if (path := project_path / "main" / name).exists():
            return path
    return None


def _load_dependencies(manifest_path: Path) -> dict:
    """Load dependencies from manifest file."""
    try:
        with open(manifest_path, 'r', encoding='utf-8') as f:
            return (yaml.safe_load(f) or {}).get('dependencies', {})
    except Exception:
        return {}


def _find_bmgr_dependency(deps: dict) -> tuple[str, dict] | None:
    """Find board manager dependency."""
    for key in BMGR_KEYS:
        if key in deps:
            return (key, deps[key])
    return None


def _download_bmgr_component(project_path: str) -> None:
    """从项目 main 目录下的 manifest 文件中提取 esp_board_manager 依赖并下载"""
    try:
        from idf_component_manager.dependencies import download_project_dependencies
        from idf_component_tools.manager import ManifestManager
        from idf_component_tools.utils import ProjectRequirements
    except ImportError:
        download_project_dependencies = ManifestManager = ProjectRequirements = None
    if not all([download_project_dependencies, ManifestManager, ProjectRequirements]):
        print("Warning: idf-component-manager is not available, cannot download component")
        return
    
    proj = Path(project_path)
    managed_path = proj / "managed_components"
    lock_path = proj / "dependencies.lock"
    
    manifest_path = _find_manifest_file(proj)
    if not manifest_path:
        print(f"Warning: Manifest file not found at {proj / 'main'}/idf_component.yml or {proj / 'main'}/idf_component.yaml")
        return
    
    managed_path.mkdir(parents=True, exist_ok=True)
    print(f"Start downloading esp_board_manager component to {managed_path}")

    try:
        deps = _load_dependencies(manifest_path)
        bmgr_result = _find_bmgr_dependency(deps)
        if not bmgr_result:
            print(f"Warning: esp_board_manager dependency not found in {manifest_path}")
            return
        
        bmgr_key, bmgr_dep = bmgr_result
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_manifest = Path(temp_dir) / "idf_component.yml"
            with open(temp_manifest, 'w', encoding='utf-8') as f:
                yaml.dump({'dependencies': {bmgr_key: bmgr_dep}}, f)
            
            manifest = ManifestManager(str(temp_dir), "temp").load()
            download_project_dependencies(
                ProjectRequirements([manifest]),
                str(lock_path),
                str(managed_path),
            )
            print(f"Successfully downloaded esp_board_manager component to {managed_path}")
    except Exception as e:
        print(f"Error downloading esp_board_manager component: {e}")
        raise

def _is_project_path(project_path: Path) -> bool:
    cmake_file = project_path / "CMakeLists.txt"
    if not cmake_file.exists():
        return False
    with open(cmake_file, "r") as f:
        return "project.cmake" in f.read()

def _is_bmgr_component(path: Path) -> bool:
    """Check if path is a board manager component directory."""
    return path.is_dir() and ((path / "idf_ext.py").exists() or (path / "idf_component.yml").exists())


def _find_local_bmgr(project_path: Path) -> Path | None:
    """Find local board manager component."""
    # Check override_path in manifest
    if manifest_path := _find_manifest_file(project_path):
        deps = _load_dependencies(manifest_path)
        if result := _find_bmgr_dependency(deps):
            _, bmgr_dep = result
            if isinstance(bmgr_dep, dict) and (override := bmgr_dep.get("override_path")):
                if Path(override).is_absolute():
                    path = Path(override)
                elif override.startswith("../"):
                    path = (project_path / "main" / override).resolve()
                elif override.startswith("components/"):
                    path = project_path / override
                else:
                    path = project_path / "components" / override
                if _is_bmgr_component(path := path.resolve()):
                    if _DEBUG:
                        print(f"[esp_bmgr_py] Found local board manager via override_path: {path}")
                    return path
    
    # Check components directory
    components = project_path / "components"
    if components.exists():
        for name in ["esp_board_manager", "espressif__esp_board_manager"]:
            if _is_bmgr_component(path := components / name):
                if _DEBUG:
                    print(f"[esp_bmgr_py] Found local board manager in components: {path}")
                return path.resolve()
    return None

def _set_idf_extra_actions_path(actions_path: str) -> None:
    paths = [p.strip() for p in os.environ.get('IDF_EXTRA_ACTIONS_PATH', '').split(';') if p.strip()]
    if actions_path not in paths:
        paths.append(actions_path)
        os.environ['IDF_EXTRA_ACTIONS_PATH'] = ';'.join(paths)
        if _DEBUG:
            print(f"[esp_bmgr_py] Set IDF_EXTRA_ACTIONS_PATH: {os.environ['IDF_EXTRA_ACTIONS_PATH']}")

def _main():
    """Main function to setup board manager paths."""
    global _MAIN_EXECUTED
    
    # Only execute once
    if _MAIN_EXECUTED:
        return
    _MAIN_EXECUTED = True
    
    if not sys.argv or not sys.argv[0].endswith("idf.py"):
        return

    if _DEBUG:
        print(f"[esp_bmgr_py] Module loaded, argv: {sys.argv}")

    project_path = Path(os.getcwd())
    if "set-target" in sys.argv:
        # remove gen_bmgr_codes directory if set-target is called
        shutil.rmtree(project_path / "components" / "gen_bmgr_codes", ignore_errors=True)
        return

    import logging
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    if _DEBUG:
        print(f"[esp_bmgr_py] Project path: {project_path}")
    if not _is_project_path(project_path):
        return
    
    # Check local component first
    if local_path := _find_local_bmgr(project_path):
        _set_idf_extra_actions_path(str(local_path))
        return
    
    bmgr_path = project_path / "managed_components" / "espressif__esp_board_manager"
    if len(sys.argv) > 2 and sys.argv[1] == "gen-bmgr-config":
        # Download and use managed component
        if not bmgr_path.exists() and os.getenv("_IDF_EXT_UPDATING_DEPS") != "1":
            os.environ["_IDF_EXT_UPDATING_DEPS"] = "1"
            os.environ.setdefault("IDF_TARGET", "esp32")
            shutil.rmtree(project_path / "components" / "gen_bmgr_codes", ignore_errors=True)
            try:
                _download_bmgr_component(project_path)
            finally:
                os.environ.pop("_IDF_EXT_UPDATING_DEPS", None)
    
    if bmgr_path.exists():
        _set_idf_extra_actions_path(str(bmgr_path.resolve()))


class IdfPyActionsHook(MetaPathFinder):
    """Import hook to execute _main() when idf_py_actions is imported."""
    
    def find_spec(self, name, path, target=None):
        # Only intercept idf_py_actions imports
        if name == 'idf_py_actions':
            # Execute _main() when idf_py_actions is being imported
            # At this point, logging system should be initialized
            _main()
            # Return None to let Python's default import mechanism handle it
            return None
        return None


# Register the import hook
# Insert at the beginning so it's checked first
if IdfPyActionsHook not in sys.meta_path:
    sys.meta_path.insert(0, IdfPyActionsHook())
