// eternity2-blackwood-fast-codegen — proc-macro that emits a match
// dispatching over `depth ∈ 0..WH` with each arm containing the
// per-depth specialised body of solve_blackwood_sized.
//
// Vol-106 T12 (WIP). The per-depth body uses `depth = D` as a const
// literal inside each arm, so all D-dependent calculations
// (post_depth = D+1, is_top_row = D < 16, etc.) become compile-time
// constants visible to LLVM.
//
// USAGE in lib.rs:
//   use eternity2_blackwood_fast_codegen::depth_dispatch;
//   depth_dispatch!(WH = 256, depth = depth, body = { ... });
//
// (Currently a SKELETON — emits the dispatch shape but the inner body
// is still parameterised on runtime `depth`. To activate constant
// folding, callers must structure the body so every reference to
// `depth` is a literal D from the macro expansion.)

use proc_macro::TokenStream;
use quote::quote;

/// Emit a `match depth { 0 => block_with_D=0, 1 => block_with_D=1, ... }`
/// where each arm has the supplied body with `__D__` replaced by the
/// literal depth value. The macro takes the body as a token tree.
///
/// CAVEAT: the body must use the placeholder `__D__` (literal token)
/// wherever a depth-const is needed. The macro substitutes it with
/// the integer literal for each arm.
///
/// Currently emits arms 0..256 (canonical WH).
#[proc_macro]
pub fn depth_dispatch_256(input: TokenStream) -> TokenStream {
    let body_ts = proc_macro2::TokenStream::from(input);
    let mut arms = proc_macro2::TokenStream::new();
    for d in 0u32..256 {
        let d_lit = proc_macro2::Literal::u32_unsuffixed(d);
        let body_substituted = substitute_placeholder(body_ts.clone(), d);
        let arm = quote! {
            #d_lit => { #body_substituted }
        };
        arms.extend(arm);
    }
    let out = quote! {
        match depth {
            #arms
            _ => unreachable!(),
        }
    };
    out.into()
}

/// Walk a TokenStream and replace any `ident == "__D__"` with the
/// integer literal `d`.
fn substitute_placeholder(ts: proc_macro2::TokenStream, d: u32) -> proc_macro2::TokenStream {
    use proc_macro2::{TokenStream, TokenTree};
    let mut out = TokenStream::new();
    for tt in ts {
        let new_tt: TokenTree = match tt {
            TokenTree::Group(g) => {
                let inner = substitute_placeholder(g.stream(), d);
                TokenTree::Group(proc_macro2::Group::new(g.delimiter(), inner))
            }
            TokenTree::Ident(id) if id.to_string() == "__D__" => {
                // Emit as usize literal so call sites can use .wrapping_sub etc.
                TokenTree::Literal(proc_macro2::Literal::usize_suffixed(d as usize))
            }
            other => other,
        };
        out.extend(std::iter::once(new_tt));
    }
    out
}
