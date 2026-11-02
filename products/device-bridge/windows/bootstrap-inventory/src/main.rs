use std::io;
fn main(){
 if std::env::args_os().count()!=1{eprintln!("HUB_Relay diagnostic accepts no arguments.");std::process::exit(2);}
 let result=bootstrap_inventory::collector::run_to(&mut io::stdout().lock());
 if result.is_err(){eprintln!("HUB_Relay diagnostic delivery incomplete.");std::process::exit(2);}
}
