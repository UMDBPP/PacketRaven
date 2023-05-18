#![allow(dead_code)]
#![allow(unused_variables)]

mod configuration;
mod connection;
mod location;
mod model;
mod parse;
mod prediction;
mod retrieve;
mod tui;

use clap::Parser;

#[derive(Parser)]
#[command(author, version, about, long_about = None)]
struct Cli {
    // configuration file to read
    configuration_filename: std::path::PathBuf,

    // start graphical interface
    #[arg(long, default_value_t = false)]
    gui: bool,
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let arguments = Cli::parse();
    if arguments.gui {
        // TODO
        unimplemented!("GUI not implemented");
    }

    let configuration_file = std::fs::File::open(arguments.configuration_filename).unwrap();
    let configuration: crate::configuration::RunConfiguration =
        serde_yaml::from_reader(configuration_file).unwrap();

    tui::run(&configuration, log::Level::Info)?;
    Ok(())
}
