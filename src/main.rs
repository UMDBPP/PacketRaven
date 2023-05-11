pub mod configuration;
pub mod connection;
pub mod location;
pub mod model;
mod parse;
pub mod prediction;

use clap::Parser;

use env_logger::{Builder, Target};
use log::{debug, error, info, warn};

#[derive(Parser)]
#[command(author, version, about, long_about = None)]
struct Cli {
    // configuration file to read
    configuration_filename: std::path::PathBuf,

    // start graphical interface
    #[arg(long, default_value_t = false)]
    gui: bool,
}

fn main() {
    if std::env::var("RUST_LOG").is_err() {
        std::env::set_var("RUST_LOG", "info")
    }
    let mut builder = Builder::from_default_env();
    builder.target(Target::Stdout);

    builder.init();

    let program_start_time = chrono::Local::now();

    let arguments = Cli::parse();
    if arguments.gui {
        // TODO
        unimplemented!("GUI not implemented");
    }

    let configuration_file = std::fs::File::open(arguments.configuration_filename).unwrap();
    let configuration: crate::configuration::RunConfiguration =
        serde_yaml::from_reader(configuration_file).unwrap();

    if let Some(output) = &configuration.log {
        // TODO
        warn!("logging to file is not implemented");
        let mut filename: std::path::PathBuf;
        if output.filename.is_file() {
            filename = output.filename.to_owned();
        } else {
            filename = std::path::PathBuf::from(".");
            filename.push(format!(
                "{:}_log_{:}.txt",
                configuration.name,
                program_start_time.to_rfc3339(),
            ));
        }
    }

    if let Some(output) = &configuration.output {
        // TODO
        warn!("file output is not implemented");
        let mut filename: std::path::PathBuf;
        if output.filename.is_file() {
            filename = output.filename.to_owned();
        } else {
            filename = std::path::PathBuf::from(".");
            filename.push(format!(
                "{:}_{:}.geojson",
                configuration.name,
                program_start_time.to_rfc3339()
            ));
        }
    }

    if let Some(output) = &configuration.output {
        // TODO
        warn!("file output is not implemented");
        let mut filename: std::path::PathBuf;
        if output.filename.is_file() {
            filename = output.filename.to_owned();
        } else {
            filename = std::path::PathBuf::from(".");
            filename.push(format!(
                "{:}_predict_{:}.geojson",
                configuration.name,
                program_start_time.to_rfc3339()
            ));
        }
    }

    let mut filter_message = String::from("retrieving packets");
    if let Some(start) = configuration.time.start {
        if let Some(end) = configuration.time.end {
            filter_message += &format!(
                " sent between {:} and {:}",
                start.to_rfc3339(),
                end.to_rfc3339()
            );
        } else {
            filter_message += &format!(" sent after {:}", start.to_rfc3339(),);
        }
    } else if let Some(end) = configuration.time.end {
        filter_message += &format!(" sent before {:}", end.to_rfc3339());
    }

    if let Some(callsigns) = &configuration.callsigns {
        if !callsigns.is_empty() {
            filter_message += &format!(
                " from {:} callsign(s): {:}",
                callsigns.len(),
                callsigns.join(", ")
            );
        }
    }

    info!("{:}", filter_message);

    if let Some(callsigns) = &configuration.callsigns {
        if !callsigns.is_empty() {
            let mut aprs_fi_url =
                format!("https://aprs.fi/#!call=a%2F{:}", callsigns.join("%2Ca%2F"));
            if let Some(start) = configuration.time.start {
                aprs_fi_url += &format!("&ts={:}", start.timestamp());
            }
            if let Some(end) = configuration.time.end {
                aprs_fi_url += &format!("&te={:}", end.timestamp());
            }
            info!("tracking URL: {:}", aprs_fi_url);
        }
    }

    let mut connections: Vec<crate::connection::Connection> = vec![];

    if let Some(text_configuration) = &configuration.packets.text {
        for location in &text_configuration.locations {
            let connection: crate::connection::Connection;
            if ["txt", "log"].contains(&location.extension().unwrap().to_str().unwrap()) {
                connection =
                    connection::Connection::AprsTextFile(crate::connection::file::AprsTextFile {
                        path: location.to_owned(),
                    });
                info!("reading text file {:}", &location.to_str().unwrap());
            } else if ["json", "geojson"].contains(&location.extension().unwrap().to_str().unwrap())
            {
                connection =
                    connection::Connection::GeoJsonFile(crate::connection::file::GeoJsonFile {
                        path: location.to_owned(),
                    });
                info!("reading GeoJSON file {:}", &location.to_str().unwrap());
            } else {
                #[cfg(feature = "serial")]
                {
                    let port = location.to_str().unwrap();
                    connection = connection::Connection::AprsSerial(
                        crate::connection::serial::AprsSerial::new(
                            if port == "auto" {
                                None
                            } else {
                                Some(String::from(port))
                            },
                            Some(9600),
                        ),
                    );
                    info!("opened port {:}", &location.to_str().unwrap());
                }
            }
            connections.push(connection);
        }
    }

    if let Some(aprs_fi_configuration) = &configuration.packets.aprs_fi {
        let connection =
            crate::connection::Connection::AprsFi(crate::connection::aprs_fi::AprsFiQuery::new(
                configuration
                    .callsigns
                    .to_owned()
                    .expect("APRS.fi requires a list of callsigns"),
                aprs_fi_configuration.api_key.to_owned(),
                None,
                None,
            ));
        connections.push(connection);
    }

    #[cfg(feature = "postgres")]
    if let Some(database_configuration) = configuration.packets.database {
        let connection = crate::connection::Connection::PacketDatabase(
            crate::connection::postgres::PacketDatabase::from_credentials(&database_configuration),
        );
        connections.push(connection);
    }

    if connections.is_empty() {
        if let Some(output) = configuration.output {
            if output.filename.exists() {
                let connection =
                    connection::Connection::GeoJsonFile(crate::connection::file::GeoJsonFile {
                        path: output.filename,
                    });
                connections.push(connection);
            }
        } else {
            error!("no connections successfully started");
            std::process::exit(1);
        }
    }

    if let Some(aprs_is_configuration) = configuration.packets.aprs_is {
        // TODO
        unimplemented!("APRS IS connection is not implemented");
    }

    info!(
        "listening for packets every {:} s from {:} source(s)",
        configuration.time.interval.num_seconds(),
        connections.len(),
    );

    let mut packet_tracks =
        std::collections::HashMap::<String, crate::location::track::BalloonTrack>::new();
    let mut predictions =
        std::collections::HashMap::<String, crate::location::track::BalloonTrack>::new();

    if let Some(plots_configuration) = configuration.plots {
        // TODO
        unimplemented!("plotting is not implemented");
    }

    loop {
        retrieve_locations(
            &mut connections,
            &mut packet_tracks,
            configuration.time.start,
            configuration.time.end,
        );

        if let Some(crate::configuration::prediction::PredictionConfiguration::Single(
            prediction_configuration,
        )) = &configuration.prediction
        {
            retrieve_predictions(
                &mut predictions,
                &packet_tracks,
                &prediction_configuration.to_tawhiri_query().query.profile,
            );
        }

        std::thread::sleep(configuration.time.interval.to_std().unwrap());
    }
}

