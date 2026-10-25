"""Build a standalone executable for the OS this is run on.

    uv run --group build python build.py               # single-file executable
    uv run --group build python build.py --onedir      # folder build (starts faster)
    uv run --group build python build.py --installer   # setup wizard (Windows / macOS)

Output lands in release/, e.g.
    release/StockingScheduler-windows.zip   (contains StockingScheduler.exe)
    release/StockingScheduler-linux.tar.gz
    release/StockingScheduler-macos.zip     (contains Stocking Scheduler.app)
    release/StockingScheduler-Setup-windows.exe      (--installer, needs Inno Setup 6)
    release/StockingScheduler-Setup-macos-arm64.pkg  (--installer)

Installer file names carry no version number so the README can link to
github.com/.../releases/latest/download/<name>; the version is inside them.

PyInstaller can only build for the platform it runs on, so run this on a
Windows PC to get the Windows .exe (or let GitHub Actions build all of them).
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist"
RELEASE = ROOT / "release"
NAME = "StockingScheduler"


def run(cmd: list[str], **kw) -> None:
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True, cwd=ROOT, **kw)


def os_tag() -> str:
    arm = platform.machine().lower() in ("arm64", "aarch64")
    if sys.platform == "darwin":
        return "macos-arm64" if arm else "macos-intel"  # an arm64 app won't run on an Intel Mac
    return {"win32": "windows"}.get(sys.platform, "linux") + ("-arm64" if arm else "")


def app_version() -> str:
    """The release tag when GitHub Actions builds a v* tag (v1.2 -> 1.2), else pyproject's version."""
    if os.environ.get("GITHUB_REF_TYPE") == "tag":
        return os.environ["GITHUB_REF_NAME"].lstrip("vV")
    import tomllib

    return tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]


