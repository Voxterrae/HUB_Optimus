//! One fixed allocation, with monotonic, disjoint borrowed ranges.
//!
//! Production requests96MiB, then claims32MiB output before acquisition. The
//! allocator's reported capacity is checked before publishing the arena. This
//! accounts for owned capacity, not allocator metadata, OS allocations or RSS.
use crate::model::{Error, Operation, Path, Phase, Reason, Result};
use std::cell::{Cell, UnsafeCell};
use std::mem::{align_of, size_of};
use std::ptr;

pub const PRODUCTION_CAPACITY: usize = 96 * 1024 * 1024;
pub const OUTPUT_CAPACITY: usize = 32 * 1024 * 1024;

pub struct Arena {
    // Length remains zero: arbitrary Copy values may contain uninitialized
    // padding, so the allocation must never be read as initialized u64 values.
    _storage: UnsafeCell<Vec<u64>>,
    base: *mut u8,
    capacity: usize,
    allocated_capacity: usize,
    used: Cell<usize>,
    peak: Cell<usize>,
    output_claimed: Cell<bool>,
}

fn budget() -> Error {
    Error::internal(Phase::Initial, Operation::Validate, Reason::Budget)
}
fn malformed() -> Error {
    Error::internal(Phase::Capture, Operation::Validate, Reason::Malformed)
}

impl Arena {
    pub fn new(capacity: usize) -> Result<Self> {
        let rounded = capacity.checked_add(7).ok_or_else(budget)? & !7;
        if rounded > isize::MAX as usize { return Err(budget()); }
        let words = rounded / 8;
        let mut storage = Vec::<u64>::new();
        storage.try_reserve_exact(words).map_err(|_| budget())?;
        let actual = storage.capacity().checked_mul(8).ok_or_else(budget)?;
        // try_reserve_exact does not promise exact reported capacity. Refuse
        // unexpected excess rather than silently exceeding the owned budget.
        if actual != rounded { return Err(budget()); }
        let base = storage.as_mut_ptr().cast::<u8>();
        Ok(Self { _storage:UnsafeCell::new(storage), base, capacity,
            allocated_capacity:actual, used:Cell::new(0), peak:Cell::new(0),
            output_claimed:Cell::new(false) })
    }

    pub fn used(&self) -> usize { self.used.get() }
    pub fn capacity(&self) -> usize { self.capacity }
    pub fn allocated_capacity(&self) -> usize { self.allocated_capacity }
    pub fn peak(&self) -> usize { self.peak.get() }

    fn reserve(&self, bytes: usize, alignment: usize) -> Result<*mut u8> {
        if alignment > align_of::<u64>() || !alignment.is_power_of_two() {
            return Err(budget());
        }
        // Empty views have no readable bytes and need no arena padding even
        // when the last occupied byte is not aligned for the requested type.
        if bytes == 0 { return Ok(ptr::NonNull::<u64>::dangling().as_ptr().cast()); }
        let start = self.used.get().checked_add(alignment - 1)
            .ok_or_else(budget)? & !(alignment - 1);
        let end = start.checked_add(bytes).ok_or_else(budget)?;
        if end > self.capacity || bytes > isize::MAX as usize { return Err(budget()); }
        self.used.set(end);
        self.peak.set(self.peak.get().max(end));
        // SAFETY: end is within the original allocation; no operation ever
        // reallocates, rewinds or republishes this newly reserved range.
        Ok(unsafe { self.base.add(start) })
    }

    pub fn bytes(&self, source: &[u8]) -> Result<&[u8]> { self.slice(source) }

    pub fn slice<T: Copy>(&self, source: &[T]) -> Result<&[T]> {
        let bytes = size_of::<T>().checked_mul(source.len()).ok_or_else(budget)?;
        let target = self.reserve(bytes, align_of::<T>())?.cast::<T>();
        // SAFETY: reserve checked alignment/extent and returned a fresh range.
        // Any existing arena-backed source is in an earlier disjoint range.
        // T:Copy permits copying its representation, including padding.
        unsafe {
            ptr::copy_nonoverlapping(source.as_ptr(), target, source.len());
            Ok(std::slice::from_raw_parts(target, source.len()))
        }
    }

