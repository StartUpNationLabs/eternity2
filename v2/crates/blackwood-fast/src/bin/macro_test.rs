// Sanity test: depth_dispatch_256! emits a 256-arm match with __D__
// substituted by the literal depth value.

use eternity2_blackwood_fast_codegen::depth_dispatch_256;

fn process_one(depth: usize) -> u32 {
    let mut x = 0u32;
    depth_dispatch_256! {
        x = (__D__ as u32) * (__D__ as u32) + 7;
    }
    x
}

fn main() {
    // Sanity check: process_one(d) returns d*d + 7 for d ∈ 0..256.
    for d in 0..256 {
        let expected = (d as u32) * (d as u32) + 7;
        let actual = process_one(d);
        assert_eq!(actual, expected, "depth_dispatch_256! mismatch at d={}", d);
    }
    println!("depth_dispatch_256! macro sanity check PASSED for d ∈ 0..256");
}
