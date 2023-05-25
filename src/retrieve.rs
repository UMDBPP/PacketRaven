pub fn retrieve_locations(
    connections: &mut Vec<crate::connection::Connection>,
    tracks: &mut Vec<crate::location::track::BalloonTrack>,
    start_time: Option<chrono::DateTime<chrono::Local>>,
    end_time: Option<chrono::DateTime<chrono::Local>>,
) -> Vec<(chrono::DateTime<chrono::Local>, String, log::Level)> {
    let mut new_packets: Vec<crate::location::BalloonLocation> = vec![];
    let mut messages = Vec::<(chrono::DateTime<chrono::Local>, String, log::Level)>::new();

    for connection in connections {
        match connection.retrieve_packets() {
            Ok(packets) => new_packets.extend(packets),
            Err(error) => {
                messages.push((chrono::Local::now(), error.to_string(), log::Level::Error));
            }
        }
    }

    let num_new_packets = new_packets.len();
    messages.push((
        chrono::Local::now(),
        format!("received {:} packets", num_new_packets),
        log::Level::Debug,
    ));

    if !new_packets.is_empty() {
        let mut packet_track_lengths = std::collections::HashMap::<String, usize>::new();
        for track in tracks.iter() {
            packet_track_lengths.insert(track.name.to_owned(), track.locations.len());
        }

        let mut num_duplicates: usize = 0;
        let mut num_time_lagged_duplicates: usize = 0;

        let mut track: &mut crate::location::track::BalloonTrack;
        for mut packet in new_packets {
            if let Some(start_time) = start_time {
                if packet.location.time < start_time {
                    messages.push((
                        chrono::Local::now(),
                        format!(
                            "skipped packet from before {:?}; {:?}",
                            start_time, packet.location.time
                        ),
                        log::Level::Debug,
                    ));
                    continue;
                }
            }

            if let Some(end_time) = end_time {
                if packet.location.time > end_time {
                    messages.push((
                        chrono::Local::now(),
                        format!(
                            "skipped packet from after {:?}; {:?}",
                            end_time, packet.location.time
                        ),
                        log::Level::Debug,
                    ));
                    continue;
                }
            }

            let name = match &packet.data.callsign {
                Some(callsign) => callsign.to_owned(),
                None => "other".to_owned(),
            };

            track = match tracks.iter_mut().find(|track| track.name == name) {
                Some(track) => track,
                _ => {
                    messages.push((
                        chrono::Local::now(),
                        format!("started track {:}", &name),
                        log::Level::Debug,
                    ));
                    packet_track_lengths.insert(name.to_owned(), 0);
                    tracks.push(crate::location::track::BalloonTrack::new(name.to_owned()));
                    tracks.last_mut().unwrap()
                }
            };

            for existing_packet in &track.locations {
                if packet.eq(existing_packet) {
                    packet.data.status = crate::location::PacketStatus::Duplicate;
                } else if packet.location.time_lag_of(&existing_packet.location) {
                    packet.data.status = crate::location::PacketStatus::TimeLaggedDuplicate;
                }
            }

            match packet.data.status {
                crate::location::PacketStatus::Duplicate => {
                    num_duplicates += 1;
                    continue;
                }
                crate::location::PacketStatus::TimeLaggedDuplicate => {
                    num_time_lagged_duplicates += 1;
                    continue;
                }
                _ => {
                    track.push(packet);
                }
            }
        }

        if num_duplicates > 0 {
            messages.push((
                chrono::Local::now(),
                format!("skipped {:} duplicate packet(s)", num_duplicates),
                log::Level::Debug,
            ));
        }

        if num_time_lagged_duplicates > 0 {
            messages.push((
                chrono::Local::now(),
                format!(
                    "skipped {:} time-lagged duplicate packet(s)",
                    num_time_lagged_duplicates
                ),
                log::Level::Debug,
            ));
        }

        for track in tracks {
            if track.locations.len() - packet_track_lengths.get(&track.name.to_owned()).unwrap() > 0
            {
                messages.push((
                    chrono::Local::now(),
                    format!("{:} - {:} packets", track.name, track.locations.len()),
                    log::Level::Info,
                ));
            }
        }
    }

    messages
}

