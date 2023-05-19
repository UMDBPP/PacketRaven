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

        let mut duplicates: usize = 0;
        let mut time_lagged_duplicates: usize = 0;
        let mut skipped: usize = 0;

        let mut track: &mut crate::location::track::BalloonTrack;
        for mut packet in new_packets {
            if let Some(start_time) = start_time {
                if packet.time < start_time {
                    messages.push((
                        chrono::Local::now(),
                        format!(
                            "skipped packet from before {:?}; {:?}",
                            start_time, packet.time
                        ),
                        log::Level::Debug,
                    ));
                    skipped += 1;
                    continue;
                }
            }

            if let Some(end_time) = end_time {
                if packet.time > end_time {
                    messages.push((
                        chrono::Local::now(),
                        format!(
                            "skipped packet from after {:?}; {:?}",
                            end_time, packet.time
                        ),
                        log::Level::Debug,
                    ));
                    skipped += 1;
                    continue;
                }
            }

            let name = match &packet.data.aprs_packet {
                Some(aprs_packet) => match &aprs_packet.from.ssid() {
                    Some(ssid) => format!("{:}-{:}", aprs_packet.from.call(), ssid),
                    None => aprs_packet.from.call().to_owned(),
                },
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
                    tracks.push(crate::location::track::BalloonTrack::new(
                        name.to_owned(),
                        None,
                    ));
                    tracks.last_mut().unwrap()
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
                    messages.push((
                        chrono::Local::now(),
                        "skipped duplicate packet".to_string(),
                        log::Level::Debug,
                    ));
                    continue;
                }
                crate::location::PacketStatus::TimeLaggedDuplicate => {
                    time_lagged_duplicates += 1;
                    messages.push((
                        chrono::Local::now(),
                        "skipped time-lagged duplicate packet".to_string(),
                        log::Level::Debug,
                    ));
                    continue;
                }
                _ => {
                    track.push(packet);
                }
            }

            messages.push((
                chrono::Local::now(),
                location_update(track),
                log::Level::Debug,
            ));
        }

        messages.push((
            chrono::Local::now(),
            format!(
                "received {:} new packets",
                num_new_packets - duplicates - skipped - time_lagged_duplicates,
            ),
            log::Level::Debug,
        ));

        for track in tracks {
            if track.locations.len() - packet_track_lengths.get(&track.name.to_owned()).unwrap() > 0
            {
                messages.push((chrono::Local::now(), track_update(&track), log::Level::Info));
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

    let intervals = track.intervals();
    let overground_distances = track.overground_distances();
    let ground_speeds = track.ground_speeds();
    let ascents = track.ascents();
    let ascent_rates = track.ascent_rates();

    let mut message = format!("{: <8} - location #{:}", track.name, track.locations.len());
    message += &format!(
        " ({:.2}, {:.2}",
        &last_location.location.x(),
        &last_location.location.y(),
    );
    if let Some(altitude) = last_location.altitude {
        message += &format!(", {:.2} m", altitude,)
    };
    message += &String::from(")");

    message += &format!("; packet time is {:}", last_location.time.to_rfc3339());

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
    let last_location = track.locations.last().unwrap();

    let intervals = track.intervals();
    let ground_speeds = track.ground_speeds();
    let ascent_rates = track.ascent_rates();

    let mut message = format!(
        "{: <8} - {:} packets - current altitude: {:.2} m",
        track.name,
        track.locations.len(),
        last_location.altitude.unwrap()
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

    if let Some(time_to_ground) = track.estimated_time_to_ground() {
        let landing_time = last_location.time + time_to_ground;
        let time_to_ground_from_now = landing_time - chrono::Local::now();
        let mut altitudes = vec![];
        for location in &track.locations {
            if let Some(altitude) = location.altitude {
                altitudes.push(altitude)
            }
        }
        message += &format!(
            " - max altitude: {:.2} - estimated landing: {:} s ({:})",
            altitudes.iter().max_by(|a, b| a.total_cmp(b)).unwrap(),
            time_to_ground_from_now.num_seconds(),
            landing_time.format("%Y-%m-%d %H:%M:%S"),
        );
    }

    message
}
