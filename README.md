# conan-updater-bgfx 
## conan-center-index updater for bgfx, bx and bimg

This script aims to help consistently update the conan-center-index recipes and definitions for bgfx and it's dependent projects.

## How to use:

1. Install python 3
2. Run `python conan-updater-bgfx.py --conan-center-index-path <your local fork of the conan index>`

### Arguments

| Argument                         | Description                                                                                                               | Default                                               |
|----------------------------------|---------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------|
| --conan-center-index-path <path> | Path to a local clone of your conan-center-index fork                                                                     | None. Will clone conan-center-index to the temp dir.  |
| --temp-dir <dir>                 | A temporary directory where bgfx, bx and bimg can be cloned and downloaded.                                               | A folder named "tmp" next to the script.              |
| --bgfx-sha <sha>                 | Specify a git sha for bgfx. When set this version of bgfx will be used and a matching commit of bx and bimg will be used. | None. The head revision will be used.                 |

Note: in order to contribute to the conan-center-index you need to create and use a fork. Using the default value of `--conan-center-index-path` will clone the conan-center-index repository itself 
(not your fork, magically) so it is useless for contributing back to the index; it may be useful however in testing these scripts.

### Contributing to conan-center-index

Read the [conan contributors guideline](https://github.com/conan-io/conan-center-index/blob/master/CONTRIBUTING.md). This script does not guarantee compliance with guidelines by any means. 
It's just a helper to speed up monotonous work.

# License

conan-updater-bgfx by Jared Thomson is marked with CC0 1.0. To view a copy of this license, visit https://creativecommons.org/publicdomain/zero/1.0/