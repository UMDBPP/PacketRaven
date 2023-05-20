pub fn run(
    configuration: &crate::configuration::RunConfiguration,
    log_level: log::Level,
) -> Result<(), Box<dyn std::error::Error>> {
    crossterm::terminal::enable_raw_mode()?;

    let original_hook = std::panic::take_hook();
    std::panic::set_hook(Box::new(move |panic| {
        reset_terminal().unwrap();
        original_hook(panic);
    }));

    let mut stdout = std::io::stdout();
    crossterm::execute!(
        stdout,
        crossterm::terminal::EnterAlternateScreen,
        crossterm::event::EnableMouseCapture
    )?;

    let backend = ratatui::backend::CrosstermBackend::new(stdout);
    let mut terminal = ratatui::Terminal::new(backend)?;

    let app = PacketravenApp::new(configuration, log_level);
    let result = run_app(&mut terminal, app);

    // restore terminal
    crossterm::terminal::disable_raw_mode()?;
    crossterm::execute!(
        terminal.backend_mut(),
        crossterm::terminal::LeaveAlternateScreen,
        crossterm::event::DisableMouseCapture
    )?;
    terminal.show_cursor()?;

    if let Err(err) = result {
        println!("{:?}", err)
    }

    Ok(())
}

fn run_app<B: ratatui::backend::Backend>(
    terminal: &mut ratatui::Terminal<B>,
    mut app: PacketravenApp,
) -> std::io::Result<()> {
    let tick_rate = app.configuration.time.interval.to_std().unwrap();

    // set the first tick to be in the past to update immediately
    let mut last_tick = std::time::Instant::now() - tick_rate;

    loop {
        terminal.draw(|frame| draw(frame, &app))?;

        if crossterm::event::poll(
            tick_rate
                .checked_sub(last_tick.elapsed())
                .unwrap_or_else(|| std::time::Duration::from_secs(1)),
        )? {
            if let crossterm::event::Event::Key(key) = crossterm::event::read()? {
                if key.kind == crossterm::event::KeyEventKind::Press {
                    app.on_key(key.code);
                }
            }
        }

        if last_tick.elapsed() >= tick_rate {
            app.on_tick();
            last_tick = std::time::Instant::now();
        }

        if app.should_quit {
            return Ok(());
        }
    }
}

pub struct PacketravenApp<'a> {
    pub configuration: &'a crate::configuration::RunConfiguration,
    pub connections: Vec<crate::connection::Connection>,
    pub tracks: Vec<crate::location::track::BalloonTrack>,
    selected_tab_index: usize,
    log_messages: Vec<(chrono::DateTime<chrono::Local>, String, log::Level)>,
    log_messages_scroll_offset: u16,
    log_level: log::Level,
    should_quit: bool,
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
                            crate::connection::file::AprsTextFile::new(location.to_owned()),
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
                        instance.configuration.callsigns.to_owned().unwrap(),
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
                let prediction =
                    track.prediction(&prediction_configuration.to_tawhiri_query().query.profile);

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
                        messages.push((chrono::Local::now(), error.to_string(), log::Level::Error))
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

