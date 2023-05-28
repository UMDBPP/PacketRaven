pub struct PacketravenApp {
    pub configuration: crate::configuration::RunConfiguration,
    pub connections: Vec<crate::connection::Connection>,
    pub tracks: Vec<crate::location::track::BalloonTrack>,
    pub tab_index: usize,
    pub chart_index: usize,
    pub log_messages: Vec<(chrono::DateTime<chrono::Local>, String, log::Level)>,
    pub log_messages_scroll_offset: u16,
    pub log_level: log::Level,
    pub should_quit: bool,
}

impl PacketravenApp {
    pub fn new(
        configuration: crate::configuration::RunConfiguration,
        log_level: log::Level,
    ) -> PacketravenApp {
        let program_start_time = chrono::Local::now();

        let mut configuration = configuration;
        let mut log_messages = vec![];
        let mut connections = vec![];
        let mut tracks = vec![];

        if let Some(path) = &mut configuration.log_file {
            // TODO
            log_messages.push((
                chrono::Local::now(),
                "logging to file is not implemented".to_owned(),
                log::Level::Warn,
            ));
            if path.is_dir() {
                path.push(format!(
                    "{:}_log_{:}.txt",
                    configuration.name,
                    program_start_time.format(&crate::DATETIME_FORMAT),
                ));
            }
        }

        if let Some(path) = &mut configuration.output_file {
            if path.is_dir() {
                path.push(format!(
                    "{:}_{:}.geojson",
                    configuration.name,
                    program_start_time.format(&crate::DATETIME_FORMAT)
                ));
            }
            // read from an existing output file
            if path.exists() {
                log_messages.push((
                    chrono::Local::now(),
                    format!("reading existing output file: {:}", path.to_string_lossy()),
                    log::Level::Debug,
                ));
                crate::retrieve::retrieve_locations(
                    &mut vec![crate::connection::Connection::GeoJsonFile(
                        crate::connection::text::file::GeoJsonFile {
                            path: format!("{:}", path.to_string_lossy()),
                        },
                    )],
                    &mut tracks,
                    configuration.time.start,
                    configuration.time.end,
                );
            }
        }

        if let Some(prediction) = &mut configuration.prediction {
            match prediction {
                crate::configuration::prediction::PredictionConfiguration::Single(prediction) => {
                    if let Some(path) = &mut prediction.output_file {
                        if path.is_dir() {
                            path.push(format!(
                                "{:}_predict_{:}.geojson",
                                configuration.name,
                                program_start_time.format(&crate::DATETIME_FORMAT)
                            ));
                        }
                    }
                }
                crate::configuration::prediction::PredictionConfiguration::Cloud { .. } => {
                    log_messages.push((
                        chrono::Local::now(),
                        "cloud prediction not implemented".to_string(),
                        log::Level::Error,
                    ))
                }
            }
        }

        let mut filter_message = "retrieving packets".to_string();
        if let Some(start) = configuration.time.start {
            if let Some(end) = configuration.time.end {
                filter_message += &format!(
                    " sent between {:} and {:}",
                    start.format(&crate::DATETIME_FORMAT),
                    end.format(&crate::DATETIME_FORMAT)
                );
            } else {
                filter_message +=
                    &format!(" sent after {:}", start.format(&crate::DATETIME_FORMAT),);
            }
        } else if let Some(end) = configuration.time.end {
            filter_message += &format!(" sent before {:}", end.format(&crate::DATETIME_FORMAT));
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

        log_messages.push((chrono::Local::now(), filter_message, log::Level::Info));

        if let Some(callsigns) = &configuration.callsigns.to_owned() {
            if !callsigns.is_empty() {
                let mut aprs_fi_url =
                    format!("https://aprs.fi/#!call=a%2F{:}", callsigns.join("%2Ca%2F"));
                if let Some(start) = configuration.time.start {
                    aprs_fi_url += &format!("&ts={:}", start.timestamp());
                }
                if let Some(end) = configuration.time.end {
                    aprs_fi_url += &format!("&te={:}", end.timestamp());
                }
                log_messages.push((
                    chrono::Local::now(),
                    format!("tracking: {:}", aprs_fi_url),
                    log::Level::Info,
                ));

                let mut sondehub_url =
                    format!("https://amateur.sondehub.org/#!q={:}", callsigns.join(","));
                if let Some(start) = configuration.time.start {
                    let duration = chrono::Local::now() - start;
                    sondehub_url += &if duration < chrono::Duration::days(1) {
                        format!("&qm={:}d", duration.num_days())
                    } else {
                        format!("&qm={:}h", duration.num_hours())
                    }
                }

                log_messages.push((
                    chrono::Local::now(),
                    format!("tracking: {:}", sondehub_url),
                    log::Level::Info,
                ));
            }
        }

        if let Some(text_configuration) = &configuration.connections.text.to_owned() {
            for text_stream in text_configuration {
                let connection = match text_stream {
                    crate::connection::text::TextStream::GeoJsonFile(connection) => {
                        let connection = connection.to_owned();
                        log_messages.push((
                            chrono::Local::now(),
                            format!("reading GeoJSON file: {:}", connection.path),
                            log::Level::Info,
                        ));

                        crate::connection::Connection::GeoJsonFile(connection)
                    }
                    crate::connection::text::TextStream::AprsTextFile(connection) => {
                        let mut connection = connection.to_owned();
                        if connection.callsigns.is_none() {
                            if let Some(callsigns) = &configuration.callsigns {
                                connection.callsigns = Some(callsigns.to_owned());
                            }
                        }
                        log_messages.push((
                            chrono::Local::now(),
                            format!("reading text file of APRS frames: {:}", connection.path),
                            log::Level::Info,
                        ));
                        crate::connection::Connection::AprsTextFile(connection)
                    }
                    #[cfg(feature = "serial")]
                    crate::connection::text::TextStream::AprsSerial(connection) => {
                        let mut connection = connection.to_owned();
                        if connection.callsigns.is_none() {
                            if let Some(callsigns) = &configuration.callsigns {
                                connection.callsigns = Some(callsigns.to_owned());
                            }
                        }
                        crate::connection::Connection::AprsSerial(connection)
                    }
                };
                connections.push(connection);
            }
        }

        #[cfg(feature = "aprsfi")]
        if let Some(aprs_fi_query) = &configuration.connections.aprs_fi {
            if let Some(callsigns) = &configuration.callsigns {
                let mut connection = aprs_fi_query.to_owned();
                if connection.callsigns.is_none() {
                    connection.callsigns = Some(callsigns.to_owned());
                }
                connections.push(crate::connection::Connection::AprsFi(connection));
            } else {
                log_messages.push((
                    chrono::Local::now(),
                    "APRS.fi requires a list of callsigns".to_string(),
                    log::Level::Error,
                ));
            }
        }

        #[cfg(feature = "sondehub")]
        if let Some(connection) = &configuration.connections.sondehub {
            if let Some(callsigns) = &configuration.callsigns {
                let mut connection = connection.to_owned();
                if connection.callsigns.is_none() {
                    connection.callsigns = Some(callsigns.to_owned());
                }
                if connection.start.is_none() {
                    connection.start = configuration.time.start;
                }
                if connection.end.is_none() {
                    connection.end = configuration.time.end;
                }

                connections.push(crate::connection::Connection::SondeHub(connection));
            } else {
                log_messages.push((
                    chrono::Local::now(),
                    "SondeHub requires a list of callsigns".to_string(),
                    log::Level::Error,
                ));
            }
        }

        #[cfg(feature = "postgres")]
        if let Some(database_credentials) = &configuration.connections.database {
            connections.push(crate::connection::Connection::PacketDatabase(
                crate::connection::postgres::PacketDatabase::from_credentials(
                    &database_credentials,
                ),
            ));
        }

        if !connections.is_empty() {
            log_messages.push((
                chrono::Local::now(),
                format!(
                    "listening for packets every {:} from {:} connection(s)",
                    crate::utilities::duration_string(&configuration.time.interval),
                    connections.len(),
                ),
                log::Level::Info,
            ));

            for connection in &connections {
                log_messages.push((
                    chrono::Local::now(),
                    format!("{:?}", connection),
                    log::Level::Debug,
                ));
            }
        } else {
            log_messages.push((
                chrono::Local::now(),
                "no connections started".to_string(),
                log::Level::Error,
            ));
        }

        PacketravenApp {
            configuration,
            connections,
            tracks,
            tab_index: 0,
            chart_index: 0,
            log_messages,
            log_messages_scroll_offset: 0,
            log_level,
            should_quit: false,
        }
    }

    pub fn add_log_message(&mut self, message: String, level: log::Level) {
        self.log_messages
            .push((chrono::Local::now(), message, level));
    }

    pub fn next_tab(&mut self) {
        if self.tab_index < self.tracks.len() {
            self.tab_index += 1;
        } else {
            self.tab_index = 0;
        }
    }

    pub fn previous_tab(&mut self) {
        if self.tab_index > 0 {
            self.tab_index -= 1;
        } else {
            self.tab_index = self.tracks.len();
        }
    }

    pub fn up(&mut self) {
        if self.tab_index == 0 {
            if self.log_messages_scroll_offset > 0 {
                self.log_messages_scroll_offset -= 1;
            }
        } else if self.chart_index < super::draw::CHARTS.len() - 1 {
            self.chart_index += 1;
        } else {
            self.chart_index = 0;
        }
    }

    pub fn down(&mut self) {
        if self.tab_index == 0 {
            self.log_messages_scroll_offset += 1;
        } else if self.chart_index > 0 {
            self.chart_index -= 1;
        } else {
            self.chart_index = super::draw::CHARTS.len() - 1;
        }
    }

    pub fn on_key(&mut self, key: crossterm::event::KeyCode) {
        match key {
            crossterm::event::KeyCode::Esc => {
                self.should_quit = true;
            }
            crossterm::event::KeyCode::Char(character) => match character {
                'q' => {
                    self.should_quit = true;
                }
                'r' | ' ' => self.on_tick(),
                _ => {}
            },
            crossterm::event::KeyCode::BackTab => self.previous_tab(),
            crossterm::event::KeyCode::Tab => self.next_tab(),
            crossterm::event::KeyCode::Left => self.previous_tab(),
            crossterm::event::KeyCode::Right => self.next_tab(),
            crossterm::event::KeyCode::Up => self.up(),
            crossterm::event::KeyCode::Down => self.down(),
            _ => {}
        }
    }

    pub fn on_tick(&mut self) {
        let tracks = &mut self.tracks;

        let mut messages = crate::retrieve::retrieve_locations(
            &mut self.connections,
            tracks,
            self.configuration.time.start,
            self.configuration.time.end,
        );

        if let Some(prediction_configuration) = &self.configuration.prediction {
            match prediction_configuration {
                crate::configuration::prediction::PredictionConfiguration::Single(
                    prediction_configuration,
                ) => {
                    let existing_prediction =
                        if let Some(path) = &prediction_configuration.output_file {
                            // read from an existing prediction output file
                            if path.exists() {
                                let mut connection = crate::connection::Connection::GeoJsonFile(
                                    crate::connection::text::file::GeoJsonFile {
                                        path: format!("{:}", path.to_string_lossy()),
                                    },
                                );
                                messages.push((
                                    chrono::Local::now(),
                                    format!(
                                        "reading existing prediction output file: {:}",
                                        path.to_string_lossy()
                                    ),
                                    log::Level::Debug,
                                ));
                                match connection.retrieve_packets() {
                                    Ok(prediction) => Some(prediction),
                                    Err(_) => None,
                                }
                            } else {
                                None
                            }
                        } else {
                            None
                        };

                    for track in tracks {
                        track.prediction = match track
                            .prediction(&prediction_configuration.to_tawhiri_query().query.profile)
                        {
                            Ok(retrieved_prediction) => {
                                let landing_location = retrieved_prediction.last().unwrap();
                                messages.push((
                                    chrono::Local::now(),
                                    format!(
                                "{:} - predicted landing location: ({:.2}, {:.2}) at {:} ({:})",
                                track.name,
                                landing_location.location.coord.x,
                                landing_location.location.coord.y,
                                landing_location
                                    .location
                                    .time
                                    .format(&crate::DATETIME_FORMAT),
                                crate::utilities::duration_string(
                                    &( landing_location.location.time- chrono::Local::now() )
                                )
                            ),
                                    log::Level::Info,
                                ));
                                Some(retrieved_prediction)
                            }
                            Err(error) => {
                                messages.push((
                                    chrono::Local::now(),
                                    error.to_string(),
                                    log::Level::Error,
                                ));
                                existing_prediction.to_owned()
                            }
                        };
                    }

                    if let Some(path) = &prediction_configuration.output_file {
                        let mut locations = vec![];
                        for track in &self.tracks {
                            if let Some(prediction) = &track.prediction {
                                let track_locations: Vec<&crate::location::BalloonLocation> =
                                    prediction.iter().collect();
                                locations.extend(track_locations);
                            }
                        }
                        let feature_collection =
                            crate::connection::text::file::locations_geojson_featurecollection(
                                locations,
                            );

                        match std::fs::write(path, feature_collection.to_string()) {
                            Ok(_) => messages.push((
                                chrono::Local::now(),
                                format!("wrote predictions to {:}", path.to_string_lossy()),
                                log::Level::Debug,
                            )),
                            Err(error) => messages.push((
                                chrono::Local::now(),
                                error.to_string(),
                                log::Level::Error,
                            )),
                        };
                    }
                }
                crate::configuration::prediction::PredictionConfiguration::Cloud { .. } => {
                    self.add_log_message(
                        "cloud prediction not implemented".to_string(),
                        log::Level::Error,
                    );
                }
            }
        }

        if let Some(path) = &self.configuration.output_file {
            let mut locations = vec![];
            for track in &self.tracks {
                let track_locations: Vec<&crate::location::BalloonLocation> =
                    track.locations.iter().collect();
                locations.extend(track_locations);
            }
            let feature_collection =
                crate::connection::text::file::locations_geojson_featurecollection(locations);

            match std::fs::write(path, feature_collection.to_string()) {
                Ok(_) => messages.push((
                    chrono::Local::now(),
                    format!("wrote telemetry to {:}", path.to_string_lossy()),
                    log::Level::Debug,
                )),
                Err(error) => {
                    messages.push((chrono::Local::now(), error.to_string(), log::Level::Error))
                }
            };
        }

        match self.log_level {
            log::Level::Debug => {
                self.log_messages.extend(messages);
            }
            _ => {
                for (time, message, level) in messages {
                    if level != log::Level::Debug {
                        self.log_messages.push((time, message, level));
                    }
                }
            }
        }
    }
}
