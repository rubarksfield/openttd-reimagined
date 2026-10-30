// GPL-2.0: Apple output adapter. All sample decoding and mixing stay upstream.
#import <UIKit/UIKit.h>
#import <AVFoundation/AVFoundation.h>
#import <AudioToolbox/AudioToolbox.h>
#include "stdafx.h"
#include "sound/sound_driver.hpp"
#include "mixer.h"
#include "EngineBridge.h"
#include "AudioDriver.h"
#include <array>
#include <atomic>
#include <fstream>

namespace {
constexpr uint32_t kSampleRate = 44100;
constexpr uint32_t kFramesPerBuffer = 1024;
constexpr uint32_t kChannels = 2;
class NativeSoundDriver;
NativeSoundDriver *active_audio = nullptr; // engine owner only
int32_t last_start_error = 0;

class NativeSoundDriver final : public SoundDriver {
 AudioQueueRef queue_ = nullptr;
 std::array<AudioQueueBufferRef, 3> buffers_{};
 std::atomic<bool> stopping_{false};
 std::atomic<uint64_t> callbacks_{0}, frames_{0}, non_silent_{0};
 std::atomic<uint32_t> peak_{0};
 std::atomic<int32_t> error_{0};
 bool background_ = false, interrupted_ = false, interruption_ended_ = false, running_ = false;
 uint32_t output_generation_ = 0;
 __strong id interruption_observer_ = nil;
 __strong id reset_observer_ = nil;
#ifdef OTTD_RUNTIME_EVIDENCE
 std::array<int16_t, kFramesPerBuffer * kChannels> captured_{};
 std::atomic<int> capture_state_{0};
 bool capture_written_ = false;
#endif

 static void Output(void *context, AudioQueueRef queue, AudioQueueBufferRef buffer)
 {
  auto *self = static_cast<NativeSoundDriver *>(context);
  if (self->stopping_.load(std::memory_order_acquire)) return;
  self->callbacks_.fetch_add(1, std::memory_order_relaxed);
  self->FillAndEnqueue(queue, buffer);
 }

 void FillAndEnqueue(AudioQueueRef queue, AudioQueueBufferRef buffer)
 {
  MxMixSamples(buffer->mAudioData, kFramesPerBuffer);
  buffer->mAudioDataByteSize = kFramesPerBuffer * kChannels * sizeof(int16_t);
  auto *samples = static_cast<const int16_t *>(buffer->mAudioData);
  uint32_t peak = 0;
  for (size_t i = 0; i < kFramesPerBuffer * kChannels; ++i) {
   peak = std::max(peak, static_cast<uint32_t>(std::abs(static_cast<int>(samples[i]))));
  }
  frames_.fetch_add(kFramesPerBuffer, std::memory_order_relaxed);
  if (peak != 0) {
   non_silent_.fetch_add(1, std::memory_order_relaxed);
   uint32_t previous = peak_.load(std::memory_order_relaxed);
   while (peak > previous && !peak_.compare_exchange_weak(previous, peak, std::memory_order_relaxed)) {}
#ifdef OTTD_RUNTIME_EVIDENCE
   int expected = 0;
   if (capture_state_.compare_exchange_strong(expected, 1)) {
    std::copy_n(samples, captured_.size(), captured_.begin());
    capture_state_.store(2, std::memory_order_release);
   }
#endif
  }
  OSStatus status = AudioQueueEnqueueBuffer(queue, buffer, 0, nullptr);
  if (status != noErr) error_.store(status, std::memory_order_relaxed);
 }

 bool ActivateSession()
 {
  @autoreleasepool {
  NSError *error = nil;
  AVAudioSession *session = AVAudioSession.sharedInstance;
  // Ambient honours the player's silent switch and coexists with other audio.
  if (![session setCategory:AVAudioSessionCategoryAmbient error:&error] ||
      ![session setActive:YES error:&error]) {
   error_.store(static_cast<int32_t>(error.code), std::memory_order_relaxed);
   return false;
  }
  return true;
  }
 }

