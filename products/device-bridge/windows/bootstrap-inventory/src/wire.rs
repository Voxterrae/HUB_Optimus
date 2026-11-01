//! Allocation-free, complete v0.1 JSON encoding. Typed observations are data;
//! validation here supplies no native identity, policy or activation authority.
use crate::model::*;

pub const MAX_OUTPUT: usize = 32 * 1024 * 1024;
pub const REFUSAL_RESERVE: usize = 128 * 1024;
const KNOWN_FOLDER: &str = "905e63b6-c1bf-494e-b29c-65b732d3d21a";

fn bad() -> Error { Error::internal(Phase::Serialize,Operation::Validate,Reason::Malformed) }
fn bound() -> Error { Error::internal(Phase::Serialize,Operation::Serialize,Reason::Bound) }
fn require(value:bool) -> Result<()> { if value {Ok(())} else {Err(bad())} }
fn bounded(value:bool) -> Result<()> { if value {Ok(())} else {Err(bound())} }

fn valid_hex(text:&str,bytes:usize) -> bool {
    text.len()==bytes*2 && text.bytes().all(|x|x.is_ascii_digit() || (b'a'..=b'f').contains(&x))
}
fn text_units(text:&str,max:usize,empty:bool) -> Result<()> {
    require(empty || !text.is_empty())?;
    require(!text.contains('\0'))?;
    bounded(text.encode_utf16().count()<=max)
}
fn path(path:Path<'_>) -> Result<()> {
    bounded(path.utf16.len()<=32767)?;
    require(!path.utf16.is_empty() && !path.utf16.contains(&0))?;
    require(path.text.encode_utf16().eq(path.utf16.iter().copied()))
}
fn sid(bytes:&[u8]) -> Result<()> {
    bounded(bytes.len()<=68)?;
    require(bytes.len()>=8)?;
    let count=usize::from(bytes[1]);
    require(bytes[0]==1 && count<=15 && bytes.len()==8+4*count)
}
fn sid_attributes(value:SidAttributes<'_>) -> Result<()> { sid(value.sid) }
fn token(value:Token<'_>) -> Result<()> {
    require(matches!(value.token_type,1|2))?;
    require(match value.token_type {1=>value.impersonation_level.is_none(),2=>value.impersonation_level.is_some_and(|x|x<=3),_=>false})?;
    sid(value.user)?;sid(value.owner)?;sid(value.primary_group)?;sid_attributes(value.integrity)?;
    for entries in [value.groups,value.restricted_sids,value.capabilities] {
        bounded(entries.len()<=2048)?;
        for entry in entries {sid_attributes(*entry)?;}
    }
    bounded(value.privileges.len()<=256)?;
    for privilege in value.privileges {text_units(privilege.name,256,false)?;}
    // Raw attributes and boolean-like DWORD results are preserved verbatim.
    // In particular, no masking repairs an unexpected TokenHasRestrictions.
    Ok(())
}
fn ascii_equal(a:&str,b:&str) -> bool {
    a.len()==b.len() && a.bytes().zip(b.bytes()).all(|(x,y)|x.eq_ignore_ascii_case(&y))
}
fn folded_prefix<'a>(text:&'a str,prefix:&str) -> Option<&'a str> {
    let head=text.get(..prefix.len())?;
    if ascii_equal(head,prefix) {text.get(prefix.len()..)} else {None}
}
fn guid_root(text:&str) -> bool {
    if text.len()!=49 || folded_prefix(text,"\\\\?\\Volume{").is_none() {return false;}
    let bytes=text.as_bytes();
    if bytes[47]!=b'}' || bytes[48]!=b'\\' {return false;}
    (11..47).all(|i| if matches!(i,19|24|29|34) {bytes[i]==b'-'} else {bytes[i].is_ascii_hexdigit()})
}
fn route_components(text:&str,allow_empty:bool) -> bool {
    if text.is_empty() {return allow_empty;}
    text.split('\\').all(|component| !component.is_empty()
        && component!="." && component!=".."
        && !component.ends_with('.') && !component.ends_with(' ')
        && !component.chars().any(|c| c<' ' || matches!(c,'/'|':'|'*'|'?'|'"'|'<'|'>'|'|')))
}
fn drive_suffix(text:&str) -> Result<&str> {
    let bytes=text.as_bytes();
    require(bytes.len()>=3 && bytes[0].is_ascii_alphabetic() && bytes[1]==b':' && bytes[2]==b'\\')?;
    let suffix=text.get(3..).ok_or_else(bad)?;
    require(route_components(suffix,true))?;
    Ok(suffix)
}
fn native_root(text:&str) -> bool {
    let Some(rest)=folded_prefix(text,"\\Device\\") else {return false;};
    let rest=rest.strip_suffix('\\').unwrap_or(rest);
    !rest.is_empty() && !rest.contains('\\') && route_components(rest,false)
}
fn relative<'a>(text:&'a str,root:&str) -> Result<&'a str> {
    let base=root.strip_suffix('\\').unwrap_or(root);
    let suffix=folded_prefix(text,base).ok_or_else(bad)?;
    let suffix=if suffix.is_empty() {suffix} else {suffix.strip_prefix('\\').ok_or_else(bad)?};
    require(route_components(suffix,true))?;
    Ok(suffix)
}
fn anchor(value:Anchor<'_>) -> Result<()> {
    require(value.known_folder_id==KNOWN_FOLDER)?;
    path(value.resolved_path)?;path(value.volume_guid)?;path(value.native_root)?;
    text_units(value.filesystem,31,false)?;
    require(guid_root(value.volume_guid.text) && native_root(value.native_root.text))?;
    drive_suffix(value.resolved_path.text)?;
    Ok(())
}
fn ancestors(values:&[Ancestor<'_>]) -> Result<()> {
    bounded(values.len()<=128)?;
    require(!values.is_empty())?;
    for (index,value) in values.iter().enumerate() {
        require(value.index==index as u32)?;
        path(value.path)?;path(value.native_path)?;
        bounded(value.owner_dacl.len()<=65536)?;
    }
    Ok(())
}
fn bindings(anchor:Anchor<'_>,values:&[Ancestor<'_>]) -> Result<()> {
    let first=values.first().ok_or_else(bad)?;
    let last=values.last().ok_or_else(bad)?;
    require(ascii_equal(first.path.text,anchor.volume_guid.text)
        && ascii_equal(first.native_path.text,anchor.native_root.text))?;
    let mut prior="";
    for (index,value) in values.iter().enumerate() {
        require(value.volume_serial64==anchor.volume_serial64)?;
        let guid=relative(value.path.text,anchor.volume_guid.text)?;
        let native=relative(value.native_path.text,anchor.native_root.text)?;
        require(ascii_equal(guid,native))?;
        if index==0 {require(guid.is_empty())?;} else {
            let remainder=if prior.is_empty() {guid} else {
                folded_prefix(guid,prior).and_then(|x|x.strip_prefix('\\')).ok_or_else(bad)?
            };
            require(!remainder.is_empty() && !remainder.contains('\\'))?;
        }
        prior=guid;
    }
    let observed=relative(last.path.text,anchor.volume_guid.text)?;
    require(ascii_equal(observed,drive_suffix(anchor.resolved_path.text)?))
}
fn cleanup_failure(error:&Error) -> bool {
    error.phase==Phase::Cleanup && matches!(error.operation,Operation::CloseHandle|Operation::LocalFree)
}
fn receipt_error(error:&Error) -> bool {
    error.kind==Kind::Receipt && error.phase==Phase::Serialize
        && error.operation==Operation::Serialize && error.domain==Domain::Internal
        && error.code.is_none() && error.reason==Some(Reason::ReceiptBound)
        && error.ancestor_index.is_none() && error.completion.is_none()
}
fn errors(values:&[Error]) -> Result<(bool,bool)> {
    bounded(values.len()<=256)?;
    let mut primary=false;
    let mut receipt=false;
    let mut cleanup=false;
    for (index,error) in values.iter().enumerate() {
        match error.kind {
            Kind::Primary=>{require(!primary && index==0)?;primary=true;},
            Kind::Cleanup=>{require(!receipt && cleanup_failure(error))?;},
            Kind::Receipt=>{require(!receipt && index+1==values.len() && receipt_error(error))?;receipt=true;}
        }
        if error.kind!=Kind::Receipt {require(error.phase!=Phase::Serialize && error.operation!=Operation::Serialize)?;}
        if error.phase==Phase::Cleanup {require(cleanup_failure(error))?;}
        cleanup|=cleanup_failure(error);
        if let Some(index)=error.ancestor_index {require(index<128)?;}
        match error.domain {
            Domain::Internal=>require(error.code.is_none() && error.reason.is_some())?,
            _=>require(error.code.is_some() && error.reason.is_none())?,
        }
        if error.reason==Some(Reason::ReceiptBound) {require(receipt_error(error))?;}
        let nt=matches!(error.operation,Operation::NtCreateFile|Operation::NtQueryInformationFile);
        if let Some(completion)=error.completion {
            require(nt)?;
            // Fatal-pending and the parent's unwritten IOSB sentinel are not
            // terminal evidence and can never be serialized into a receipt.
            require(completion.call!=0x103 && completion.io_status!=0x103
                && !(completion.call as i32>=0 && completion.io_status==0xc0000001 && completion.information==u64::MAX))?;
            match error.domain {
                Domain::Ntstatus=>{
                    require(error.code==Some(completion.call))?;
                    require((completion.call as i32)<0 || (completion.io_status as i32)<0)?;
                },
                Domain::Internal=>require(error.reason==Some(Reason::Malformed)
                    && completion.call as i32>=0 && completion.io_status as i32>=0)?,
                _=>return Err(bad()),
            }
        } else if error.domain==Domain::Ntstatus {return Err(bad());}
    }
    bounded(receipt || values.len()<=255)?;
    Ok((cleanup,receipt))
}
fn validate(receipt:&Receipt<'_>) -> Result<()> {
    require(valid_hex(receipt.collector.source_commit,20) && valid_hex(receipt.collector.policy_sha256,32))?;
    bounded(receipt.collector.target.len()<=128)?;
    require(receipt.collector.target.is_ascii())?;
    if let Some(value)=receipt.process {path(value.image_win32)?;path(value.image_native)?;}
    if let Some(value)=receipt.primary_token {token(value)?;}
    if let Some(value)=receipt.thread_token {token(value)?;require(receipt.thread_context==ThreadContext::Present && value.token_type==2)?;}
    if receipt.thread_context!=ThreadContext::Present {require(receipt.thread_token.is_none())?;}
    if let Some(value)=receipt.anchor {anchor(value)?;}
    if let Some(values)=receipt.ancestors {ancestors(values)?;}
    if let (Some(anchor),Some(values))=(receipt.anchor,receipt.ancestors) {bindings(anchor,values)?;}
    let (cleanup_failed,overflow)=errors(receipt.errors)?;
    require((receipt.cleanup==Cleanup::Failed)==cleanup_failed)?;
    if overflow {require(receipt.outcome==Outcome::Refused && receipt.process.is_none()
        && receipt.primary_token.is_none() && receipt.thread_token.is_none()
        && receipt.anchor.is_none() && receipt.ancestors.is_none())?;}
    match receipt.outcome {
        Outcome::Refused=>require(!receipt.errors.is_empty())?,
        Outcome::Observed=>{
            require(receipt.errors.is_empty() && receipt.recheck==Recheck::Equal
                && receipt.cleanup==Cleanup::Complete && receipt.thread_context==ThreadContext::NoToken
                && receipt.thread_token.is_none() && receipt.elapsed_ms<=10000)?;
            let process=receipt.process.ok_or_else(bad)?;
            require(process.pid!=0 && process.process_machine==0 && process.native_machine==0x8664)?;
            let primary=receipt.primary_token.ok_or_else(bad)?;
            require(primary.token_type==1 && primary.is_app_container==0)?;
            let anchor=receipt.anchor.ok_or_else(bad)?;
            require(anchor.filesystem=="NTFS" && anchor.drive_type==3)?;
            for value in receipt.ancestors.ok_or_else(bad)? {
                require(value.policy_match && value.reparse_tag==0 && value.attributes&0x400==0
                    && value.attributes&0x10!=0 && !value.delete_pending)?;
            }
        }
    }
    Ok(())
}

