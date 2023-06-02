#![allow(dead_code)]
#![allow(unused_assignments)]

mod configuration;
mod connection;
mod location;
mod model;
mod prediction;
mod retrieve;
mod tui;
mod utilities;

use clap::Parser;

lazy_static::lazy_static! {
    pub static ref DEFAULT_INTERVAL: chrono::Duration = chrono::Duration::seconds(60);
    pub static ref DATETIME_FORMAT: String = "%Y-%m-%d %H:%M:%S".to_string();
    pub static ref LOG_LEVEL: log::Level = log::Level::Debug;
}

#[derive(Parser)]
#[command(author, version, about, long_about = None)]
struct PacketravenCommand {
    // configuration file to read
    config_file: std::path::PathBuf,
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let arguments = PacketravenCommand::parse();

    let configuration_file = std::fs::File::open(arguments.config_file).unwrap();
    let configuration: crate::configuration::RunConfiguration =
        serde_yaml::from_reader(configuration_file).expect("error reading configuration");

    tui::run(configuration, *LOG_LEVEL)?;
    Ok(())
}
