# Virtual HID Development Cost for MCL

## Verdict

Virtual HID is the correct software-side route for improving compatibility beyond user-mode `SendInput`, but it is not a small library integration. On Windows, the production-grade path is a kernel-mode HID source driver using Microsoft Virtual HID Framework (VHF), plus installer, signing, detection, diagnostics, and rollback tooling.

## Recommended Scope

### Phase 2.1 — Detection and UX scaffold

Status: already started in `feat/virtual-hid-detection`.

- Backend registry exposes `virtual-hid`.
- Detection reports unavailable states such as `driver_not_installed`.
- Config schema supports `inputBackend`, `fallbackBackend`, and `fallbackPolicy`.
- Logs must show requested backend, actual backend, and fallback reason.
- UI should show Virtual HID as experimental/not installed instead of hiding it.

Estimated cost: **0.5–1.5 engineering days**.

### Phase 2.2 — Driver feasibility prototype

- Clone/study Microsoft `vhidmini2` and VHF samples.
- Build a minimal KMDF/VHF HID source driver.
- Define keyboard and mouse HID report descriptors.
- Submit test input reports from a tiny user-mode control app.
- Run only on test-signed/dev machines.

Estimated cost: **1–3 engineering weeks** if the engineer already understands Windows driver development; **4–8 weeks** if not.

### Phase 2.3 — MCL integration prototype

- Add a user-mode bridge between MCL and the driver.
- Define a stable IOCTL/control protocol.
- Map MCL actions to HID keyboard/mouse reports.
- Preserve fallback behavior when the driver is unavailable.
- Add logs and a diagnostics page showing service/device status.

Estimated cost: **2–4 engineering weeks** after the driver prototype works.

### Phase 2.4 — Production packaging

- Driver signing workflow.
- Installer/uninstaller.
- Upgrade and rollback behavior.
- Driver/service recovery.
- Windows 10/11 compatibility matrix.
- Security review and abuse-risk documentation.
- HLK or attestation submission workflow depending on distribution goals.

Estimated cost: **1–3 engineering months** for a robust public release.

## Cost Drivers

- **Driver signing**: 64-bit Windows kernel-mode drivers require proper signing. Current Microsoft docs state Windows 10/Server 2016+ kernel-mode drivers must be signed through the Windows Hardware Developer Center Dashboard and require an EV certificate.
- **HLK vs attestation**: HLK-tested dashboard signing is the recommended broad compatibility path. Attestation signing is easier but is described by Microsoft as testing-oriented, not Windows Certified, and has distribution limitations.
- **Installer risk**: Bad driver install/uninstall can leave input devices or services in a broken state.
- **Support burden**: Users will have different Windows versions, Secure Boot/HVCI settings, security products, and permissions.
- **Not an anti-cheat bypass**: Virtual HID may improve normal compatibility, but protected games and anti-cheat systems can still block, flag, or disallow automation.

## Staffing Estimate

| Target | Team | Calendar |
|---|---:|---:|
| Detection-only scaffold | 1 app engineer | 1 day |
| Developer-only VHF prototype | 1 Windows driver-capable engineer | 2–6 weeks |
| MCL integrated experimental backend | 1 driver engineer + 1 app engineer | 1–2 months |
| Public production-ready backend | 1 driver engineer + 1 app engineer + QA/signing/release support | 2–4 months |

## Practical Recommendation

For MCL, do not jump straight to driver installation. Finish the user-facing macro experience first:

- Macro test panel.
- Backend diagnostics page.
- Compatibility matrix.
- Default rule templates.
- Clear error/fallback messages.
- Log export.

Then build a separate experimental VHF branch with a dev-only driver. Promote it only after install/uninstall and recovery are reliable.

## Non-goals

- No anti-cheat bypass guarantee.
- No protected-process bypass.
- No stealth behavior.
- No default driver installation without explicit user action.
- No driver-signing-bypass instructions in product docs.