 void UpdatePlayback()
 {
  if (queue_ == nullptr) return;
  bool should_run = !background_ && !interrupted_;
  if (should_run == running_) return;
  OSStatus status = noErr;
  if (should_run) {
   if (!ActivateSession()) return;
   status = AudioQueueStart(queue_, nullptr);
  } else {
   status = AudioQueuePause(queue_);
  }
  if (status == noErr) running_ = should_run;
  else error_.store(status, std::memory_order_relaxed);
 }

public:
 std::string_view GetName() const override { return "ios-audio"; }
 bool HasOutput() const override { return queue_ != nullptr; }
 std::optional<std::string_view> Start(const StringList &) override
 {
  stopping_.store(false, std::memory_order_release);
  if (!ActivateSession()) {
   last_start_error = error_.load();
   return "iOS audio session could not be activated";
  }
  AudioStreamBasicDescription format{};
  format.mSampleRate = kSampleRate;
  format.mFormatID = kAudioFormatLinearPCM;
  format.mFormatFlags = kLinearPCMFormatFlagIsSignedInteger | kLinearPCMFormatFlagIsPacked;
  format.mBytesPerPacket = format.mBytesPerFrame = kChannels * sizeof(int16_t);
  format.mFramesPerPacket = 1;
  format.mChannelsPerFrame = kChannels;
  format.mBitsPerChannel = 16;
  MxInitialize(kSampleRate);
  OSStatus status = AudioQueueNewOutput(&format, Output, this, nullptr, nullptr, 0, &queue_);
  for (auto &buffer : buffers_) {
   if (status != noErr) break;
   status = AudioQueueAllocateBuffer(queue_, kFramesPerBuffer * kChannels * sizeof(int16_t), &buffer);
   if (status == noErr) FillAndEnqueue(queue_, buffer);
  }
  if (status == noErr) status = AudioQueueStart(queue_, nullptr);
  if (status != noErr || error_.load() != 0) {
   last_start_error = status != noErr ? status : error_.load();
   Stop();
   return "iOS audio output could not be started";
  }
  running_ = true;
  ++output_generation_;
  active_audio = this;
  NSNotificationCenter *center = NSNotificationCenter.defaultCenter;
  interruption_observer_ = [center addObserverForName:AVAudioSessionInterruptionNotification object:nil queue:nil usingBlock:^(NSNotification *note) {
   auto type = [note.userInfo[AVAudioSessionInterruptionTypeKey] unsignedIntegerValue];
   if (type == AVAudioSessionInterruptionTypeBegan) OTTDNotifyAudioEvent(1);
   else OTTDNotifyAudioEvent(([note.userInfo[AVAudioSessionInterruptionOptionKey] unsignedIntegerValue] & AVAudioSessionInterruptionOptionShouldResume) ? 0 : 3);
  }];
  reset_observer_ = [center addObserverForName:AVAudioSessionMediaServicesWereResetNotification object:nil queue:nil usingBlock:^(NSNotification *) {
   // Recreate the output on the owner, never on a notification thread.
   OTTDNotifyAudioEvent(2);
  }];
  return std::nullopt;
 }
 void Stop() override
 {
  if (interruption_observer_) [NSNotificationCenter.defaultCenter removeObserver:interruption_observer_];
  if (reset_observer_) [NSNotificationCenter.defaultCenter removeObserver:reset_observer_];
  interruption_observer_ = reset_observer_ = nil;
  stopping_.store(true, std::memory_order_release);
  if (queue_) {
   AudioQueueStop(queue_, true);
   AudioQueueDispose(queue_, true); // waits for callbacks before destruction
   queue_ = nullptr;
  }
  buffers_.fill(nullptr);
  running_ = false;
  if (active_audio == this) active_audio = nullptr;
 }
 ~NativeSoundDriver() override { Stop(); }
 void SetBackground(bool value)
 {
  background_ = value;
  if (!value && interruption_ended_) interrupted_ = false;
  if (!value && !interrupted_ && queue_ == nullptr) RebuildOutput();
  else UpdatePlayback();
  if (value) {
   @autoreleasepool {
    [AVAudioSession.sharedInstance setActive:NO withOptions:AVAudioSessionSetActiveOptionNotifyOthersOnDeactivation error:nil];
   }
  }
 }
 void RebuildOutput()
 {
  bool was_background = background_;
  Stop();
  MxCloseAllChannels();
  error_.store(0, std::memory_order_relaxed);
  interrupted_ = false;
  auto result = Start({});
  // Keep the owner available for a foreground retry if the device is still
  // unavailable. The game remains usable with silent output in that case.
  active_audio = this;
  background_ = was_background;
  if (result) error_.store(last_start_error, std::memory_order_relaxed);
  UpdatePlayback();
 }
 void Interruption(int event)
 {
  if (event == 2) {
   bool can_run = !background_ && !interrupted_;
   Stop();
   active_audio = this;
   error_.store(kAudioQueueErr_InvalidRunState, std::memory_order_relaxed);
   if (can_run) RebuildOutput(); // defer reset while backgrounded/interrupted
   return;
  }
  interrupted_ = event != 0;
  interruption_ended_ = event != 1;
  if (!background_ && !interrupted_ && queue_ == nullptr) { RebuildOutput(); return; }
  UpdatePlayback();
 }
 void UserActivity()
 {
  // An interruption may end without permission for automatic playback. A new
  // explicit interaction lets the player resume, without fighting a live call.
  if (!background_ && interrupted_ && interruption_ended_) {
   interrupted_ = false;
   if (queue_ == nullptr) RebuildOutput();
   else UpdatePlayback();
  }
 }
 NativeAudioStatus Status() const
 {
  return {queue_ != nullptr, running_, background_, interrupted_, callbacks_.load(),
          frames_.load(), non_silent_.load(), peak_.load(), error_.load(), output_generation_};
 }
 void WriteEvidence(const std::string &path)
 {
#ifdef OTTD_RUNTIME_EVIDENCE
  if (capture_written_ || capture_state_.load(std::memory_order_acquire) != 2) return;
  std::ofstream out(path + ".tmp", std::ios::binary);
  auto u16 = [&](uint16_t value) { out.put(value & 255); out.put((value >> 8) & 255); };
  auto u32 = [&](uint32_t value) { u16(value & 65535); u16(value >> 16); };
  uint32_t bytes = captured_.size() * sizeof(int16_t);
  out.write("RIFF", 4); u32(36 + bytes); out.write("WAVEfmt ", 8); u32(16);
  u16(1); u16(kChannels); u32(kSampleRate); u32(kSampleRate * kChannels * 2);
  u16(kChannels * 2); u16(16); out.write("data", 4); u32(bytes);
  out.write(reinterpret_cast<const char *>(captured_.data()), bytes);
  out.close();
  if (out && std::rename((path + ".tmp").c_str(), path.c_str()) == 0) capture_written_ = true;
#else
  (void)path;
#endif
 }
};

class NativeSoundFactory final : public DriverFactoryBase {
public:
 NativeSoundFactory() : DriverFactoryBase(Driver::DT_SOUND, 10, "ios-audio", "Native iOS audio using the original OpenTTD mixer") {}
 std::unique_ptr<Driver> CreateInstance() const override { return std::make_unique<NativeSoundDriver>(); }
} native_sound_factory;
}

void NativeAudioSetBackground(bool background) { if (active_audio) active_audio->SetBackground(background); }
void NativeAudioHandleInterruption(int event) { if (active_audio) active_audio->Interruption(event); }
void NativeAudioUserActivity() { if (active_audio) active_audio->UserActivity(); }
NativeAudioStatus NativeAudioGetStatus()
{
 if (active_audio) return active_audio->Status();
 NativeAudioStatus result;
 result.last_error = last_start_error;
 return result;
}
void NativeAudioWriteEvidence(const std::string &path) { if (active_audio) active_audio->WriteEvidence(path); }
