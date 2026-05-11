// Monotonic-microsecond clock that works on native and wasm32 browsers.

#[cfg(not(target_arch = "wasm32"))]
pub struct Clock(std::time::Instant);

#[cfg(not(target_arch = "wasm32"))]
impl Clock {
    pub fn now() -> Self { Self(std::time::Instant::now()) }
    pub fn elapsed_us(&self) -> u64 {
        u64::try_from(self.0.elapsed().as_micros()).unwrap_or(u64::MAX)
    }
}

#[cfg(target_arch = "wasm32")]
pub struct Clock(f64);

#[cfg(target_arch = "wasm32")]
impl Clock {
    pub fn now() -> Self { Self(js_sys::Date::now()) }
    pub fn elapsed_us(&self) -> u64 {
        let now = js_sys::Date::now();
        ((now - self.0).max(0.0) * 1000.0) as u64
    }
}
