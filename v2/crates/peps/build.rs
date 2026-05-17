fn main() {
    // Link against system openblas (provides BLAS + LAPACK).
    println!("cargo:rustc-link-search=native=/opt/homebrew/opt/openblas/lib");
    println!("cargo:rustc-link-lib=dylib=openblas");
}