struct Writer<'a> { output:Option<&'a mut[u8]>, at:usize, limit:usize }
impl<'a> Writer<'a> {
    fn bytes(&mut self,bytes:&[u8]) -> Result<()> {
        let end=self.at.checked_add(bytes.len()).ok_or_else(bound)?;
        bounded(end<=self.limit)?;
        if let Some(output)=self.output.as_deref_mut() {
            output.get_mut(self.at..end).ok_or_else(bound)?.copy_from_slice(bytes);
        }
        self.at=end;
        Ok(())
    }
    fn literal(&mut self,text:&str) -> Result<()> {self.bytes(text.as_bytes())}
    fn unsigned(&mut self,mut value:u64) -> Result<()> {
        let mut buffer=[0u8;20];
        let mut start=buffer.len();
        loop {start-=1;buffer[start]=b'0'+(value%10) as u8;value/=10;if value==0 {break;}}
        self.bytes(&buffer[start..])
    }
    fn signed(&mut self,value:i32) -> Result<()> {
        let wide=i64::from(value);
        if wide<0 {self.literal("-")?;self.unsigned((-wide) as u64)} else {self.unsigned(wide as u64)}
    }
    fn u64s(&mut self,value:u64) -> Result<()> {self.literal("\"")?;self.unsigned(value)?;self.literal("\"")}
    fn string(&mut self,value:&str) -> Result<()> {
        self.literal("\"")?;
        let mut first=0usize;
        for (index,byte) in value.bytes().enumerate() {
            let escaped=match byte {b'"'=>Some("\\\""),b'\\'=>Some("\\\\"),8=>Some("\\b"),12=>Some("\\f"),10=>Some("\\n"),13=>Some("\\r"),9=>Some("\\t"),_=>None};
            if escaped.is_some() || byte<0x20 {
                self.bytes(&value.as_bytes()[first..index])?;
                if let Some(text)=escaped {self.literal(text)?;} else {
                    let hex=b"0123456789abcdef";
                    self.bytes(&[b'\\',b'u',b'0',b'0',hex[usize::from(byte>>4)],hex[usize::from(byte&15)]])?;
                }
                first=index+1;
            }
        }
        self.bytes(&value.as_bytes()[first..])?;
        self.literal("\"")
    }
    fn hex(&mut self,value:&[u8]) -> Result<()> {
        self.literal("\"")?;
        let hex=b"0123456789abcdef";
        for byte in value {self.bytes(&[hex[usize::from(byte>>4)],hex[usize::from(byte&15)]])?;}
        self.literal("\"")
    }
    fn boolean(&mut self,value:bool) -> Result<()> {self.literal(if value {"true"} else {"false"})}
    fn binary(&mut self,value:&[u8]) -> Result<()> {
        self.literal("{\"hex\":")?;self.hex(value)?;
        self.literal(",\"byte_count\":")?;self.unsigned(value.len() as u64)?;self.literal("}")
    }
    fn path(&mut self,value:Path<'_>) -> Result<()> {
        self.literal("{\"text\":")?;self.string(value.text)?;
        self.literal(",\"utf16_units\":")?;self.unsigned(value.utf16.len() as u64)?;self.literal("}")
    }
    fn luid(&mut self,value:Luid) -> Result<()> {
        self.literal("{\"low\":")?;self.unsigned(u64::from(value.low))?;
        self.literal(",\"high\":")?;self.signed(value.high)?;self.literal("}")
    }
    fn sid_attributes(&mut self,value:SidAttributes<'_>) -> Result<()> {
        self.literal("{\"sid\":")?;self.binary(value.sid)?;
        self.literal(",\"attributes\":")?;self.unsigned(u64::from(value.attributes))?;self.literal("}")
    }
    fn sid_array(&mut self,value:&[SidAttributes<'_>]) -> Result<()> {
        self.literal("[")?;
        for (index,value) in value.iter().enumerate() {if index!=0 {self.literal(",")?;}self.sid_attributes(*value)?;}
        self.literal("]")
    }
    fn token(&mut self,value:Token<'_>) -> Result<()> {
        self.literal("{\"type\":")?;self.unsigned(u64::from(value.token_type))?;
        self.literal(",\"impersonation_level\":")?;match value.impersonation_level {Some(x)=>self.unsigned(u64::from(x))?,None=>self.literal("null")?};
        self.literal(",\"user\":")?;self.binary(value.user)?;
        self.literal(",\"owner\":")?;self.binary(value.owner)?;
        self.literal(",\"primary_group\":")?;self.binary(value.primary_group)?;
        self.literal(",\"integrity\":")?;self.sid_attributes(value.integrity)?;
        self.literal(",\"groups\":")?;self.sid_array(value.groups)?;
        self.literal(",\"restricted_sids\":")?;self.sid_array(value.restricted_sids)?;
        self.literal(",\"capabilities\":")?;self.sid_array(value.capabilities)?;
        self.literal(",\"privileges\":[")?;
        for (index,privilege) in value.privileges.iter().enumerate() {
            if index!=0 {self.literal(",")?;}
            self.literal("{\"luid\":")?;self.luid(privilege.luid)?;
            self.literal(",\"name\":")?;self.string(privilege.name)?;
            self.literal(",\"attributes\":")?;self.unsigned(u64::from(privilege.attributes))?;self.literal("}")?;
        }
        self.literal("],\"token_id\":")?;self.luid(value.token_id)?;
        self.literal(",\"authentication_id\":")?;self.luid(value.authentication_id)?;
        self.literal(",\"modified_id\":")?;self.luid(value.modified_id)?;
        for (name,number) in [("session_id",value.session_id),("elevation_type",value.elevation_type),
            ("elevation",value.elevation),("has_restrictions",value.has_restrictions),
            ("is_app_container",value.is_app_container),("mandatory_policy",value.mandatory_policy),
            ("ui_access",value.ui_access),("virtualization_allowed",value.virtualization_allowed),
            ("virtualization_enabled",value.virtualization_enabled)] {
            self.literal(",")?;self.string(name)?;self.literal(":")?;self.unsigned(u64::from(number))?;
        }
        self.literal("}")
    }
    fn process(&mut self,value:Process<'_>) -> Result<()> {
        self.literal("{\"pid\":")?;self.unsigned(u64::from(value.pid))?;
        self.literal(",\"creation_utc\":")?;self.u64s(value.creation_utc)?;
        self.literal(",\"process_machine\":")?;self.unsigned(u64::from(value.process_machine))?;
        self.literal(",\"native_machine\":")?;self.unsigned(u64::from(value.native_machine))?;
        self.literal(",\"image_win32\":")?;self.path(value.image_win32)?;
        self.literal(",\"image_native\":")?;self.path(value.image_native)?;self.literal("}")
    }
    fn anchor(&mut self,value:Anchor<'_>) -> Result<()> {
        self.literal("{\"known_folder_id\":")?;self.string(value.known_folder_id)?;
        self.literal(",\"resolved_path\":")?;self.path(value.resolved_path)?;
        self.literal(",\"volume_guid\":")?;self.path(value.volume_guid)?;
        self.literal(",\"native_root\":")?;self.path(value.native_root)?;
        self.literal(",\"volume_serial64\":")?;self.u64s(value.volume_serial64)?;
        self.literal(",\"filesystem_serial32\":")?;self.unsigned(u64::from(value.filesystem_serial32))?;
        self.literal(",\"filesystem\":")?;self.string(value.filesystem)?;
        self.literal(",\"drive_type\":")?;self.unsigned(u64::from(value.drive_type))?;self.literal("}")
    }
    fn ancestor(&mut self,value:Ancestor<'_>) -> Result<()> {
        self.literal("{\"index\":")?;self.unsigned(u64::from(value.index))?;
        self.literal(",\"path\":")?;self.path(value.path)?;
        self.literal(",\"native_path\":")?;self.path(value.native_path)?;
        self.literal(",\"volume_serial64\":")?;self.u64s(value.volume_serial64)?;
        self.literal(",\"file_id\":")?;self.hex(&value.file_id)?;
        self.literal(",\"attributes\":")?;self.unsigned(u64::from(value.attributes))?;
        self.literal(",\"reparse_tag\":")?;self.unsigned(u64::from(value.reparse_tag))?;
        self.literal(",\"delete_pending\":")?;self.boolean(value.delete_pending)?;
        self.literal(",\"owner_dacl\":")?;self.binary(value.owner_dacl)?;
        self.literal(",\"policy_result\":")?;self.string(if value.policy_match {"match"} else {"refused"})?;self.literal("}")
    }
    fn error(&mut self,value:Error) -> Result<()> {
        self.literal("{\"kind\":")?;self.string(value.kind.as_str())?;
        self.literal(",\"phase\":")?;self.string(value.phase.as_str())?;
        self.literal(",\"operation\":")?;self.string(value.operation.as_str())?;
        self.literal(",\"domain\":")?;self.string(value.domain.as_str())?;
        self.literal(",\"code\":")?;match value.code {Some(x)=>self.unsigned(u64::from(x))?,None=>self.literal("null")?};
        self.literal(",\"reason\":")?;match value.reason {Some(x)=>self.string(x.as_str())?,None=>self.literal("null")?};
        self.literal(",\"ancestor_index\":")?;match value.ancestor_index {Some(x)=>self.unsigned(u64::from(x))?,None=>self.literal("null")?};
        self.literal(",\"completion\":")?;
        if let Some(value)=value.completion {
            self.literal("{\"call\":")?;self.unsigned(u64::from(value.call))?;
            self.literal(",\"io_status\":")?;self.unsigned(u64::from(value.io_status))?;
            self.literal(",\"information\":")?;self.u64s(value.information)?;self.literal("}")?;
        } else {self.literal("null")?;}
        self.literal("}")
    }
    fn receipt(&mut self,value:&Receipt<'_>,minimum:bool) -> Result<()> {
        self.literal("{\"schema\":\"hub_relay.bootstrap_inventory.v0.1\",\"mode\":\"diagnostic_only\",\"outcome\":")?;
        self.string(if minimum {"refused"} else {value.outcome.as_str()})?;
        self.literal(",\"activation\":\"blocked\",\"loaded_image_provenance\":\"not_established\",\"collector\":{\"source_commit\":")?;
        self.string(value.collector.source_commit)?;
        self.literal(",\"policy_sha256\":")?;self.string(value.collector.policy_sha256)?;
        self.literal(",\"target\":")?;self.string(value.collector.target)?;self.literal("}")?;
        self.literal(",\"started_utc\":")?;self.u64s(value.started_utc)?;
        self.literal(",\"finished_utc\":")?;self.u64s(value.finished_utc)?;
        self.literal(",\"elapsed_ms\":")?;self.u64s(value.elapsed_ms)?;
        self.literal(",\"process\":")?;
        if !minimum {if let Some(x)=value.process {self.process(x)?;} else {self.literal("null")?;}} else {self.literal("null")?;}
        self.literal(",\"primary_token\":")?;
        if !minimum {if let Some(x)=value.primary_token {self.token(x)?;} else {self.literal("null")?;}} else {self.literal("null")?;}
        self.literal(",\"thread_token\":")?;
        if !minimum {if let Some(x)=value.thread_token {self.token(x)?;} else {self.literal("null")?;}} else {self.literal("null")?;}
        self.literal(",\"thread_context\":")?;self.string(value.thread_context.as_str())?;
        self.literal(",\"anchor\":")?;
        if !minimum {if let Some(x)=value.anchor {self.anchor(x)?;} else {self.literal("null")?;}} else {self.literal("null")?;}
        self.literal(",\"ancestors\":")?;
        if !minimum {if let Some(values)=value.ancestors {
            self.literal("[")?;for (index,x) in values.iter().enumerate() {if index!=0 {self.literal(",")?;}self.ancestor(*x)?;}self.literal("]")?;
        } else {self.literal("null")?;}} else {self.literal("null")?;}
        self.literal(",\"recheck\":")?;self.string(value.recheck.as_str())?;
        self.literal(",\"product_collision\":\"not_observed\",\"service_collision\":\"not_observed\",\"service_sid_binding\":\"external_evidence_required\",\"errors\":[")?;
        for (index,error) in value.errors.iter().enumerate() {if index!=0 {self.literal(",")?;}self.error(*error)?;}
        self.literal("],\"cleanup\":")?;self.string(value.cleanup.as_str())?;self.literal("}")
    }
}

pub fn encoded_len(receipt:&Receipt<'_>) -> Result<usize> {
    validate(receipt)?;
    // Prove the complete retained-error envelope fits its independent reserve
    // before attempting the potentially much larger observation encoding.
    let mut minimum=Writer {output:None,at:0,limit:REFUSAL_RESERVE};
    minimum.receipt(receipt,true)?;
    let mut writer=Writer {output:None,at:0,limit:MAX_OUTPUT};
    writer.receipt(receipt,false)?;
    Ok(writer.at)
}

pub fn encode_into(receipt:&Receipt<'_>,output:&mut[u8]) -> Result<usize> {
    // Validation, exact escaped-byte counting, and capacity checks precede the
    // first output write. Invalid input and short output leave bytes untouched.
    let length=encoded_len(receipt)?;
    bounded(output.len()>=length)?;
    let mut writer=Writer {output:Some(output),at:0,limit:length};
    writer.receipt(receipt,false)?;
    require(writer.at==length)?;
    Ok(writer.at)
}
