# The upstream user-config workflow loads this repository as a ZMK module.
if(CONFIG_ZMK_RGB_UNDERGLOW)
  zephyr_library()
  zephyr_library_sources(src/led_calibration.c)
  zephyr_library_sources(src/indicator_layers.c)
  zephyr_include_directories(${APPLICATION_SOURCE_DIR}/include)
endif()
