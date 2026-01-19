# Session Log: January 19, 2026

## 🚀 High-Precision Movement & Physics
- **FRect Migration**: Transitioned all game entities (`Bird`, `Pipe`, `Particle`, `Button`) to `pygame.FRect` for true sub-pixel precision.
- **get_frect Helper**: Added a compatibility layer to ensure the game runs on both `pygame-ce` (with FRect) and standard `pygame` (falling back to Rect).
- **Sub-step Integration**: Moved background and ground scrolling into the 4x sub-step physics loop to perfectly sync the environment with entity movement.

## 🕹️ Responsiveness & Controls
- **Instant Jump**: Moved the flap trigger to `FINGERDOWN` (Touch) for immediate response.
- **Latency Tuning**: Reduced `pygame.mixer` buffer to `512` and tuned `flap_cooldown` to `0.05s` to eliminate double-flapping while maintaining high responsiveness.
- **Unpause Logic**: Tapping the play button unpauses without flapping; tapping anywhere else unpauses AND flaps.

## 🎨 UI & Effects
- **Pulse Score**: Added a smooth scaling "pulse" effect to the score counter whenever it updates.
- **Dynamic Pause Button**: A simplified white icon with shadow that toggles between Pause and Play states.
- **Smooth Particles**: Fixed collision particle invisibility by ensuring unique surface copies for independent alpha fading.

## 🏗️ Pipe Motion Refinement
- **Graceful Oscillation**: Implemented amplitude ramping (lerp) so pipes start moving smoothly at score 5 rather than jumping suddenly.
- **Randomized Phase**: Each pipe pair now has a unique random phase while maintaining perfect top/bottom synchronization.

## 💀 Death & Collision Physics
- **Visual Snapping**: Used collision masks to ensure the bird rests perfectly on the ground without "floating."
- **Crashed Aesthetic**: Bird now settles "beak-down" (-90 degrees) and sinks slightly into the ground upon impact.
- **Pipe Hit Reaction**: Hitting a pipe triggers a backward projectile arc, while ceiling/ground hits result in a direct tumble.

## 🔧 Critical Bug Fixes
- Fixed `SyntaxError` regarding `global` declarations inside the main loop.
- Fixed `TypeError` caused by float indexing into `SINE_TABLE`.
- Fixed `AttributeError` by removing all remaining `px/py` references in favor of `rect.x/y`.

## 📌 Status for Next Session
- **Build State**: Ready to build and deploy. All syntax and logic errors observed in local testing have been resolved.
- **Testing Goal**: Verify the "graceful" pipe ramping and the "pulse" score effect on the physical device.
