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
    #[command(subcommand)]
    command: Command,
}

#[derive(clap::Subcommand)]
enum Command {
    /// run program from configuration
    Start {
        /// file path to configuration
        config_file: std::path::PathBuf,
    },
    /// retrieve a balloon prediction from the given API - negative values must be preceded with a `-- `, i.e. `-- -79`
    Predict {
        /// start time i.e. `2023-08-16T10:00:00`
        time: chrono::NaiveDateTime,
        /// start longitude
        longitude: f64,
        /// start latitude
        latitude: f64,
        /// start altitude
        #[arg(short, long)]
        altitude: Option<f64>,
        /// expected average ascent rate
        ascent_rate: f64,
        /// expected burst altitude
        burst_altitude: f64,
        /// descent rate at sea level
        sea_level_descent_rate: f64,
        /// desired float altitude
        #[arg(long)]
        float_altitude: Option<f64>,
        /// desired float duration in seconds
        #[arg(long)]
        float_duration: Option<f64>,
    },
    /// write an empty configuration file
    Write {
        /// file path to configuration
        filename: std::path::PathBuf,
    },
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let arguments = PacketravenCommand::parse();

    match arguments.command {
        Command::Start { config_file } => {
            let file = std::fs::File::open(config_file).unwrap();
            let configuration: crate::configuration::RunConfiguration =
                serde_yaml::from_reader(file).expect("error reading configuration");

            tui::run(configuration, *LOG_LEVEL)?;
            Ok(())
        }
        Command::Predict {
            time,
            longitude,
            latitude,
            altitude,
            ascent_rate,
            burst_altitude,
            sea_level_descent_rate,
            float_altitude,
            float_duration,
        } => {
            let start = location::Location {
                time: time.and_local_timezone(chrono::Local).unwrap(),
                coord: geo::coord! {x:longitude,y:latitude},
                altitude,
            };
            let profile = prediction::FlightProfile::new(
                ascent_rate,
                float_altitude,
                match float_duration {
                    Some(seconds) => Some(chrono::Duration::seconds(seconds as i64)),
                    None => None,
                },
                None,
                burst_altitude,
                sea_level_descent_rate,
            );

            let query = prediction::tawhiri::TawhiriQuery::new(
                &start, &profile, None, None, None, false, None,
            );

            match query.retrieve_prediction() {
                Ok(prediction) => {
                    for location in prediction {
                        println!(
                            "{:}, {:.1}, {:.1}, {:.1}",
                            location.location.time.format("%Y-%m-%d %H:%M:%S"),
                            location.location.coord.x,
                            location.location.coord.y,
                            location.location.altitude.unwrap_or(0.0)
                        );
                    }
                }
                Err(error) => return Err(Box::new(error)),
            }

            Ok(())
        }
        Command::Write { filename } => {
            let configuration = configuration::RunConfiguration::default();
            let file = std::fs::File::create(filename).unwrap();

            serde_yaml::to_writer(file, &configuration).unwrap();
            Ok(())
        }
    }
}
