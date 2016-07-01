# This module provides an interface for girder tests to include data
# files that are hosted externally.  The current standard storage
# location is https://midas3.kitware.com, but any site that supports
# content-addressed URL's can be used.  This module is largely a
# thin wrapper arround the core CMake ExternalData module.
include(ExternalData)

# Private variables
set(_build_data_path "${PROJECT_BINARY_DIR}/data_src")
set(_source_data_path "${PROJECT_SOURCE_DIR}/tests/data")
set(_plugin_rel_data_path "plugin_tests/data")
set(_plugin_build_data_path "${_build_data_path}/plugins")

# set the default mirror
set(ExternalData_URL_TEMPLATES
  "https://midas3.kitware.com/midas/api/rest?method=midas.bitstream.download&checksum=%(hash)&algorithm=%(algo)"
  "https://data.kitware.com/api/v1/file/hashsum/%(algo)/%(hash)/download"
)

# Expose the absolute path to the data file source tree because
# they file paths will need to be provided absolutely otherwise
# CMake will append the wrong prefix:
#  https://github.com/Kitware/CMake/blob/master/Modules/ExternalData.cmake#L564
set(GIRDER_EXTERNAL_DATA_BUILD_PATH
  "${_build_data_path}"
)

# Contains the actual data files after they are downloaded.  These files
# will generally be linked from the data store, so it is unlikely that anyone
# will need to modify the value.
set(GIRDER_EXTERNAL_DATA_ROOT "${PROJECT_BINARY_DIR}/data"
  CACHE STRING "The root directory where external data files will be placed."
)
mark_as_advanced(GIRDER_EXTERNAL_DATA_ROOT)

# Contains the "data store" path for sharing downloaded resources
# between build directories.
set(GIRDER_EXTERNAL_DATA_STORE "${PROJECT_BINARY_DIR}/store"
  CACHE STRING "The location where downloaded files are cached.  Can be shared between build directories."
)

# Set module level variables for ExternalData
set(ExternalData_BINARY_ROOT "${GIRDER_EXTERNAL_DATA_ROOT}")
set(ExternalData_OBJECT_STORES "${GIRDER_EXTERNAL_DATA_STORE}")

# Set the top level file path where data key files are stored.
# This has to be external to the project source directory because
# we need to build the directory tree with key files provided by
# plugins as well.
set(ExternalData_SOURCE_ROOT
  "${_build_data_path}"
)

# Set up the data source directory by copying the main data source
# path into the build.
function(_setup_base_data_path)
  # we rebuild this directory on every cmake invocation to avoid
  # stale files and handling of merging directories.  The overhead
  # should be minimal because it should only contain a series of
  # very small text files.
  if(EXISTS "${_build_data_path}")
    file(REMOVE_RECURSE "${_build_data_path}")
    file(MAKE_DIRECTORY "${_build_data_path}")
  endif()
  file(GLOB _base_data_files "${_source_data_path}/*")
  file(COPY ${_base_data_files} DESTINATION "${_build_data_path}")
endfunction()

# Add a plugin data directory to the root data store.
function(add_plugin_data_path plugin_name plugin_dir)
  set(_plugin_source_data_path "${plugin_dir}/${_plugin_rel_data_path}")
  if(EXISTS "${_plugin_source_data_path}")
    file(MAKE_DIRECTORY "${_plugin_build_data_path}/${plugin_name}")
    file(GLOB _plugin_data_files "${_plugin_source_data_path}/*")
    file(COPY ${_plugin_data_files} DESTINATION "${_plugin_build_data_path}/${plugin_name}")
  endif()
endfunction()

# Adds a new mirror hosting external data.  The argument passed to this
# method should be a url template similar to the default mirror:
# 
#   https://midas3.kitware.com/midas/api/rest?method=midas.bitstream.download&checksum=%(hash)&algorithm=%(algo)
# 
# where "%(algo)" will be replaced by a hashing algorithm such as "md5" or
# "sha512" and "%(hash)" will be the corresponding hash value.
#
# This is provided as a function because in the future we may want to provide
# a custom fetch script to handle things like authentication.
function(add_external_data_mirror url_template)
  list(APPEND ExternalData_URL_TEMPLATES url_template)
endfunction()

# These are wrappers around ExternalData functions that have access to the
# locally scoped variables such as the mirror list and the data source
# root directory.
#   See https://cmake.org/cmake/help/v3.3/module/ExternalData.html#module-functions
function(girder_ExternalData_add_test)
  ExternalData_add_test(${ARGN})
endfunction()

function(girder_ExternalData_add_target)
  ExternalData_add_target(${ARGN})
endfunction()

function(girder_ExternalData_expand_arguments)
  ExternalData_Expand_Arguments(${ARGN})
endfunction()

# Finally call the setup to generate the tree of source files for girder core.
_setup_base_data_path()
