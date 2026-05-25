# Input Backend Roadmap

## Stages

1. **User-mode backends**
   - `native-sendinput`: Rust DLL over Windows `SendInput` using scan-code keys and Unicode text.
   - `python-sendinput`: Python ctypes fallback.
   - `window-message`: foreground window `PostMessage` path for targets that accept window messages.

2. **Virtual HID**
   - Current stage: interface and detection only.
   - First status: `unavailable: driver_not_installed`.
   - Later work: service/device detection, installer/uninstaller, signing, permission checks, OS compatibility, and recovery.
   - Cost and rollout notes: see [Virtual HID Development Cost](virtual-hid-development-cost.md).

3. **Hardware HID**
   - Future advanced mode for devices such as RP2040.
   - PC app edits/validates/downloads rules; hardware executes supported actions.

## Non-goals

- No anti-cheat bypass guarantee.
- No protected-process or elevated-window bypass guarantee.
- User-mode backends are best-effort and may fail for Raw Input, DirectInput, exclusive fullscreen, driver-only, or filtered targets.

## Fallback Policy

When a requested backend is unavailable:

- `auto`: log the requested backend, actual fallback backend, and reason, then use `fallbackBackend`.
- `error`: log unavailable and do not silently send via another backend.
- `disabled`: treat unavailable as disabled and do not send.

Default:

```json
{
  "inputBackend": "auto",
  "fallbackBackend": "native-sendinput",
  "fallbackPolicy": "auto",
  "inputMode": "scan-code"
}
```
