pub struct PacketravenApp<'a> {
    pub configuration: &'a crate::configuration::RunConfiguration,
    pub connections: Vec<crate::connection::Connection>,
    pub tracks: Vec<crate::location::track::BalloonTrack>,
    pub selected_tab_index: usize,
    pub log_messages: Vec<(chrono::DateTime<chrono::Local>, String, log::Level)>,
    pub log_messages_scroll_offset: u16,
    pub log_level: log::Level,
    pub should_not_retrieve: Vec<String>,
    pub should_quit: bool,
}

impl<'a> PacketravenApp<'a> {
    pub fn new(
        configuration: &'a crate::configuration::RunConfiguration,
        log_level: log::Level,
    ) -> PacketravenApp<'a> {
        let program_start_time = chrono::Local::now();

        let mut instance = PacketravenApp {
            configuration,
            connections: vec![],
            tracks: vec![],
            selected_tab_index: 0,
            log_messages: vec![],
            log_messages_scroll_offset: 0,
            log_level,
            should_not_retrieve: Vec::<String>::new(),
            should_quit: false,
        };

        if let Some(output) = &instance.configuration.log {
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

        if let Some(output) = &instance.configuration.output {
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

        if let Some(output) = &instance.configuration.output {
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

        if let Some(callsigns) = &instance.configuration.callsigns {
            if !callsigns.is_empty() {
                let mut aprs_fi_url =
                    format!("https://aprs.fi/#!call=a%2F{:}", callsigns.join("%2Ca%2F"));
                if let Some(start) = instance.configuration.time.start {
                    aprs_fi_url += &format!("&ts={:}", start.timestamp());
                }
                if let Some(end) = instance.configuration.time.end {
                    aprs_fi_url += &format!("&te={:}", end.timestamp());
                }
                instance
                    .add_log_message(format!("tracking URL: {:}", aprs_fi_url), log::Level::Info);
            }
        }

        if let Some(text_configuration) = &instance.configuration.packets.text {
            for location in &text_configuration.locations {
                let connection: crate::connection::Connection;
                if let Some(extension) = location.extension() {
                    if ["json", "geojson"]
                        .contains(&location.extension().unwrap().to_str().unwrap())
                    {
                        connection = crate::connection::Connection::GeoJsonFile(
                            crate::connection::file::GeoJsonFile::new(location.to_owned()),
                        );
                        instance.add_log_message(
                            format!("reading GeoJSON file {:}", &location.to_str().unwrap()),
                            log::Level::Info,
                        );
                    } else if ["txt", "log"].contains(&extension.to_str().unwrap()) {
                        connection = crate::connection::Connection::AprsTextFile(
                            match crate::connection::file::AprsTextFile::new(location.to_owned()) {
                                Ok(file) => file,
                                Err(_) => continue,
                            },
                        );
                        instance.add_log_message(
                            format!("reading text file {:}", &location.to_str().unwrap()),
                            log::Level::Info,
                        );
                    } else {
                        instance.add_log_message(
                            format!("File type not implemented: {:}", location.to_str().unwrap()),
                            log::Level::Error,
                        );
                        continue;
                    }
                } else {
                    #[cfg(feature = "serial")]
                    {
                        let port = location.to_str().unwrap();

                        let serial = crate::connection::serial::AprsSerial::new(
                            if port == "auto" {
                                None
                            } else {
                                Some(port.to_string())
                            },
                            Some(9600),
                            configuration.callsigns.to_owned(),
                        );

                        match serial {
                            Ok(serial) => {
                                connection = crate::connection::Connection::AprsSerial(serial);
                                instance.add_log_message(
                                    format!("opened port {:}", &location.to_str().unwrap()),
                                    log::Level::Info,
                                );
                            }
                            Err(error) => {
                                instance.add_log_message(error.to_string(), log::Level::Error);
                                continue;
                            }
                        }
                    }
                }
                instance.connections.push(connection);
            }
        }

        #[cfg(feature = "aprsfi")]
        if let Some(aprs_fi_configuration) = &instance.configuration.packets.aprs_fi {
            let connection = crate::connection::Connection::AprsFi(
                crate::connection::aprs_fi::AprsFiQuery::new(
                    instance
                        .configuration
                        .callsigns
                        .to_owned()
                        .expect("APRS.fi requires a list of callsigns"),
                    aprs_fi_configuration.api_key.to_owned(),
                ),
            );
            instance.connections.push(connection);
        }

        #[cfg(feature = "sondehub")]
        if let Some(sondehub_enabled) = instance.configuration.packets.sondehub {
            if sondehub_enabled {
                let connection = crate::connection::Connection::SondeHub(
                    crate::connection::sondehub::SondeHubQuery::new(
                        instance
                            .configuration
                            .callsigns
                            .to_owned()
                            .expect("SondeHub requires a list of callsigns"),
                        instance.configuration.time.start,
                        instance.configuration.time.end,
                    ),
                );
                instance.connections.push(connection);
            }
        }

        #[cfg(feature = "postgres")]
        if let Some(database_configuration) = instance.configuration.packets.database {
            let connection = crate::connection::Connection::PacketDatabase(
                crate::connection::postgres::PacketDatabase::from_credentials(
                    &database_configuration,
                ),
            );
            connections.push(connection);
        }

        if instance.connections.is_empty() {
            if let Some(output) = &instance.configuration.output {
                if output.filename.exists() {
                    let connection = crate::connection::Connection::GeoJsonFile(
                        crate::connection::file::GeoJsonFile {
                            path: output.filename.to_owned(),
                        },
                    );
                    instance.connections.push(connection);
                }
            } else {
                instance.add_log_message(
                    "no connections successfully started".to_string(),
                    log::Level::Error,
                );
            }
        }

        if let Some(aprs_is_configuration) = &configuration.packets.aprs_is {
            // TODO
            unimplemented!("APRS IS connection is not implemented");
        }

        instance.add_log_message(
            format!(
                "listening for packets every {:} s from {:} source(s)",
                instance.configuration.time.interval.num_seconds(),
                instance.connections.len(),
            ),
            log::Level::Info,
        );

        if instance.configuration.plots.is_some() {
            instance.add_log_message(
                "plotting is implemented in the TUI".to_string(),
                log::Level::Debug,
            );
        }

        instance
    }

    pub fn add_log_message(&mut self, message: String, level: log::Level) {
        self.log_messages
            .push((chrono::Local::now(), message, level));
    }

    pub fn next_tab(&mut self) {
        if self.selected_tab_index < self.tracks.len() {
            self.selected_tab_index += 1;
        } else {
            self.selected_tab_index = 0;
        }
    }

    pub fn previous_tab(&mut self) {
        if self.selected_tab_index > 0 {
            self.selected_tab_index -= 1;
        } else {
            self.selected_tab_index = self.tracks.len();
        }
    }

    pub fn up(&mut self) {
        if self.selected_tab_index == 0 && self.log_messages_scroll_offset > 0 {
            self.log_messages_scroll_offset -= 1;
        }
    }

    pub fn down(&mut self) {
        if self.selected_tab_index == 0 {
            self.log_messages_scroll_offset += 1;
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
                if self.should_not_retrieve.contains(&track.name) {
                    let prediction = track
                        .prediction(&prediction_configuration.to_tawhiri_query().query.profile);

                    match prediction {
                        Ok(prediction) => {
                            if track.descending() {
                                let landing_location = prediction.last().unwrap().location.x_y();
                                self.log_messages.push((
                                    chrono::Local::now(),
                                    format!(
                                        "{:} - predicted landing location: ({:.2}, {:.2})",
                                        track.name, landing_location.0, landing_location.1,
                                    ),
                                    log::Level::Info,
                                ));
                            }
                            track.prediction = Some(prediction);
                        }
                        Err(error) => {
                            self.should_not_retrieve.push(track.name.to_owned());
                            messages.push((
                                chrono::Local::now(),
                                error.to_string(),
                                log::Level::Error,
                            ));
                        }
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