fn draw<B: ratatui::backend::Backend>(frame: &mut ratatui::Frame<B>, app: &PacketravenApp) {
    let size = frame.size();
    let areas = ratatui::layout::Layout::default()
        .direction(ratatui::layout::Direction::Vertical)
        .constraints(
            [
                ratatui::layout::Constraint::Min(3),
                ratatui::layout::Constraint::Min(20),
            ]
            .as_ref(),
        )
        .split(size);

    let mut titles: Vec<ratatui::text::Spans> = app
        .tracks
        .iter()
        .map(|track| {
            ratatui::text::Spans::from(vec![ratatui::text::Span::styled(
                track.name.to_owned(),
                ratatui::style::Style::default().fg(ratatui::style::Color::Green),
            )])
        })
        .collect();
    titles.insert(
        0,
        ratatui::text::Spans::from(vec![ratatui::text::Span::raw("Log")]),
    );
    let tabs = ratatui::widgets::Tabs::new(titles)
        .block(ratatui::widgets::Block::default().borders(ratatui::widgets::Borders::ALL))
        .select(app.selected_tab_index)
        .style(ratatui::style::Style::default().fg(ratatui::style::Color::Cyan))
        .highlight_style(
            ratatui::style::Style::default()
                .add_modifier(ratatui::style::Modifier::BOLD)
                .add_modifier(ratatui::style::Modifier::UNDERLINED)
                .bg(ratatui::style::Color::Black),
        );
    frame.render_widget(tabs, areas[0]);

    let bold_style = ratatui::style::Style::default().add_modifier(ratatui::style::Modifier::BOLD);

    if app.selected_tab_index == 0 {
        let num_messages = app.log_messages.len() as u16;
        let paragraph_height = areas[1].height;
        if num_messages < paragraph_height {
            0
        } else {
            num_messages - paragraph_height + 2
        };

        let log = ratatui::widgets::Paragraph::new(
            app.log_messages
                .iter()
                .map(|(time, message, level)| {
                    let level_style = match level {
                        log::Level::Error => bold_style.fg(ratatui::style::Color::Red),
                        log::Level::Warn => bold_style.fg(ratatui::style::Color::Yellow),
                        log::Level::Info => bold_style.fg(ratatui::style::Color::Blue),
                        _ => bold_style,
                    };

                    ratatui::text::Spans::from(vec![
                        ratatui::text::Span::styled(
                            format!("{:} ", time.format("%Y-%m-%d %H:%M:%S")),
                            bold_style,
                        ),
                        ratatui::text::Span::styled(format!("{:<5} ", level), level_style),
                        ratatui::text::Span::raw(message),
                    ])
                })
                .collect::<Vec<ratatui::text::Spans>>(),
        )
        .scroll((app.log_messages_scroll_offset, 0))
        .wrap(ratatui::widgets::Wrap { trim: true })
        .block(ratatui::widgets::Block::default().borders(ratatui::widgets::Borders::ALL));
        frame.render_widget(log, areas[1]);
    } else {
        let track = &app.tracks[app.selected_tab_index - 1];
        let block = ratatui::widgets::Block::default();
        let track_areas = ratatui::layout::Layout::default()
            .direction(ratatui::layout::Direction::Vertical)
            .constraints(
                [
                    ratatui::layout::Constraint::Min(10),
                    ratatui::layout::Constraint::Min(10),
                ]
                .as_ref(),
            )
            .split(block.inner(areas[1]));

        let track_info_areas = ratatui::layout::Layout::default()
            .direction(ratatui::layout::Direction::Horizontal)
            .constraints(
                [
                    ratatui::layout::Constraint::Min(33),
                    ratatui::layout::Constraint::Min(30),
                    ratatui::layout::Constraint::Min(30),
                ]
                .as_ref(),
            )
            .split(track_areas[0]);

        let intervals = track.intervals();
        let overground_distances = track.overground_distances();
        let ground_speeds = track.ground_speeds();
        let ascents = track.ascents();
        let ascent_rates = track.ascent_rates();
        let mut positive_ascent_rates = vec![];
        let mut negative_ascent_rates = vec![];
        for ascent_rate in ascent_rates.clone() {
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

        let last_location = track.locations.last().unwrap();

        let mut last_location_info = vec![ratatui::text::Spans::from(vec![
            ratatui::text::Span::styled("time: ", bold_style),
            ratatui::text::Span::raw(format!(
                "{:}",
                last_location.time.format("%Y-%m-%d %H:%M:%S")
            )),
        ])];
        if track.locations.len() > 1 {
            last_location_info.push(ratatui::text::Spans::from(vec![
                ratatui::text::Span::styled("since prev.: ", bold_style),
                ratatui::text::Span::raw(format!(
                    "{:.2} s",
                    intervals.last().unwrap().num_seconds(),
                )),
            ]));
        }
        last_location_info.push(ratatui::text::Spans::from(vec![
            ratatui::text::Span::styled("coordinates: ", bold_style),
            ratatui::text::Span::raw(format!(
                "({:.2}, {:.2})",
                &last_location.location.x(),
                &last_location.location.y(),
            )),
        ]));
        if let Some(altitude) = last_location.altitude {
            last_location_info.push(ratatui::text::Spans::from(vec![
                ratatui::text::Span::styled("altitude: ", bold_style),
                ratatui::text::Span::raw(format!("{:.2} m", altitude)),
            ]));
        }
        if track.locations.len() > 1 {
            last_location_info.extend([
                ratatui::text::Spans::from(vec![
                    ratatui::text::Span::styled("over ground: ", bold_style),
                    ratatui::text::Span::raw(format!(
                        "{:.2} m",
                        overground_distances.last().unwrap(),
                    )),
                ]),
                ratatui::text::Spans::from(vec![
                    ratatui::text::Span::styled("ground speed: ", bold_style),
                    ratatui::text::Span::raw(format!("{:.2} m/s", ground_speeds.last().unwrap(),)),
                ]),
                ratatui::text::Spans::from(vec![
                    ratatui::text::Span::styled("ascent: ", bold_style),
                    ratatui::text::Span::raw(format!("{:.2} m", ascents.last().unwrap(),)),
                ]),
                ratatui::text::Spans::from(vec![
                    ratatui::text::Span::styled("ascent rate: ", bold_style),
                    ratatui::text::Span::raw(format!("{:.2} m/s", ascent_rates.last().unwrap(),)),
                ]),
            ]);
        }
        let last_location_info = ratatui::widgets::Paragraph::new(last_location_info).block(
            ratatui::widgets::Block::default()
                .borders(ratatui::widgets::Borders::ALL)
                .title(format!("Location #{:}", track.locations.len())),
        );
        frame.render_widget(last_location_info, track_info_areas[0]);

        if track.locations.len() > 1 {
            let track_info = ratatui::widgets::Paragraph::new(vec![
                ratatui::text::Spans::from(vec![
                    ratatui::text::Span::styled(
                        format!("{:<10}", "pos. ascent rate: "),
                        bold_style,
                    ),
                    ratatui::text::Span::raw(format!(
                        "{:.2} m/s",
                        positive_ascent_rates.iter().sum::<f64>()
                            / positive_ascent_rates.len() as f64
                    )),
                ]),
                ratatui::text::Spans::from(vec![
                    ratatui::text::Span::styled(
                        format!("{:<10}", "neg. ascent rate: "),
                        bold_style,
                    ),
                    ratatui::text::Span::raw(format!(
                        "{:.2} m/s",
                        negative_ascent_rates.iter().sum::<f64>()
                            / negative_ascent_rates.len() as f64
                    )),
                ]),
                ratatui::text::Spans::from(vec![
                    ratatui::text::Span::styled("ground speed: ", bold_style),
                    ratatui::text::Span::raw(format!(
                        "{:.2} m/s",
                        ground_speeds.iter().sum::<f64>() / ground_speeds.len() as f64,
                    )),
                ]),
                ratatui::text::Spans::from(vec![
                    ratatui::text::Span::styled("time interval: ", bold_style),
                    ratatui::text::Span::raw(format!(
                        "{:.2} s",
                        total_interval.num_seconds() as f64 / intervals.len() as f64,
                    )),
                ]),
            ])
            .block(
                ratatui::widgets::Block::default()
                    .borders(ratatui::widgets::Borders::ALL)
                    .title("Averages"),
            );
            frame.render_widget(track_info, track_info_areas[1]);
        }

        let with_altitude: Vec<&crate::location::BalloonLocation> = track
            .locations
            .iter()
            .filter(|location| location.altitude.is_some())
            .collect();
        let start_time = with_altitude.first().unwrap().time;
        let end_time = with_altitude.last().unwrap().time;
        let altitudes: Vec<f64> = with_altitude
            .iter()
            .map(|location| location.altitude.unwrap())
            .collect();
        let min_altitude = altitudes.iter().min_by(|a, b| a.total_cmp(b)).unwrap();
        let max_altitude = altitudes.iter().max_by(|a, b| a.total_cmp(b)).unwrap();

        let mut landing_estimate = vec![];
        if let Some(estimated_time_to_ground) = track.estimated_time_to_ground() {
            let landing_time = last_location.time + estimated_time_to_ground;
            let time_to_ground_from_now = landing_time - chrono::Local::now();

            landing_estimate.extend([
                ratatui::text::Spans::from(vec![
                    ratatui::text::Span::styled("max altitude: ", bold_style),
                    ratatui::text::Span::raw(format!("{:.2} m", max_altitude)),
                ]),
                ratatui::text::Spans::from(vec![
                    ratatui::text::Span::styled("est. time to landing: ", bold_style),
                    ratatui::text::Span::raw(format!(
                        "{:} s",
                        time_to_ground_from_now.num_seconds(),
                    )),
                ]),
                ratatui::text::Spans::from(vec![
                    ratatui::text::Span::styled("est. landing time: ", bold_style),
                    ratatui::text::Span::raw(format!(
                        "{:}",
                        landing_time.format("%Y-%m-%d %H:%M:%S"),
                    )),
                ]),
            ]);
        }

        if let Some(prediction) = &track.prediction {
            let predicted_landing_location = prediction.last().unwrap();
            landing_estimate.extend([
                ratatui::text::Spans::from(vec![
                    ratatui::text::Span::styled("pred. time to landing: ", bold_style),
                    ratatui::text::Span::raw(format!(
                        "{:} s",
                        (predicted_landing_location.time - chrono::Local::now()).num_seconds()
                    )),
                ]),
                ratatui::text::Spans::from(vec![
                    ratatui::text::Span::styled("pred. landing time: ", bold_style),
                    ratatui::text::Span::raw(format!(
                        "{:}",
                        predicted_landing_location.time.format("%Y-%m-%d %H:%M:%S"),
                    )),
                ]),
                ratatui::text::Spans::from(vec![
                    ratatui::text::Span::styled("pred. landing location: ", bold_style),
                    ratatui::text::Span::raw(format!(
                        "({:.2}, {:.2})",
                        predicted_landing_location.location.x(),
                        predicted_landing_location.location.y(),
                    )),
                ]),
            ]);
        }

        if !landing_estimate.is_empty() {
            let landing_estimate = ratatui::widgets::Paragraph::new(landing_estimate).block(
                ratatui::widgets::Block::default()
                    .borders(ratatui::widgets::Borders::ALL)
                    .title("Descent"),
            );
            frame.render_widget(landing_estimate, track_info_areas[2]);
        }

        let mut datasets = vec![];

        let x_range = [0.0, (end_time - start_time).num_seconds() as f64];
        let y_range = [min_altitude.to_owned(), max_altitude.to_owned()];

        let data = altitudes_dataset(&track.locations);
        datasets.push(
            ratatui::widgets::Dataset::default()
                .marker(ratatui::symbols::Marker::Braille)
                .style(ratatui::style::Style::default().fg(ratatui::style::Color::Blue))
                .data(&data)
                .name("telemetry")
                .graph_type(ratatui::widgets::GraphType::Scatter),
        );

        let data;
        if let Some(prediction) = &track.prediction {
            data = altitudes_dataset(prediction);
            datasets.push(
                ratatui::widgets::Dataset::default()
                    .marker(ratatui::symbols::Marker::Braille)
                    .style(ratatui::style::Style::default().fg(ratatui::style::Color::Red))
                    .data(&data)
                    .name("prediction")
                    .graph_type(ratatui::widgets::GraphType::Scatter),
            );
        }

        let time_format = if end_time - start_time < chrono::Duration::days(1) {
            "%H:%M:%S"
        } else {
            "%Y-%m-%d %H:%M:%S"
        };
        let time_labels = vec![
            ratatui::text::Span::styled(
                start_time.format(time_format).to_string(),
                ratatui::style::Style::default().add_modifier(ratatui::style::Modifier::BOLD),
            ),
            ratatui::text::Span::raw(
                (start_time + ((end_time - start_time) / 2))
                    .format(time_format)
                    .to_string(),
            ),
            ratatui::text::Span::styled(
                end_time.format(time_format).to_string(),
                ratatui::style::Style::default().add_modifier(ratatui::style::Modifier::BOLD),
            ),
        ];

        let chart = ratatui::widgets::Chart::new(datasets)
            .block(
                ratatui::widgets::Block::default().title(ratatui::text::Span::styled(
                    "altitude / time",
                    ratatui::style::Style::default()
                        .fg(ratatui::style::Color::Cyan)
                        .add_modifier(ratatui::style::Modifier::BOLD),
                )),
            )
            .x_axis(
                ratatui::widgets::Axis::default()
                    .style(ratatui::style::Style::default().fg(ratatui::style::Color::Gray))
                    .labels(time_labels)
                    .bounds(x_range),
            )
            .y_axis(
                ratatui::widgets::Axis::default()
                    .style(ratatui::style::Style::default().fg(ratatui::style::Color::Gray))
                    .labels(vec![
                        ratatui::text::Span::styled(
                            format!("{:.0} m", min_altitude),
                            ratatui::style::Style::default()
                                .add_modifier(ratatui::style::Modifier::BOLD),
                        ),
                        ratatui::text::Span::styled(
                            format!(
                                "{:.0} m",
                                min_altitude + ((max_altitude - min_altitude) / 4.0)
                            ),
                            ratatui::style::Style::default(),
                        ),
                        ratatui::text::Span::styled(
                            format!(
                                "{:.0} m",
                                min_altitude + ((max_altitude - min_altitude) / 2.0)
                            ),
                            ratatui::style::Style::default(),
                        ),
                        ratatui::text::Span::styled(
                            format!(
                                "{:.0} m",
                                min_altitude + ((max_altitude - min_altitude) * 3.0 / 4.0)
                            ),
                            ratatui::style::Style::default(),
                        ),
                        ratatui::text::Span::styled(
                            format!("{:.0} m", max_altitude),
                            ratatui::style::Style::default()
                                .add_modifier(ratatui::style::Modifier::BOLD),
                        ),
                    ])
                    .bounds(y_range),
            );
        frame.render_widget(chart, track_areas[1]);

        frame.render_widget(block, areas[1]);
    }
}

fn altitudes_dataset(locations: &[crate::location::BalloonLocation]) -> Vec<(f64, f64)> {
    let with_altitude: Vec<&crate::location::BalloonLocation> = locations
        .iter()
        .filter(|location| location.altitude.is_some())
        .collect();
    let start_time = with_altitude.first().unwrap().time;
    let seconds: Vec<f64> = with_altitude
        .iter()
        .map(|location| (location.time - start_time).num_seconds() as f64)
        .collect();
    let altitudes: Vec<f64> = with_altitude
        .iter()
        .map(|location| location.altitude.unwrap())
        .collect();

    seconds
        .iter()
        .zip(altitudes.iter())
        .map(|tuple| (tuple.0.to_owned(), tuple.1.to_owned()))
        .collect::<Vec<(f64, f64)>>()
}

fn reset_terminal() -> Result<(), Box<dyn std::error::Error>> {
    crossterm::terminal::disable_raw_mode()?;
    crossterm::execute!(std::io::stdout(), crossterm::terminal::LeaveAlternateScreen)?;

    Ok(())
}
