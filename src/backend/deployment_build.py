from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class WimAddItem:
    source_path: str
    target_path: str


@dataclass(frozen=True)
class IsoAddItem:
    source_path: str
    target_path: str


@dataclass(frozen=True)
class IsoReplaceItem:
    source_path: str
    target_path: str


@dataclass
class DeploymentBuildPlan:
    wim_additions: list[WimAddItem] = field(default_factory=list)
    iso_additions: list[IsoAddItem] = field(default_factory=list)
    iso_replacements: list[IsoReplaceItem] = field(default_factory=list)


def build_installer_payload(project_root: Path, work_dir: Path) -> Path:
    payload_root = work_dir / "installer_payload" / "WindowsAutoInstaller"
    payload_root.mkdir(parents=True, exist_ok=True)

    runtime_sources = [
        (project_root / "src" / "backend", payload_root / "backend"),
        (project_root / "src" / "shared", payload_root / "shared"),
        (project_root / "src" / "frontend" / "dist", payload_root / "frontend" / "dist"),
        (project_root / "src" / "frontend" / "electron", payload_root / "frontend" / "electron"),
    ]

    copied_any = False
    ignore_patterns = shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo", "node_modules")

    for source_path, target_path in runtime_sources:
        if source_path.exists():
            shutil.copytree(source_path, target_path, dirs_exist_ok=True, ignore=ignore_patterns)
            copied_any = True

    frontend_package = project_root / "src" / "frontend" / "package.json"
    if frontend_package.exists():
        (payload_root / "frontend").mkdir(parents=True, exist_ok=True)
        shutil.copy2(frontend_package, payload_root / "frontend" / "package.json")
        copied_any = True

    if not copied_any:
        raise FileNotFoundError("No installer runtime payload was found to integrate into WIM")

    return payload_root


def collect_directory_iso_additions(local_root: Path, iso_root: str) -> list[IsoAddItem]:
    normalized_iso_root = "/" + iso_root.strip("/")
    additions: list[IsoAddItem] = []

    for local_path in sorted(local_root.rglob("*")):
        if not local_path.is_file():
            continue
        relative_path = local_path.relative_to(local_root).as_posix()
        additions.append(IsoAddItem(str(local_path), f"{normalized_iso_root}/{relative_path}"))

    return additions


def build_deployment_plan(
    template_iso_path: str,
    configuration: Any,
    file_mappings: list[tuple[str, str]],
    integrate_installer: bool,
    work_dir: Path,
    project_root: Path,
    autounattend_xml_bytes: bytes,
    install_image_iso_path: str,
    updated_wim_path: Path,
) -> DeploymentBuildPlan:
    plan = DeploymentBuildPlan(
        wim_additions=[WimAddItem(source_path, target_path) for source_path, target_path in file_mappings],
        iso_replacements=[
            IsoReplaceItem(str(updated_wim_path), install_image_iso_path),
        ],
    )

    if integrate_installer:
        payload_root = build_installer_payload(project_root, work_dir)
        plan.wim_additions.append(
            WimAddItem(str(payload_root), "\\Windows\\Setup\\Scripts\\WindowsAutoInstaller")
        )

    autounattend_xml_path = work_dir / "autounattend.xml"
    autounattend_xml_path.write_bytes(autounattend_xml_bytes)
    plan.iso_replacements.append(IsoReplaceItem(str(autounattend_xml_path), "/autounattend.xml"))

    from deployment_assets import resolve_builtin_virtio_iso_additions

    plan.iso_additions.extend(
        resolve_builtin_virtio_iso_additions(template_iso_path, configuration, work_dir, project_root)
    )
    return plan


def apply_wim_plan(handler: Any, image_index: int, plan: DeploymentBuildPlan) -> None:
    add_files = [(item.source_path, item.target_path) for item in plan.wim_additions]
    if add_files:
        handler.update_image(image_index, add_files=add_files)


def apply_iso_plan(writer: Any, plan: DeploymentBuildPlan) -> None:
    for item in plan.iso_replacements:
        writer.replace_file(item.target_path, item.source_path)
    for item in plan.iso_additions:
        writer.add_file(item.source_path, item.target_path)
