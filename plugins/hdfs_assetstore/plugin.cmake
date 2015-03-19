add_python_test(assetstore PLUGIN hdfs_assetstore)

add_python_style_test(
  python_static_analysis_hdfs_assetstore
  "${PROJECT_SOURCE_DIR}/plugins/hdfs_assetstore/server"
)

add_javascript_style_test(
  hdfs_assetstore
  "${PROJECT_SOURCE_DIR}/plugins/hdfs_assetstore/web_client/js"
)
