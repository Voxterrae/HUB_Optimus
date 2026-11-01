//! Fixed error reserve:255 acquisition/cleanup entries and one final receipt.
use crate::model::{Domain, Error, Kind, Operation, Phase, Reason};

const EMPTY: Error = Error::internal(Phase::Initial, Operation::Validate, Reason::Budget);
pub struct ErrorBag {
    entries: [Error;256],
    count: usize,
    primary: bool,
    receipt: bool,
    cleanup_failed: bool,
    unrepresentable: bool,
}

impl ErrorBag {
    pub const fn new() -> Self {
        Self {entries:[EMPTY;256],count:0,primary:false,receipt:false,
            cleanup_failed:false,unrepresentable:false}
    }
    fn fail(&mut self) -> bool { self.unrepresentable=true; false }
    fn cleanup_shape(error:&Error) -> bool {
        error.phase==Phase::Cleanup && matches!(error.operation,Operation::CloseHandle|Operation::LocalFree)
    }
    pub fn primary(&mut self, mut error:Error) -> bool {
        error.kind=Kind::Primary;
        if Self::cleanup_shape(&error) { self.cleanup_failed=true; }
        if self.primary {
            // Helpers can register the failure before checked cleanup, then
            // propagate the same error to the orchestration boundary.
            if self.entries[0]==error { return true; }
            return self.fail();
        }
        let normal=self.count-usize::from(self.receipt);
        if normal>=255 { return self.fail(); }
        self.entries.copy_within(0..self.count,1);
        self.entries[0]=error;
        self.primary=true;
        self.count+=1;
        true
    }
    pub fn cleanup(&mut self, mut error:Error) -> bool {
        self.cleanup_failed=true;
        if !Self::cleanup_shape(&error) { return self.fail(); }
        let normal=self.count-usize::from(self.receipt);
        if normal>=255 { return self.fail(); }
        error.kind=Kind::Cleanup;
        if self.receipt { self.entries[normal+1]=self.entries[normal]; }
        self.entries[normal]=error;
        self.count+=1;
        true
    }
    pub fn receipt_bound(&mut self) -> bool {
        if self.receipt || self.count>=256 { return self.fail(); }
        self.entries[self.count]=Error {kind:Kind::Receipt,phase:Phase::Serialize,
            operation:Operation::Serialize,domain:Domain::Internal,code:None,
            reason:Some(Reason::ReceiptBound),ancestor_index:None,completion:None};
        self.count+=1;
        self.receipt=true;
        true
    }
    pub fn as_slice(&self) -> &[Error] { &self.entries[..self.count] }
    pub fn cleanup_failed(&self) -> bool { self.cleanup_failed }
    pub fn unrepresentable(&self) -> bool { self.unrepresentable }
}
