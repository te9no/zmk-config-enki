if(CONFIG_SHIELD_ENKI)
  zephyr_library()
  zephyr_library_include_directories(${ZEPHYR_LVGL_MODULE_DIR})

  set(ENKI_NICE_VIEW_DIR ${CMAKE_CURRENT_LIST_DIR}/src/nice_view)
  zephyr_library_include_directories(${ENKI_NICE_VIEW_DIR})

  zephyr_library_sources(src/enki_status_screen.c)

  # Assets
  zephyr_library_sources(${ENKI_NICE_VIEW_DIR}/assets/images.c)
  zephyr_library_sources(${ENKI_NICE_VIEW_DIR}/assets/crystal.c)
  zephyr_library_sources(${ENKI_NICE_VIEW_DIR}/assets/pokemon.c)
  zephyr_library_sources(${ENKI_NICE_VIEW_DIR}/assets/vim.c)
  zephyr_library_sources(${ENKI_NICE_VIEW_DIR}/assets/vip_marcos.c)
  zephyr_library_sources(${ENKI_NICE_VIEW_DIR}/assets/pixel_operator_mono.c)
  zephyr_library_sources(${ENKI_NICE_VIEW_DIR}/assets/pixel_operator_mono_8.c)
  zephyr_library_sources(${ENKI_NICE_VIEW_DIR}/assets/pixel_operator_mono_12.c)

  # Widgets
  zephyr_library_sources(${ENKI_NICE_VIEW_DIR}/widgets/animation.c)
  zephyr_library_sources(${ENKI_NICE_VIEW_DIR}/widgets/battery.c)
  zephyr_library_sources(${ENKI_NICE_VIEW_DIR}/widgets/output.c)
  zephyr_library_sources(${ENKI_NICE_VIEW_DIR}/widgets/screen_peripheral.c)
  zephyr_library_sources(${ENKI_NICE_VIEW_DIR}/widgets/util.c)
endif()
