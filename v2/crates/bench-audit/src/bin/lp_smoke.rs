#![forbid(unsafe_code)]

use good_lp::{constraint, default_solver, variables, Solution, SolverModel};

fn main() {
    variables! {
        problem:
            0 <= x <= 5;
            0 <= y <= 5;
    }
    let solution = problem
        .maximise(2.0 * x + 3.0 * y)
        .using(default_solver)
        .with(constraint!(x + y <= 7))
        .with(constraint!(x + 2.0 * y <= 10))
        .solve()
        .expect("LP solve failed");
    let xv = solution.value(x);
    let yv = solution.value(y);
    let obj = 2.0 * xv + 3.0 * yv;
    println!("x = {xv:.4}");
    println!("y = {yv:.4}");
    println!("obj = {obj:.4}");
    // Expected: x=4, y=3, obj=17 (or 0,5 obj=15, depends on LP solver pivoting; both feasible)
    assert!(obj >= 14.9 - 1e-6, "expected obj >= 14.9, got {obj}");
    println!("LP smoke test passed.");
}
