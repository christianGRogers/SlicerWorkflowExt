"""Import-safety tests for the DAI Workflow module.

These run WITHOUT 3D Slicer: the Slicer-side dependencies (``slicer``, ``qt``,
``vtk``, ``ctk``, ``DICOMLib``) are replaced with permissive stubs. That is
enough to exercise everything that happens at *import* time -- module-level
code, cross-submodule imports, import cycles, and the bootstrap calls -- which
is where the workflow package's structural bugs live. Real Slicer calls only
happen at run time inside function bodies and are not exercised here.

Run with:  python -m pytest tests/ -q     (or just: python tests/test_package_imports.py)
"""
import ast
import importlib
import os
import sys
import types

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKFLOW_DIR = os.path.join(REPO_ROOT, "DAI_Workflow", "workflow")
MODUALS_DIR = os.path.join(WORKFLOW_DIR, "Moduals")


class _Stub(types.ModuleType):
    """A module whose every attribute access yields a callable no-op object."""

    def __getattr__(self, name):  # noqa: D401
        return _Dummy()


class _Dummy:
    def __getattr__(self, name):
        return _Dummy()

    def __call__(self, *args, **kwargs):
        return _Dummy()


def _install_slicer_stubs():
    for name in ("slicer", "qt", "vtk"):
        sys.modules.setdefault(name, _Stub(name))
    # slicer.util / slicer.i18n / etc. resolve via _Stub.__getattr__ lazily.


def _import_workflow_module():
    _install_slicer_stubs()
    if WORKFLOW_DIR not in sys.path:
        sys.path.insert(0, WORKFLOW_DIR)
    return importlib.import_module("Moduals.workflow_moduals")


def _public_function_names():
    """Function names defined across the _impl submodules (the real API)."""
    impl = os.path.join(MODUALS_DIR, "_impl")
    names = set()
    for fn in os.listdir(impl):
        if not fn.endswith(".py") or fn.startswith("__"):
            continue
        tree = ast.parse(open(os.path.join(impl, fn), encoding="utf-8").read())
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                names.add(node.name)
    return names


def test_package_imports_without_slicer():
    """The facade imports cleanly -- no import cycles, no bootstrap errors."""
    wf = _import_workflow_module()
    assert wf is not None


def test_public_api_is_complete():
    """Every function defined in the _impl submodules is reachable on the facade."""
    wf = _import_workflow_module()
    missing = sorted(n for n in _public_function_names() if not hasattr(wf, n))
    assert not missing, f"functions missing from the facade: {missing}"


def test_known_entry_points_present():
    """A few load-bearing entry points callers depend on must exist."""
    wf = _import_workflow_module()
    for name in (
        "start_with_dicom_data",
        "load_dicom_from_source_file",
        "set_3d_view_background_black",
        "force_collapse_left_panel_on_startup",
    ):
        assert hasattr(wf, name), f"missing entry point: {name}"


if __name__ == "__main__":
    failures = 0
    for fn in (test_package_imports_without_slicer,
               test_public_api_is_complete,
               test_known_entry_points_present):
        try:
            fn()
            print(f"PASS  {fn.__name__}")
        except AssertionError as exc:
            failures += 1
            print(f"FAIL  {fn.__name__}: {exc}")
    sys.exit(1 if failures else 0)
