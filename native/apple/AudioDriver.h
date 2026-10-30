// GPL-2.0: native output for the unchanged OpenTTD mixer.
#pragma once
#include <cstdint>
#include <string>

struct NativeAudioStatus {
 bool available = false;
 bool running = false;
 bool background = false;
 bool interrupted = false;
 uint64_t callbacks = 0;
 uint64_t frames = 0;
 uint64_t non_silent_buffers = 0;
 uint32_t peak = 0;
 int32_t last_error = 0;
 uint32_t output_generation = 0;
};

// These functions are called only by the engine owner. AudioQueue owns its
// serial callback; the original mixer supplies its existing atomic channels.
void NativeAudioSetBackground(bool background);
void NativeAudioHandleInterruption(int event);
void NativeAudioUserActivity();
NativeAudioStatus NativeAudioGetStatus();
void NativeAudioWriteEvidence(const std::string &path);
