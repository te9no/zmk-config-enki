if(CONFIG_SHIELD_ENKI)
  zephyr_library()
  zephyr_library_include_directories(${ZEPHYR_LVGL_MODULE_DIR})

  zephyr_library_sources(
    src/backlight_control.c
    src/touch_gestures.c
    src/key_counter_screen.c
  )
endif()
