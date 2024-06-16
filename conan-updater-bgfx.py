import os
import re
import subprocess
import hashlib
import yaml
from pathlib import Path
import argparse

def run_command(command, cwd=None):
    result = subprocess.run(command, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        raise Exception(f"Command {' '.join(command)} failed with error: {result.stderr}")
    return result.stdout.strip()

def get_commit_timestamp(clone_path):
    result = subprocess.run(['git', 'log', '-1', '--format=%ct'], cwd=clone_path, capture_output=True, text=True)
    return result.stdout.strip()

def get_commit_hash_at_timestamp(clone_path, timestamp):
    result = subprocess.run(['git', 'log', '-1', '--format=%H', '--before=' + timestamp], cwd=clone_path, capture_output=True, text=True)
    return result.stdout.strip()

def clone_or_pull(repo_url, clone_path, sha=None):
    if os.path.exists(clone_path):
        run_command(['git', 'pull', repo_url], cwd=clone_path)
    else:
        run_command(['git', 'clone', repo_url, clone_path])
    
    if sha:
        run_command(['git', 'checkout', sha], cwd=clone_path)

def get_revision_count(repo_dir):
    return run_command(["git", "rev-list", "--count", "HEAD"], cwd=repo_dir)

def get_genie_version(bx_dir, bgfx_dir):
    genie_path = Path(bx_dir) / "tools" / "bin" / "windows" / "genie.exe"
    bgfx_scripts_path = Path(bgfx_dir) / "scripts"
    genie_version_output = run_command([str(genie_path), "version"], cwd=bgfx_scripts_path)
    output_lines = genie_version_output.strip().split('\n')
    for line in output_lines:
        if line.count('.') == 2 and all(part.isdigit() for part in line.split('.')):
            return line.strip()    
    raise Exception("Version format not found in the command output")

def download_file(url, dest):
    if not os.path.exists(dest):
        result = subprocess.run(["curl", "-L", url, "-o", dest], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode != 0:
            raise Exception(f"Failed to download {url} with error: {result.stderr}")

def calculate_sha256(file_path):
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def update_yaml_list(file_path, list_name, new_data):
    with open(file_path, "r") as f:
        data = yaml.safe_load(f)
    # append to the beginning of the list
    data[list_name] = {**new_data, **data[list_name]}
    with open(file_path, "w") as f:
        yaml.safe_dump(data, f)

# Opens the conanfile.py to set version mappings in the _bx_version and _bimg_version properties
# It will first check to see if the bgfx version is mapped. Note that it will not handle commented out code.
def update_bgfx_conanfile(repo_dir, bgfx_version, bx_version, bimg_version):
    conanfile_path = Path(repo_dir) / "recipes" / "bgfx" / "all" / "conanfile.py"

    with open(conanfile_path, "r") as f:
        conanfile_content = f.read()

    bx_version_pattern = r"(def _bx_version\(self\):\s*return\s*\{)"
    bx_version_match = re.search(bx_version_pattern, conanfile_content)

    # Update _bx_version
    if bx_version_match:
        bx_version_start = bx_version_match.end()
        bx_version_entry_pattern = re.compile(rf'"{bgfx_version}":\s*"[^\"]*"')
        bx_version_entry_match = bx_version_entry_pattern.search(conanfile_content, bx_version_start)

        if bx_version_entry_match:
            entry_start, entry_end = bx_version_entry_match.span()
            conanfile_content = conanfile_content[:entry_start] + f'"{bgfx_version}": "{bx_version}"' + conanfile_content[entry_end:]
        else:
            conanfile_content = conanfile_content[:bx_version_start] + f'\n            "{bgfx_version}": "{bx_version}",' + conanfile_content[bx_version_start:]

    bimg_version_pattern = r"(def _bimg_version\(self\):\s*return\s*\{)"
    bimg_version_match = re.search(bimg_version_pattern, conanfile_content)
    
    # Update _bimg_version
    if bimg_version_match:
        bimg_version_start = bimg_version_match.end()
        bimg_version_entry_pattern = re.compile(rf'"{bgfx_version}":\s*"[^\"]*"?')
        bimg_version_entry_match = bimg_version_entry_pattern.search(conanfile_content, bimg_version_start)

        if bimg_version_entry_match:
            entry_start, entry_end = bimg_version_entry_match.span()
            conanfile_content = conanfile_content[:entry_start] + f'"{bgfx_version}": "{bimg_version}"' + conanfile_content[entry_end:]
        else:
            conanfile_content = conanfile_content[:bimg_version_start] + f'\n            "{bgfx_version}": "{bimg_version}",' + conanfile_content[bimg_version_start:]

    with open(conanfile_path, "w") as f:
        f.write(conanfile_content)

def main():
    parser = argparse.ArgumentParser(description="Update conan-center-index for bx, bimg, and bgfx.")
    script_dir = Path(__file__).resolve().parent
    parser.add_argument("--conan-center-index-path", type=str, default=str(script_dir / "tmp" / "conan-center-index"),
                        help="Path to the conan-center-index repository.")
    parser.add_argument("--temp-dir", type=str, default=str(script_dir / "tmp"),
                        help="Path to the temporary directory.")
    parser.add_argument("--bgfx-sha", type=str, default=None,
                        help="SHA of the bgfx commit to use.")
    args = parser.parse_args()

    temp_dir = Path(args.temp_dir)
    temp_dir.mkdir(parents=True, exist_ok=True)

    bx_dir = temp_dir / "bx"
    bimg_dir = temp_dir / "bimg"
    bgfx_dir = temp_dir / "bgfx"

    clone_or_pull("https://github.com/bkaradzic/bx.git", bx_dir)
    clone_or_pull("https://github.com/bkaradzic/bimg.git", bimg_dir)
    if os.path.exists(bgfx_dir):
        run_command(['git', 'checkout', '--', 'src/version.h'], cwd=bgfx_dir)
    clone_or_pull("https://github.com/bkaradzic/bgfx.git", bgfx_dir, args.bgfx_sha)

    if args.bgfx_sha:
        bgfx_timestamp = get_commit_timestamp(bgfx_dir)
        bx_sha = get_commit_hash_at_timestamp(bx_dir, bgfx_timestamp)
        bimg_sha = get_commit_hash_at_timestamp(bimg_dir, bgfx_timestamp)

        run_command(['git', 'checkout', bx_sha], cwd=bx_dir)
        run_command(['git', 'checkout', bimg_sha], cwd=bimg_dir)

    bx_version = get_revision_count(bx_dir)
    bimg_version = get_revision_count(bimg_dir)
    bgfx_version = get_genie_version(bx_dir=bx_dir, bgfx_dir=bgfx_dir)

    bx_commit = run_command(["git", "rev-parse", "HEAD"], cwd=bx_dir)
    bimg_commit = run_command(["git", "rev-parse", "HEAD"], cwd=bimg_dir)
    bgfx_commit = run_command(["git", "rev-parse", "HEAD"], cwd=bgfx_dir)

    bx_url = f"https://github.com/bkaradzic/bx/archive/{bx_commit}.tar.gz"
    bimg_url = f"https://github.com/bkaradzic/bimg/archive/{bimg_commit}.tar.gz"
    bgfx_url = f"https://github.com/bkaradzic/bgfx/archive/{bgfx_commit}.tar.gz"

    bx_tar = temp_dir / f"bx.{bx_commit}.tar.gz"
    bimg_tar = temp_dir / f"bimg.{bimg_commit}tar.gz"
    bgfx_tar = temp_dir / f"bgfx.{bgfx_commit}tar.gz"

    download_file(bx_url, bx_tar)
    download_file(bimg_url, bimg_tar)
    download_file(bgfx_url, bgfx_tar)

    bx_sha256 = calculate_sha256(bx_tar)
    bimg_sha256 = calculate_sha256(bimg_tar)
    bgfx_sha256 = calculate_sha256(bgfx_tar)

    conan_config_path_bx = Path(args.conan_center_index_path) / "recipes" / "bx" / "config.yml"
    conan_config_path_bimg = Path(args.conan_center_index_path) / "recipes" / "bimg" / "config.yml"
    conan_config_path_bgfx = Path(args.conan_center_index_path) / "recipes" / "bgfx" / "config.yml"

    conan_data_path_bx = Path(args.conan_center_index_path) / "recipes" / "bx" / "all" / "conandata.yml"
    conan_data_path_bimg = Path(args.conan_center_index_path) / "recipes" / "bimg" / "all" / "conandata.yml"
    conan_data_path_bgfx = Path(args.conan_center_index_path) / "recipes" / "bgfx" / "all" / "conandata.yml"

    update_yaml_list(file_path=conan_config_path_bx, list_name="versions", new_data={f"{bx_version}": {"folder": "all"}})
    update_yaml_list(file_path=conan_config_path_bimg, list_name="versions", new_data={f"{bimg_version}": {"folder": "all"}})
    update_yaml_list(file_path=conan_config_path_bgfx, list_name="versions", new_data={f"{bgfx_version}": {"folder": "all"}})

    update_yaml_list(file_path=conan_data_path_bx, list_name="sources", new_data={f"{bx_version}": {"url": bx_url, "sha256": bx_sha256}})
    update_yaml_list(file_path=conan_data_path_bimg, list_name="sources", new_data={f"{bimg_version}": {"url": bimg_url, "sha256": bimg_sha256}})
    update_yaml_list(file_path=conan_data_path_bgfx, list_name="sources", new_data={f"{bgfx_version}": {"url": bgfx_url, "sha256": bgfx_sha256}})

    update_bgfx_conanfile(args.conan_center_index_path, bgfx_version, bx_version, bimg_version)

if __name__ == "__main__":
    main()
