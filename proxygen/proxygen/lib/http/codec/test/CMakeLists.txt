# Copyright (c) Facebook, Inc. and its affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

if(NOT BUILD_TESTS)
    return()
endif()

add_library(codectestutils TestUtils.cpp)
target_include_directories(
    codectestutils PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}>
    ${LIBGMOCK_INCLUDE_DIR}
    ${LIBGTEST_INCLUDE_DIR}
)
target_compile_options(
    codectestutils PRIVATE
    ${_PROXYGEN_COMMON_COMPILE_OPTIONS}
)
target_link_libraries(codectestutils PUBLIC proxygen)

proxygen_add_test(TARGET CodecTests
  SOURCES
    CodecUtilTests.cpp
    DefaultHTTPCodecFactoryTest.cpp
    FilterTests.cpp
    HTTP1xCodecTest.cpp
    HTTP2CodecTest.cpp
    HTTP2FramerTest.cpp
    SPDYCodecTest.cpp
  DEPENDS
    codectestutils
    proxygen
    testmain
)

if (BUILD_QUIC)
  proxygen_add_test(TARGET HQFramerTests
    SOURCES
      HQFramerTest.cpp
    DEPENDS
      codectestutils
      proxygen
      testmain
      mvfst::mvfst_codec_types
  )

  proxygen_add_test(TARGET HQCodecTests
    SOURCES
      HQCodecTest.cpp
      HQMultiCodecTest.cpp
    DEPENDS
      codectestutils
      proxygen
      testmain
      mvfst::mvfst_codec_types
      mvfst::mvfst_state_machine
  )
endif()
