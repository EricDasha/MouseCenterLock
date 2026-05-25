#![cfg_attr(not(windows), allow(unused))]

#[cfg(windows)]
mod win {
    use core::mem::size_of;

    const INPUT_MOUSE: u32 = 0;
    const INPUT_KEYBOARD: u32 = 1;

    const KEYEVENTF_KEYUP: u32 = 0x0002;
    const KEYEVENTF_UNICODE: u32 = 0x0004;
    const KEYEVENTF_SCANCODE: u32 = 0x0008;
    const KEYEVENTF_EXTENDEDKEY: u32 = 0x0001;
    const MAPVK_VK_TO_VSC_EX: u32 = 4;

    const MOUSEEVENTF_LEFTDOWN: u32 = 0x0002;
    const MOUSEEVENTF_LEFTUP: u32 = 0x0004;
    const MOUSEEVENTF_RIGHTDOWN: u32 = 0x0008;
    const MOUSEEVENTF_RIGHTUP: u32 = 0x0010;
    const MOUSEEVENTF_MIDDLEDOWN: u32 = 0x0020;
    const MOUSEEVENTF_MIDDLEUP: u32 = 0x0040;
    const MOUSEEVENTF_XDOWN: u32 = 0x0080;
    const MOUSEEVENTF_XUP: u32 = 0x0100;

    const XBUTTON1: u32 = 0x0001;
    const XBUTTON2: u32 = 0x0002;

    #[repr(C)]
    #[derive(Clone, Copy)]
    struct MouseInput {
        dx: i32,
        dy: i32,
        mouse_data: u32,
        dw_flags: u32,
        time: u32,
        dw_extra_info: usize,
    }

    #[repr(C)]
    #[derive(Clone, Copy)]
    struct KeybdInput {
        w_vk: u16,
        w_scan: u16,
        dw_flags: u32,
        time: u32,
        dw_extra_info: usize,
    }

    #[repr(C)]
    #[derive(Clone, Copy)]
    struct HardwareInput {
        u_msg: u32,
        w_param_l: u16,
        w_param_h: u16,
    }

    #[repr(C)]
    union InputUnion {
        mi: MouseInput,
        ki: KeybdInput,
        hi: HardwareInput,
    }

    #[repr(C)]
    struct Input {
        r#type: u32,
        union: InputUnion,
    }

    #[link(name = "user32")]
    unsafe extern "system" {
        fn SendInput(c_inputs: u32, p_inputs: *const Input, cb_size: i32) -> u32;
        fn MapVirtualKeyW(u_code: u32, u_map_type: u32) -> u32;
        fn mouse_event(dw_flags: u32, dx: u32, dy: u32, dw_data: u32, dw_extra_info: usize);
    }

    fn mouse_input(flags: u32, mouse_data: u32) -> Input {
        Input {
            r#type: INPUT_MOUSE,
            union: InputUnion {
                mi: MouseInput {
                    dx: 0,
                    dy: 0,
                    mouse_data,
                    dw_flags: flags,
                    time: 0,
                    dw_extra_info: 0,
                },
            },
        }
    }

    fn keyboard_input(vk: u16, flags: u32) -> Input {
        Input {
            r#type: INPUT_KEYBOARD,
            union: InputUnion {
                ki: KeybdInput {
                    w_vk: vk,
                    w_scan: 0,
                    dw_flags: flags,
                    time: 0,
                    dw_extra_info: 0,
                },
            },
        }
    }

    fn scancode_input(scan: u16, flags: u32) -> Input {
        Input {
            r#type: INPUT_KEYBOARD,
            union: InputUnion {
                ki: KeybdInput {
                    w_vk: 0,
                    w_scan: scan,
                    dw_flags: flags | KEYEVENTF_SCANCODE,
                    time: 0,
                    dw_extra_info: 0,
                },
            },
        }
    }

    fn unicode_input(unit: u16, flags: u32) -> Input {
        Input {
            r#type: INPUT_KEYBOARD,
            union: InputUnion {
                ki: KeybdInput {
                    w_vk: 0,
                    w_scan: unit,
                    dw_flags: flags | KEYEVENTF_UNICODE,
                    time: 0,
                    dw_extra_info: 0,
                },
            },
        }
    }

    fn send_input(inputs: &[Input]) -> bool {
        if inputs.is_empty() {
            return true;
        }
        let sent = unsafe { SendInput(inputs.len() as u32, inputs.as_ptr(), size_of::<Input>() as i32) };
        sent == inputs.len() as u32
    }

