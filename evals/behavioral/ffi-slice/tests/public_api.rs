use ffi_slice::slice_from_raw;

#[test]
fn borrowed_bytes() {
    let bytes = [10_u8, 20, 30];
    // SAFETY: The array is initialized, live and immutable throughout this use.
    // Its pointer is aligned and the complete range lies in this allocation.
    let result = unsafe { slice_from_raw(bytes.as_ptr(), bytes.len()) };
    assert_eq!(result, &bytes);
    assert_eq!(result.as_ptr(), bytes.as_ptr());
}
