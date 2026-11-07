#!/usr/bin/env bash
# Build the physical-iOS Dawn static library without a builder home path.
# The pinned encounter/dawn-build archive embeds /Users/runner/work/dawn-build.
set -euo pipefail

repo_root="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
if [[ "$(uname -s)" != "Darwin" || "$(uname -m)" != "arm64" ]]; then
  echo "ERROR: Dawn's iOS device package requires arm64 macOS" >&2
  exit 1
fi

dawn_commit="13abc3bc8ea2d3c2050f9e77a12d012108ceee24"
dawn_source_sha256="713bea5b92d4f6c5175752fd7cbf1c3c5ce36598ff5dd98685d8a1216614ebba"
source_archive="${repo_root}/build/dependency-cache/dawn-${dawn_commit}.tar.gz"
source_dir="${repo_root}/build/dawn-ios-device-source"
build_dir="${repo_root}/build/dawn-ios-device-build"
install_dir="${repo_root}/build/dawn-ios-device-install"
host_build_dir="${repo_root}/build/dawn-host-protoc-build"
package_path="${repo_root}/build/dependency-cache/dawn-ios-device-arm64-kartpad.tar.gz"
path_map_flags="-ffile-prefix-map=${source_dir}=Dawn -fmacro-prefix-map=${source_dir}=Dawn -ffile-prefix-map=${build_dir}=DawnBuild -fmacro-prefix-map=${build_dir}=DawnBuild -ffile-prefix-map=${repo_root}=KartPad -fmacro-prefix-map=${repo_root}=KartPad"

mkdir -p "$(dirname "${source_archive}")"
if [[ ! -f "${source_archive}" ]]; then
  curl --fail --location --silent --show-error \
    "https://github.com/google/dawn/archive/${dawn_commit}.tar.gz" \
    -o "${source_archive}"
fi
if [[ "$(shasum -a 256 "${source_archive}" | awk '{print $1}')" != "${dawn_source_sha256}" ]]; then
  echo "ERROR: Dawn source archive hash mismatch" >&2
  exit 1
fi
if [[ ! -f "${source_dir}/CMakeLists.txt" ]]; then
  mkdir -p "${source_dir}"
  tar -xzf "${source_archive}" --strip-components=1 -C "${source_dir}"
fi
if [[ ! -x "${host_build_dir}/protoc" ]]; then
  cmake -S "${source_dir}" -B "${host_build_dir}" -G Ninja \
    -C "${source_dir}/.github/workflows/dawn-ci.cmake" \
    -C "${repo_root}/cmake/dawn-kartpad-ci.cmake" \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_C_FLAGS_RELEASE="-O3 -DNDEBUG ${path_map_flags}" \
    -DCMAKE_CXX_FLAGS_RELEASE="-O3 -DNDEBUG ${path_map_flags}"
  cmake --build "${host_build_dir}" --target protoc --parallel 4
fi

cmake -S "${source_dir}" -B "${build_dir}" -G Ninja \
  -C "${source_dir}/.github/workflows/dawn-ci.cmake" \
  -C "${repo_root}/cmake/dawn-kartpad-ci.cmake" \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_SYSTEM_NAME=iOS \
  -DCMAKE_OSX_SYSROOT=iphoneos \
  -DCMAKE_OSX_ARCHITECTURES=arm64 \
  -DCMAKE_OSX_DEPLOYMENT_TARGET=16.0 \
  -DCMAKE_SYSTEM_PROCESSOR=arm64 \
  -DCMAKE_C_FLAGS_RELEASE="-O3 -DNDEBUG ${path_map_flags}" \
  -DCMAKE_CXX_FLAGS_RELEASE="-O3 -DNDEBUG ${path_map_flags}" \
  -DCMAKE_OBJC_FLAGS_RELEASE="-O3 -DNDEBUG ${path_map_flags}" \
  -DCMAKE_OBJCXX_FLAGS_RELEASE="-O3 -DNDEBUG ${path_map_flags}" \
  -DWITH_PROTOC="${host_build_dir}/protoc"
cmake --build "${build_dir}" --parallel 4
cmake --install "${build_dir}" --prefix "${install_dir}"
test -f "${install_dir}/lib/libwebgpu_dawn.a"
test -f "${install_dir}/lib/cmake/Dawn/DawnConfig.cmake"
python3 "${repo_root}/scripts/check_private_build_paths.py" \
  "${install_dir}/lib/libwebgpu_dawn.a"
ZERO_AR_DATE=1 ranlib "${install_dir}/lib/libwebgpu_dawn.a"
python3 "${repo_root}/scripts/check_private_build_paths.py" \
  "${install_dir}/lib/libwebgpu_dawn.a"
find "${install_dir}" -exec touch -h -t 198001010000 {} +
mkdir -p "$(dirname "${package_path}")"
(
  cd "${install_dir}"
  find . -print | LC_ALL=C sort |
    COPYFILE_DISABLE=1 tar -cf - --no-recursion --uid 0 --gid 0 \
      --uname root --gname root --format=ustar -T -
) | gzip -n -9 > "${package_path}"
python3 "${repo_root}/scripts/check_private_build_paths.py" \
  --tar-member libwebgpu_dawn.a "${package_path}"
echo "Dawn iOS device package without private user paths: ${package_path}"
shasum -a 256 "${package_path}"