fn retrieve_locations(
    connections: &mut Vec<crate::connection::Connection>,
    packet_tracks: &mut std::collections::HashMap<String, crate::location::track::BalloonTrack>,
    start_time: Option<chrono::DateTime<chrono::Local>>,
    end_time: Option<chrono::DateTime<chrono::Local>>,
) {
    let mut new_packets: Vec<crate::location::BalloonLocation> = vec![];

    for connection in connections {
        match connection.retrieve_packets() {
            Ok(packets) => new_packets.extend(packets),
            Err(error) => {
                error!("{:}", error);
                std::process::exit(1)
            }
        }
    }

    let num_new_packets = new_packets.len();
    debug!("received {:} packets", num_new_packets);

    if !new_packets.is_empty() {
        let mut packet_track_lengths = std::collections::HashMap::<String, usize>::new();
        for (name, track) in packet_tracks.iter() {
            packet_track_lengths.insert(name.to_owned(), track.locations.len());
        }

        let mut duplicates: usize = 0;
        let mut time_lagged_duplicates: usize = 0;
        let mut skipped: usize = 0;

        let mut track: &mut crate::location::track::BalloonTrack;
        for mut packet in new_packets {
            if let Some(start_time) = start_time {
                if packet.time < start_time {
                    debug!(
                        "skipped packet from before {:?}; {:?}",
                        start_time, packet.time
                    );
                    skipped += 1;
                    continue;
                }
            }

            if let Some(end_time) = end_time {
                if packet.time > end_time {
                    debug!(
                        "skipped packet from after {:?}; {:?}",
                        end_time, packet.time
                    );
                    skipped += 1;
                    continue;
                }
            }

            let name: String;
            if let Some(aprs_packet) = &packet.data.aprs_packet {
                name = match aprs_packet.from.ssid() {
                    Some(ssid) => format!("{:}-{:}", aprs_packet.from.call(), ssid),
                    None => String::from(aprs_packet.from.call()),
                };
            } else {
                name = String::from("other");
            }

            track = match packet_tracks.get_mut(&name) {
                Some(track) => track,
                None => {
                    debug!("started track {:}", &name);
                    packet_track_lengths.insert(name.to_owned(), 0);
                    packet_tracks
                        .entry(name.to_owned())
                        .or_insert(crate::location::track::BalloonTrack::new(name.to_owned()))
                }
            };

            for existing_packet in &track.locations {
                if packet.eq(existing_packet) {
                    packet.data.status = crate::location::PacketStatus::Duplicate;
                } else if packet.time_lag_of(existing_packet) {
                    packet.data.status = crate::location::PacketStatus::TimeLaggedDuplicate;
                }
            }

            match packet.data.status {
                crate::location::PacketStatus::Duplicate => {
                    duplicates += 1;
                    debug!("skipped time-lagged duplicate packet");
                    continue;
                }
                crate::location::PacketStatus::TimeLaggedDuplicate => {
                    time_lagged_duplicates += 1;
                    debug!("skipped duplicate packet");
                    continue;
                }
                _ => {
                    track.push(packet);
                }
            }

            debug!("{:}", location_update(track));
        }

        info!(
            "received {:} new packets",
            num_new_packets - duplicates - skipped - time_lagged_duplicates
        );

        for (name, track) in packet_tracks {
            if track.locations.len() - packet_track_lengths.get(name).unwrap() > 0 {
                info!("{:}", track_update(track));
            }
        }
    }
}