def find_iscc() -> str | None:
    """Inno Setup's command-line compiler, wherever the Inno Setup 6 installer put it."""
    found = shutil.which("iscc")
    if found:
        return found
    for base in (os.environ.get("ProgramFiles(x86)"), os.environ.get("ProgramFiles"),
                 os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs")):
        if base and (Path(base) / "Inno Setup 6" / "ISCC.exe").exists():
            return str(Path(base) / "Inno Setup 6" / "ISCC.exe")
    return None


def windows_installer(built: Path, version: str) -> Path:
    iscc = find_iscc()
    if iscc is None:
        raise SystemExit("Inno Setup 6 is needed to build the installer: "
                         "winget install JRSoftware.InnoSetup  (or https://jrsoftware.org/isdl.php)")
    RELEASE.mkdir(exist_ok=True)
    run([iscc, f"/DAppVersion={version}", f"/DSourceDir={built}", f"/DOutputDir={RELEASE}",
         str(ROOT / "installer" / "windows" / "StockingScheduler.iss")])
    return RELEASE / f"{NAME}-Setup-windows.exe"


def macos_installer(built: Path, version: str) -> Path:
    """A .pkg that opens the standard macOS Installer wizard and puts the app in /Applications."""
    import plistlib

    src = ROOT / "installer" / "macos"
    work = ROOT / "build" / "pkg"
    shutil.rmtree(work, ignore_errors=True)
    stage = work / "root"
    stage.mkdir(parents=True)
    run(["ditto", str(built), str(stage / built.name)])  # ditto keeps the bundle's links and signature intact

    # Always install into /Applications — by default Installer would instead
    # "upgrade" any stray copy of the app it finds elsewhere on the disk.
    plist = work / "component.plist"
    run(["pkgbuild", "--analyze", "--root", str(stage), str(plist)])
    components = plistlib.loads(plist.read_bytes())
    for c in components:
        c["BundleIsRelocatable"] = False
    plist.write_bytes(plistlib.dumps(components))

    component = f"{NAME}-component.pkg"
    run(["pkgbuild", "--root", str(stage), "--component-plist", str(plist), "--install-location", "/Applications",
         "--identifier", "com.stocking1.scheduler", "--version", version, str(work / component)])

    arch = "arm64" if platform.machine().lower() in ("arm64", "aarch64") else "x86_64"
    layout = (src / "distribution.xml").read_text(encoding="utf-8")
    layout = layout.replace("{VERSION}", version).replace("{ARCH}", arch).replace("{COMPONENT}", component)
    (work / "distribution.xml").write_text(layout, encoding="utf-8")
    resources = work / "resources"
    resources.mkdir()
    for page in ("welcome.html", "conclusion.html"):
        shutil.copy(src / page, resources / page)

    RELEASE.mkdir(exist_ok=True)
    out = RELEASE / f"{NAME}-Setup-{os_tag()}.pkg"
    run(["productbuild", "--distribution", str(work / "distribution.xml"), "--resources", str(resources),
         "--package-path", str(work), str(out)])
    return out


def main() -> int:
    installer = "--installer" in sys.argv
    onedir = "--onedir" in sys.argv or installer  # installed apps start faster as a folder build
    skip_test = "--no-test" in sys.argv
    if installer and sys.platform not in ("win32", "darwin"):
        print("--installer builds the Windows or macOS setup wizard; run it on that OS "
              "(or let GitHub Actions do it).", file=sys.stderr)
        return 2
    version = app_version()

    if not (ROOT / "assets" / "icon.png").exists():
        run([sys.executable, str(ROOT / "make_icon.py")])

    for p in (DIST, ROOT / "build"):
        shutil.rmtree(p, ignore_errors=True)

    env = dict(os.environ, ONEDIR="1" if onedir else "0", APP_VERSION=version)
    run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", str(ROOT / "StockingScheduler.spec")], env=env)

    # What did we get?
    if sys.platform == "darwin":
        built = DIST / "Stocking Scheduler.app"
    elif onedir:
        built = DIST / NAME
    else:
        built = DIST / (NAME + (".exe" if sys.platform == "win32" else ""))
    if not built.exists():
        print(f"Build finished but {built} is missing", file=sys.stderr)
        return 1

    # Launch it once headlessly to make sure it actually starts.
    if not skip_test:
        if sys.platform == "darwin":
            exe = built / "Contents" / "MacOS" / NAME
        elif onedir:
            exe = built / (NAME + (".exe" if sys.platform == "win32" else ""))
        else:
            exe = built
        test_env = dict(os.environ, STOCKING_SCHEDULER_DATA=str(ROOT / "build" / "smoke-data"))
        if sys.platform != "win32":
            test_env["QT_QPA_PLATFORM"] = "offscreen"
        print("+ smoke test:", exe, flush=True)
        subprocess.run([str(exe), "--smoke-test"], check=True, env=test_env, timeout=120)
        print("  smoke test passed")

    if installer:
        out = windows_installer(built, version) if sys.platform == "win32" else macos_installer(built, version)
        print(f"\nDone: {out}  ({out.stat().st_size / 1_000_000:.0f} MB)")
        return 0

    # Package for handing out.
    RELEASE.mkdir(exist_ok=True)
    tag = os_tag()
    readme = ROOT / "RUNNING.txt"
    if sys.platform == "win32" or sys.platform == "darwin":
        out = RELEASE / f"{NAME}-{tag}.zip"
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
            if built.is_dir():
                for f in built.rglob("*"):
                    if f.is_file():
                        z.write(f, f.relative_to(DIST))
            else:
                z.write(built, built.name)
            if readme.exists():
                z.write(readme, readme.name)
    else:
        out = RELEASE / f"{NAME}-{tag}.tar.gz"
        with tarfile.open(out, "w:gz") as t:
            t.add(built, arcname=built.name)
            if readme.exists():
                t.add(readme, arcname=readme.name)
    size = out.stat().st_size / 1_000_000
    print(f"\nDone: {out}  ({size:.0f} MB)")
    print(f"Executable: {built}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