    pub fn copy_iter<T: Copy>(&self, count: usize, iter: impl IntoIterator<Item=T>) -> Result<&[T]> {
        let bytes = size_of::<T>().checked_mul(count).ok_or_else(budget)?;
        if count > isize::MAX as usize || (size_of::<T>() == 0 && count > self.capacity) {
            return Err(budget());
        }
        let target = self.reserve(bytes, align_of::<T>())?.cast::<T>();
        let mut values = iter.into_iter();
        for index in 0..count {
            let value = values.next().ok_or_else(malformed)?;
            // SAFETY: each distinct slot is in the checked fresh allocation;
            // no reference to a partially initialized result is published.
            unsafe { target.add(index).write(value); }
        }
        if values.next().is_some() { return Err(malformed()); }
        // On iterator mismatch the reservation intentionally stays charged.
        // SAFETY: all count elements were initialized; T has no destructor.
        Ok(unsafe { std::slice::from_raw_parts(target, count) })
    }

    fn utf8_len(utf16: &[u16], max: usize) -> Result<usize> {
        if utf16.len() > max { return Err(budget()); }
        let mut bytes = 0usize;
        for decoded in char::decode_utf16(utf16.iter().copied()) {
            let ch = decoded.map_err(|_| malformed())?;
            if ch == '\0' { return Err(malformed()); }
            bytes = bytes.checked_add(ch.len_utf8()).ok_or_else(budget)?;
        }
        Ok(bytes)
    }

    // The only writable view covers a fresh, unpublished UTF-8 range. Both
    // passes decode the same borrowed input; valid scalars initialize all bytes.
    // SAFETY contract: target must identify a writable, disjoint range of length
    // bytes, remain allocated for 'a, and never be mutated after this returns a
    // view. Only path/text call this, with a reservation borrowed from self.
    unsafe fn write_utf8<'a>(target: *mut u8, bytes: usize, utf16: &[u16]) -> Result<&'a str> {
        let mut offset = 0usize;
        for decoded in char::decode_utf16(utf16.iter().copied()) {
            let ch = decoded.map_err(|_| malformed())?;
            let mut encoded = [0u8;4];
            let text = ch.encode_utf8(&mut encoded).as_bytes();
            let end = offset.checked_add(text.len()).ok_or_else(budget)?;
            if end > bytes { return Err(malformed()); }
            // SAFETY: caller reserved bytes; end is checked above, and this
            // local character buffer cannot overlap the arena allocation.
            unsafe { ptr::copy_nonoverlapping(text.as_ptr(), target.add(offset), text.len()); }
            offset = end;
        }
        if offset != bytes { return Err(malformed()); }
        // SAFETY: all bytes in the newly reserved range have been initialized.
        let data = unsafe { std::slice::from_raw_parts(target, bytes) };
        std::str::from_utf8(data).map_err(|_| malformed())
    }

    pub fn path(&self, utf16: &[u16]) -> Result<Path<'_>> {
        if utf16.is_empty() { return Err(malformed()); }
        let utf8_bytes = Self::utf8_len(utf16, 32767)?;
        let unit_bytes = utf16.len().checked_mul(2).ok_or_else(budget)?;
        let total = unit_bytes.checked_add(utf8_bytes).ok_or_else(budget)?;
        // Charge both representations and their alignment before copying any
        // source bytes; a failure cannot publish a partial Path.
        let target = self.reserve(total, align_of::<u16>())?;
        // SAFETY: the two regions are disjoint within the checked reservation;
        // source is a valid borrowed slice and previous arena ranges are disjoint.
        unsafe {
            ptr::copy_nonoverlapping(utf16.as_ptr(), target.cast::<u16>(), utf16.len());
            let text = Self::write_utf8(target.add(unit_bytes), utf8_bytes, utf16)?;
            Ok(Path { text, utf16:std::slice::from_raw_parts(target.cast::<u16>(), utf16.len()) })
        }
    }

    pub fn text(&self, utf16: &[u16], max: usize) -> Result<&str> {
        let bytes = Self::utf8_len(utf16, max)?;
        let target = self.reserve(bytes, 1)?;
        // SAFETY: fresh reservation has exactly the length computed above.
        unsafe { Self::write_utf8(target, bytes, utf16) }
    }

    pub fn output(&self, count: usize) -> Result<&mut [u8]> {
        if self.output_claimed.get() { return Err(budget()); }
        let target = self.reserve(count, 1)?;
        self.output_claimed.set(true);
        // SAFETY: a fresh range is initialized before forming the only mutable
        // view. Bump-only allocation cannot create another overlapping view.
        unsafe {
            ptr::write_bytes(target, 0, count);
            Ok(std::slice::from_raw_parts_mut(target, count))
        }
    }
}
