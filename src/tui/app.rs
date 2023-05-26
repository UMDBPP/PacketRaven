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

        let mut instance = PacketravenApp {
            configuration,
            connections: vec![],
            tracks: vec![],
            tab_index: 0,
            chart_index: 0,
            log_messages: vec![],
            log_messages_scroll_offset: 0,
            log_level,
            should_quit: false,
        };

        if let Some(output) = &instance.configuration.log.to_owned() {
            // TODO
            instance.add_log_message(
                "logging to file is not implemented".to_owned(),
                log::Level::Warn,
            );
            let mut filename: std::path::PathBuf;
            if output.filename.is_file() {
                filename = output.filename.to_owned();
            } else {
                filename = std::path::PathBuf::from(".");
                filename.push(format!(
                    "{:}_log_{:}.txt",
                    instance.configuration.name,
                    program_start_time.format(&crate::DATETIME_FORMAT),
                ));
            }
        }

        if let Some(output) = &instance.configuration.output.to_owned() {
            // TODO
            instance.add_log_message(
                "file output is not implemented".to_owned(),
                log::Level::Warn,
            );
            let mut filename: std::path::PathBuf;
            if output.filename.is_file() {
                filename = output.filename.to_owned();
            } else {
                filename = std::path::PathBuf::from(".");
                filename.push(format!(
                    "{:}_{:}.geojson",
                    instance.configuration.name,
                    program_start_time.format(&crate::DATETIME_FORMAT)
                ));
            }
        }

        if let Some(output) = &instance.configuration.output.to_owned() {
            // TODO
            instance.add_log_message(
                "file output is not implemented".to_owned(),
                log::Level::Warn,
            );
            let mut filename: std::path::PathBuf;
            if output.filename.is_file() {
                filename = output.filename.to_owned();
            } else {
                filename = std::path::PathBuf::from(".");
                filename.push(format!(
                    "{:}_predict_{:}.geojson",
                    instance.configuration.name,
                    program_start_time.format(&crate::DATETIME_FORMAT)
                ));
            }
        }

        let mut filter_message = "retrieving packets".to_string();
        if let Some(start) = instance.configuration.time.start {
            if let Some(end) = instance.configuration.time.end {
                filter_message += &format!(
                    " sent between {:} and {:}",
                    start.format(&crate::DATETIME_FORMAT),
                    end.format(&crate::DATETIME_FORMAT)
                );
            } else {
                filter_message +=
                    &format!(" sent after {:}", start.format(&crate::DATETIME_FORMAT),);
            }
        } else if let Some(end) = instance.configuration.time.end {
            filter_message += &format!(" sent before {:}", end.format(&crate::DATETIME_FORMAT));
        }
        if let Some(callsigns) = &instance.configuration.callsigns {
            if !callsigns.is_empty() {
                filter_message += &format!(
                    " from {:} callsign(s): {:}",
                    callsigns.len(),
                    callsigns.join(", ")
                );
            }
        }

        instance.add_log_message(filter_message, log::Level::Info);

        if let Some(callsigns) = &instance.configuration.callsigns.to_owned() {
            if !callsigns.is_empty() {
                let mut aprs_fi_url =
                    format!("https://aprs.fi/#!call=a%2F{:}", callsigns.join("%2Ca%2F"));
                if let Some(start) = instance.configuration.time.start {
                    aprs_fi_url += &format!("&ts={:}", start.timestamp());
                }
                if let Some(end) = instance.configuration.time.end {
                    aprs_fi_url += &format!("&te={:}", end.timestamp());
                }
                instance.add_log_message(format!("tracking: {:}", aprs_fi_url), log::Level::Info);

                let mut sondehub_url =
                    format!("https://amateur.sondehub.org/#!q={:}", callsigns.join(","));
                if let Some(start) = instance.configuration.time.start {
                    let duration = chrono::Local::now() - start;
                    sondehub_url += &if duration < chrono::Duration::days(1) {
                        format!("&qm={:}d", duration.num_days())
                    } else {
                        format!("&qm={:}h", duration.num_hours())
                    }
                }

                instance.add_log_message(format!("tracking: {:}", sondehub_url), log::Level::Info);
            }
        }

        if let Some(text_configuration) = &instance.configuration.packets.text.to_owned() {
            for text_stream in text_configuration {
                let connection = match text_stream {
                    crate::connection::text::TextStream::GeoJsonFile(connection) => {
                        let connection = connection.to_owned();
                        instance.add_log_message(
                            format!("reading GeoJSON file: {:}", connection.path),
                            log::Level::Info,
                        );

                        crate::connection::Connection::GeoJsonFile(connection)
                    }
                    crate::connection::text::TextStream::AprsTextFile(connection) => {
                        let mut connection = connection.to_owned();
                        if connection.callsigns.is_none() {
                            if let Some(callsigns) = &instance.configuration.callsigns {
                                connection.callsigns = Some(callsigns.to_owned());
                            }
                        }
                        instance.add_log_message(
                            format!("reading text file of APRS frames: {:}", connection.path),
                            log::Level::Info,
                        );
                        crate::connection::Connection::AprsTextFile(connection)
                    }
                    #[cfg(feature = "serial")]
                    crate::connection::text::TextStream::AprsSerial(connection) => {
                        let mut connection = connection.to_owned();
                        if connection.callsigns.is_none() {
                            if let Some(callsigns) = &instance.configuration.callsigns {
                                connection.callsigns = Some(callsigns.to_owned());
                            }
                        }
                        crate::connection::Connection::AprsSerial(connection)
                    }
                };
                instance.connections.push(connection);
            }
        }

        #[cfg(feature = "aprsfi")]
        if let Some(aprs_fi_query) = &instance.configuration.packets.aprs_fi {
            if let Some(callsigns) = &instance.configuration.callsigns {
                let mut connection = aprs_fi_query.to_owned();
                if connection.callsigns.is_none() {
                    connection.callsigns = Some(callsigns.to_owned());
                }
                instance
                    .connections
                    .push(crate::connection::Connection::AprsFi(connection));
            } else {
                instance.add_log_message(
                    "APRS.fi requires a list of callsigns".to_string(),
                    log::Level::Error,
                );
            }
        }

        #[cfg(feature = "sondehub")]
        if let Some(connection) = &instance.configuration.packets.sondehub {
            if let Some(callsigns) = &instance.configuration.callsigns {
                let mut connection = connection.to_owned();
                if connection.callsigns.is_none() {
                    connection.callsigns = Some(callsigns.to_owned());
                }
                if connection.start.is_none() {
                    connection.start = instance.configuration.time.start;
                }
                if connection.end.is_none() {
                    connection.end = instance.configuration.time.end;
                }
                instance
                    .connections
                    .push(crate::connection::Connection::SondeHub(connection));
            } else {
                instance.add_log_message(
                    "SondeHub requires a list of callsigns".to_string(),
                    log::Level::Error,
                );
            }
        }

        #[cfg(feature = "postgres")]
        if let Some(database_credentials) = &instance.configuration.packets.database {
            instance
                .connections
                .push(crate::connection::Connection::PacketDatabase(
                    crate::connection::postgres::PacketDatabase::from_credentials(
                        &database_credentials,
                    ),
                ));
        }

        if instance.connections.is_empty() {
            if let Some(output) = &instance.configuration.output {
                if output.filename.exists() {
                    instance
                        .connections
                        .push(crate::connection::Connection::GeoJsonFile(
                            crate::connection::text::file::GeoJsonFile {
                                path: output.filename.to_str().unwrap().to_owned(),
                            },
                        ));
                    instance.add_log_message(
                        format!(
                            "reading existing output file: {:}",
                            output.filename.to_str().unwrap()
                        ),
                        log::Level::Debug,
                    );
                }
            } else {
                instance
                    .add_log_message("no connections were started".to_string(), log::Level::Error);
            }
        }

        instance.add_log_message(
            format!(
                "listening for packets every {:} from {:} connection(s)",
                crate::utilities::duration_string(&instance.configuration.time.interval),
                instance.connections.len(),
            ),
            log::Level::Info,
        );

        for connection in instance.connections.to_owned() {
            instance.add_log_message(format!("{:?}", connection), log::Level::Debug);
        }

        instance
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
        if self.tab_index == 0 && self.log_messages_scroll_offset > 0 {
            self.log_messages_scroll_offset -= 1;
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

        if let Some(crate::configuration::prediction::PredictionConfiguration::Single(
            prediction_configuration,
        )) = &self.configuration.prediction
        {
            for track in tracks {
                let prediction =
                    track.prediction(&prediction_configuration.to_tawhiri_query().query.profile);

                match prediction {
                    Ok(prediction) => {
                        let landing_location = prediction.last().unwrap();
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
                                    &(chrono::Local::now() - landing_location.location.time)
                                )
                            ),
                            log::Level::Info,
                        ));
                        track.prediction = Some(prediction);
                    }
                    Err(error) => {
                        messages.push((chrono::Local::now(), error.to_string(), log::Level::Error));
                    }
                }
            }
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