fn location_update(track: &crate::location::track::BalloonTrack) -> String {
    let last_location = match track.locations.last() {
        Some(location) => location,
        None => {
            panic!(
                "tried to log update for track with length {:?}",
                track.locations.len()
            )
        }
    };

    let intervals = crate::location::track::intervals(&track.locations);
    let overground_distances = crate::location::track::overground_distances(&track.locations);
    let ground_speeds = crate::location::track::ground_speeds(&track.locations);
    let ascents = crate::location::track::ascents(&track.locations);
    let ascent_rates = crate::location::track::ascent_rates(&track.locations);

    let mut message = format!("{: <8} - location #{:}", track.name, track.locations.len());
    message += &format!(
        " ({:.2}, {:.2}",
        &last_location.location.coord.x, &last_location.location.coord.y,
    );
    if let Some(altitude) = last_location.location.altitude {
        message += &format!(", {:.2} m", altitude,)
    };
    message += &String::from(")");

    message += &format!(
        "; packet time is {:}",
        last_location.location.time.format(&crate::DATETIME_FORMAT)
    );

    if track.locations.len() > 1 {
        message += &format!(
            " ({:.2} since the previous packet); traveled {:.2} m ({:.2} m/s) over the ground and {:.2} m ({:.2} m/s) vertically",
            crate::utilities::duration_string(intervals.last().unwrap()),
            overground_distances.last().unwrap(),
            ground_speeds.last().unwrap(),
            ascents.last().unwrap(),
            ascent_rates.last().unwrap(),
        );
    }

    message
}

fn track_update(track: &crate::location::track::BalloonTrack) -> String {
    let last_location = track.locations.last().unwrap();

    let intervals = crate::location::track::intervals(&track.locations);
    let ground_speeds = crate::location::track::ground_speeds(&track.locations);
    let ascent_rates = crate::location::track::ascent_rates(&track.locations);

    let mut message = format!(
        "{: <8} - {:} packets - current altitude: {:.2} m",
        track.name,
        track.locations.len(),
        last_location.location.altitude.unwrap()
    );

    if track.locations.len() > 1 {
        let positive_ascent_rates: Vec<f64> = ascent_rates
            .iter()
            .filter(|rate| rate > &&0.0)
            .map(|rate| rate.to_owned())
            .collect();
        let negative_ascent_rates: Vec<f64> = ascent_rates
            .iter()
            .filter(|rate| rate < &&0.0)
            .map(|rate| rate.to_owned())
            .collect();

        let duration = intervals
            .iter()
            .fold(chrono::Duration::zero(), |sum, duration| sum + *duration);

        message += &format!(
            " - avg. ascent rate: {:.2} m/s - avg. descent rate: {:.2} m/s - avg. ground speed: {:.2} m/s - avg. packet interval: {:.2} s",
            positive_ascent_rates.iter().sum::<f64>() / positive_ascent_rates.len() as f64,
            negative_ascent_rates.iter().sum::<f64>() / negative_ascent_rates.len() as f64,
            ground_speeds.iter().sum::<f64>() / ground_speeds.len() as f64,
            duration.num_seconds() as f64 / intervals.len() as f64,
        );
    }

    if let Some(time_to_ground) = track.estimated_time_to_ground() {
        let landing_time = last_location.location.time + time_to_ground;
        let time_to_ground_from_now = landing_time - chrono::Local::now();
        let mut altitudes = vec![];
        for location in &track.locations {
            if let Some(altitude) = location.location.altitude {
                altitudes.push(altitude)
            }
        }
        message += &format!(
            " - max altitude: {:.2} - estimated landing: {:} s ({:})",
            altitudes.iter().max_by(|a, b| a.total_cmp(b)).unwrap(),
            time_to_ground_from_now.num_seconds(),
            landing_time.format(&crate::DATETIME_FORMAT),
        );
    }

    message
}
