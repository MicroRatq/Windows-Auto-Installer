from __future__ import annotations

from pathlib import Path
from typing import Any

from deployment_build import IsoAddItem, collect_directory_iso_additions


def find_builtin_virtio_driver_iso(project_root: Path) -> Path:
    driver_dir = project_root / "data" / "drivers"
    candidates = sorted(driver_dir.glob("virtio-win-*.iso"))
    if not candidates:
        raise FileNotFoundError(
            f"No built-in VirtIO driver ISO found under {driver_dir}. "
            "Place a virtio-win-*.iso file in data/drivers/."
        )
    if len(candidates) > 1:
        raise ValueError(
            "Multiple built-in VirtIO driver ISOs found. "
            f"Keep only one under {driver_dir}: {', '.join(path.name for path in candidates)}"
        )
    return candidates[0]


def extract_iso_directory(reader: Any, source_dir: str, output_dir: Path) -> int:
    output_dir.mkdir(parents=True, exist_ok=True)
    extracted_files = 0

    for entry in reader.list_directory(source_dir):
        if entry in (".", ".."):
            continue

        source_path = f"{source_dir.rstrip('/')}/{entry}"
        target_path = output_dir / entry

        if reader.file_exists(source_path):
            reader.extract_file(source_path, str(target_path))
            extracted_files += 1
            continue

        extracted_files += extract_iso_directory(reader, source_path, target_path)

    return extracted_files


def resolve_builtin_virtio_iso_additions(
    template_iso_path: str,
    configuration: Any,
    work_dir: Path,
    project_root: Path,
) -> list[IsoAddItem]:
    from iso_reader import ISOReader
    from unattend_generator import GeneratePESettings, ProcessorArchitecture

    pe_settings = getattr(configuration, "pe_settings", None)
    if not isinstance(pe_settings, GeneratePESettings) or not pe_settings.inject_virtio_storage_drivers:
        return []

    if ProcessorArchitecture.amd64 not in getattr(configuration, "processor_architectures", {ProcessorArchitecture.amd64}):
        raise ValueError("Built-in VirtIO PE driver injection currently supports amd64 only.")

    driver_iso_path = find_builtin_virtio_driver_iso(project_root)
    template_iso_name = Path(template_iso_path).name.lower()
    preferred_driver_dirs = [
        ("/vioscsi/w11/amd64", "virtio/vioscsi/w11/amd64"),
        ("/vioscsi/w10/amd64", "virtio/vioscsi/w10/amd64"),
        ("/vioscsi/2k25/amd64", "virtio/vioscsi/2k25/amd64"),
        ("/vioscsi/2k22/amd64", "virtio/vioscsi/2k22/amd64"),
    ]
    if "win10" in template_iso_name:
        preferred_driver_dirs = [preferred_driver_dirs[1], preferred_driver_dirs[0], *preferred_driver_dirs[2:]]

    with ISOReader(str(driver_iso_path)) as reader:
        checked_dirs: list[str] = []
        for source_dir, relative_target_dir in preferred_driver_dirs:
            checked_dirs.append(source_dir)
            try:
                dir_entries = [entry for entry in reader.list_directory(source_dir) if entry not in (".", "..")]
            except Exception:
                continue

            if not any(entry.lower().endswith(".inf") for entry in dir_entries):
                continue

            extract_root = work_dir / "virtio_iso_extract"
            extracted_dir = extract_root / Path(relative_target_dir)
            extracted_files = extract_iso_directory(reader, source_dir, extracted_dir)
            if extracted_files == 0:
                continue
            if not any(path.is_file() and path.suffix.lower() == ".inf" for path in extracted_dir.rglob("*")):
                continue
            return collect_directory_iso_additions(extracted_dir, f"/$WinPEDriver$/{relative_target_dir}")

    raise FileNotFoundError(
        f"Could not find a supported vioscsi driver directory in {driver_iso_path}. "
        f"Checked: {', '.join(checked_dirs)}"
    )