fn location_update(track: &crate::location::track::BalloonTrack) -> String {
    let current_location = match track.locations.last() {
        Some(location) => location,
        None => {
            panic!(
                "tried to log update for track with length {:?}",
                track.locations.len()
            )
        }
    };

    let intervals = track.intervals();
    let overground_distances = track.overground_distances();
    let ground_speeds = track.ground_speeds();
    let ascents = track.ascents();
    let ascent_rates = track.ascent_rates();

    let mut message = format!("{: <8} - location #{:}", track.name, track.locations.len());
    message += &format!(
        " ({:.2}, {:.2}",
        &current_location.location.x(),
        &current_location.location.y(),
    );
    if let Some(altitude) = current_location.altitude {
        message += &format!(", {:.2} m", altitude,)
    };
    message += &String::from(")");

    message += &format!("; packet time is {:}", current_location.time.to_rfc3339());

    if track.locations.len() > 1 {
        message += &format!(
            " ({:.2} s since the previous packet); traveled {:.2} m ({:.2} m/s) over the ground and {:.2} m ({:.2} m/s) vertically",
            intervals.last().unwrap().num_seconds(),
            overground_distances.last().unwrap(),
            ground_speeds.last().unwrap(),
            ascents.last().unwrap(),
            ascent_rates.last().unwrap(),
        );
    }

    message
}

fn track_update(track: &crate::location::track::BalloonTrack) -> String {
    let current_location = track.locations.last().unwrap();

    let intervals = track.intervals();
    let ground_speeds = track.ground_speeds();
    let ascent_rates = track.ascent_rates();

    let mut message = format!(
        "{: <8} - {:} packets - current altitude: {:.2} m",
        track.name,
        track.locations.len(),
        current_location.altitude.unwrap()
    );

    if track.locations.len() > 1 {
        let mut positive_ascent_rates = vec![];
        let mut negative_ascent_rates = vec![];
        for ascent_rate in ascent_rates {
            if ascent_rate > 0.0 {
                positive_ascent_rates.push(ascent_rate);
            } else {
                negative_ascent_rates.push(ascent_rate);
            }
        }

        let mut total_interval = chrono::Duration::seconds(0);
        for interval in &intervals {
            total_interval = total_interval + interval.to_owned();
        }
        message += &format!(
            " - avg. ascent rate: {:.2} m/s - avg. descent rate: {:.2} m/s - avg. ground speed: {:.2} m/s - avg. packet interval: {:.2} s",
            positive_ascent_rates.iter().sum::<f64>() / positive_ascent_rates.len() as f64,
            negative_ascent_rates.iter().sum::<f64>() / negative_ascent_rates.len() as f64,
            ground_speeds.iter().sum::<f64>() / ground_speeds.len() as f64,
            total_interval.num_seconds() as f64 / intervals.len() as f64,
        );
    }

    if let Some(time_to_ground) = track.time_to_ground() {
        let landing_time = current_location.time + time_to_ground;
        let time_to_landing = chrono::Local::now() - landing_time;
        let mut altitudes = vec![];
        for location in &track.locations {
            if let Some(altitude) = location.altitude {
                altitudes.push(altitude)
            }
        }
        message += &format!(
            " - max altitude: {:.2} - estimated landing: {:} ({:})",
            altitudes.iter().max_by(|a, b| a.total_cmp(b)).unwrap(),
            landing_time.to_rfc3339(),
            time_to_landing,
        );
    }

    message
}

fn retrieve_predictions(
    predictions: &mut std::collections::HashMap<String, crate::location::track::BalloonTrack>,
    packet_tracks: &std::collections::HashMap<String, crate::location::track::BalloonTrack>,
    profile: &crate::prediction::FlightProfile,
) {
    for (name, track) in packet_tracks {
        let prediction = track.prediction(profile);

        if track.falling().is_some() || track.descending() {
            let landing_location = prediction.locations.last().unwrap().location.x_y();
            info!(
                "{:} - predicted landing location: ({:.2}, {:.2})",
                track.name, landing_location.0, landing_location.1
            );
        }
        predictions.insert(name.to_owned(), prediction);
    }
}