    fn button_flags(button_code: u32) -> (u32, u32, u32) {
        match button_code {
            1 => (MOUSEEVENTF_RIGHTDOWN, MOUSEEVENTF_RIGHTUP, 0),
            2 => (MOUSEEVENTF_MIDDLEDOWN, MOUSEEVENTF_MIDDLEUP, 0),
            3 => (MOUSEEVENTF_XDOWN, MOUSEEVENTF_XUP, XBUTTON1),
            4 => (MOUSEEVENTF_XDOWN, MOUSEEVENTF_XUP, XBUTTON2),
            _ => (MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP, 0),
        }
    }

    fn vk_to_scan_flags(vk: u16) -> Option<(u16, u32)> {
        if vk == 0 {
            return None;
        }
        let mapped = unsafe { MapVirtualKeyW(vk as u32, MAPVK_VK_TO_VSC_EX) };
        if mapped == 0 {
            return None;
        }
        let scan = (mapped & 0xFF) as u16;
        let flags = if mapped & 0x100 != 0 {
            KEYEVENTF_EXTENDEDKEY
        } else {
            0
        };
        Some((scan, flags))
    }

    #[unsafe(no_mangle)]
    pub extern "C" fn mcl_native_version() -> u32 {
        1
    }

    #[unsafe(no_mangle)]
    pub extern "C" fn mcl_click_mouse(button_code: u32) -> i32 {
        let (down, up, data) = button_flags(button_code);
        let inputs = [mouse_input(down, data), mouse_input(up, data)];
        if send_input(&inputs) {
            return 1;
        }
        // Same safety-net semantics as the Python backend: old mouse_event path
        // is only used after SendInput refuses the batch.
        unsafe {
            mouse_event(down, 0, 0, data, 0);
            mouse_event(up, 0, 0, data, 0);
        }
        2
    }

    #[unsafe(no_mangle)]
    pub extern "C" fn mcl_mouse_down(button_code: u32) -> i32 {
        let (down, _up, data) = button_flags(button_code);
        let inputs = [mouse_input(down, data)];
        if send_input(&inputs) {
            return 1;
        }
        unsafe {
            mouse_event(down, 0, 0, data, 0);
        }
        2
    }

    #[unsafe(no_mangle)]
    pub extern "C" fn mcl_mouse_up(button_code: u32) -> i32 {
        let (_down, up, data) = button_flags(button_code);
        let inputs = [mouse_input(up, data)];
        if send_input(&inputs) {
            return 1;
        }
        unsafe {
            mouse_event(up, 0, 0, data, 0);
        }
        2
    }

    #[unsafe(no_mangle)]
    pub extern "C" fn mcl_key_down_vk(vk: u16) -> i32 {
        if vk == 0 {
            return 0;
        }
        if let Some((scan, flags)) = vk_to_scan_flags(vk) {
            return i32::from(send_input(&[scancode_input(scan, flags)]));
        }
        i32::from(send_input(&[keyboard_input(vk, 0)]))
    }

    #[unsafe(no_mangle)]
    pub extern "C" fn mcl_key_up_vk(vk: u16) -> i32 {
        if vk == 0 {
            return 0;
        }
        if let Some((scan, flags)) = vk_to_scan_flags(vk) {
            return i32::from(send_input(&[scancode_input(scan, flags | KEYEVENTF_KEYUP)]));
        }
        i32::from(send_input(&[keyboard_input(vk, KEYEVENTF_KEYUP)]))
    }

    #[unsafe(no_mangle)]
    pub extern "C" fn mcl_press_vk(vk: u16) -> i32 {
        if vk == 0 {
            return 0;
        }
        if let Some((scan, flags)) = vk_to_scan_flags(vk) {
            let inputs = [
                scancode_input(scan, flags),
                scancode_input(scan, flags | KEYEVENTF_KEYUP),
            ];
            return i32::from(send_input(&inputs));
        }
        let inputs = [keyboard_input(vk, 0), keyboard_input(vk, KEYEVENTF_KEYUP)];
        i32::from(send_input(&inputs))
    }

    #[unsafe(no_mangle)]
    pub extern "C" fn mcl_type_utf16(units: *const u16, len: usize) -> i32 {
        if units.is_null() || len == 0 || len > 2048 {
            return 0;
        }
        let text = unsafe { core::slice::from_raw_parts(units, len) };
        for unit in text.iter().copied() {
            let inputs = [
                unicode_input(unit, 0),
                unicode_input(unit, KEYEVENTF_KEYUP),
            ];
            if !send_input(&inputs) {
                return 0;
            }
        }
        1
    }
}

#[cfg(not(windows))]
#[unsafe(no_mangle)]
pub extern "C" fn mcl_native_version() -> u32 {
    0
}
