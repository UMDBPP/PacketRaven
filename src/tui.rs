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

    app.on_tick();
    let mut last_tick = std::time::Instant::now();

    loop {
        terminal.draw(|frame| draw(frame, &app))?;

        if crossterm::event::poll(
            tick_rate
                .checked_sub(last_tick.elapsed())
                .unwrap_or_else(|| std::time::Duration::from_secs(1)),
        )? {
            if let crossterm::event::Event::Key(key) = crossterm::event::read()? {
                if key.kind == crossterm::event::KeyEventKind::Press {
                    match key.code {
                        crossterm::event::KeyCode::Char(c) => app.on_key(c),
                        crossterm::event::KeyCode::Left => app.previous(),
                        crossterm::event::KeyCode::Right => app.next(),
                        _ => {}
                    }
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
            log_level,
            should_quit: false,
        };

        if let Some(output) = &instance.configuration.log {
            // TODO
            instance.log(
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
                    program_start_time.to_rfc3339(),
                ));
            }
        }

        if let Some(output) = &instance.configuration.output {
            // TODO
            instance.log(
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
                    program_start_time.to_rfc3339()
                ));
            }
        }

        if let Some(output) = &instance.configuration.output {
            // TODO
            instance.log(
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
                    program_start_time.to_rfc3339()
                ));
            }
        }

        let mut filter_message = String::from("retrieving packets");
        if let Some(start) = instance.configuration.time.start {
            if let Some(end) = instance.configuration.time.end {
                filter_message += &format!(
                    " sent between {:} and {:}",
                    start.to_rfc3339(),
                    end.to_rfc3339()
                );
            } else {
                filter_message += &format!(" sent after {:}", start.to_rfc3339(),);
            }
        } else if let Some(end) = instance.configuration.time.end {
            filter_message += &format!(" sent before {:}", end.to_rfc3339());
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

        instance.log(filter_message, log::Level::Info);

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
                instance.log(format!("tracking URL: {:}", aprs_fi_url), log::Level::Info);
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
                            crate::connection::file::GeoJsonFile {
                                path: location.to_owned(),
                            },
                        );
                        instance.log(
                            format!("reading GeoJSON file {:}", &location.to_str().unwrap()),
                            log::Level::Info,
                        );
                    } else if ["txt", "log"].contains(&extension.to_str().unwrap()) {
                        connection = crate::connection::Connection::AprsTextFile(
                            crate::connection::file::AprsTextFile {
                                path: location.to_owned(),
                            },
                        );
                        instance.log(
                            format!("reading text file {:}", &location.to_str().unwrap()),
                            log::Level::Info,
                        );
                    } else {
                        instance.log(
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
                                Some(String::from(port))
                            },
                            Some(9600),
                        );

                        match serial {
                            Ok(serial) => {
                                connection = crate::connection::Connection::AprsSerial(serial);
                                instance.log(
                                    format!("opened port {:}", &location.to_str().unwrap()),
                                    log::Level::Info,
                                );
                            }
                            Err(error) => {
                                instance.log(error.to_string(), log::Level::Error);
                                continue;
                            }
                        }
                    }
                }
                instance.connections.push(connection);
            }
        }

        if let Some(aprs_fi_configuration) = &instance.configuration.packets.aprs_fi {
            let connection = crate::connection::Connection::AprsFi(
                crate::connection::aprs_fi::AprsFiQuery::new(
                    instance
                        .configuration
                        .callsigns
                        .to_owned()
                        .expect("APRS.fi requires a list of callsigns"),
                    aprs_fi_configuration.api_key.to_owned(),
                    None,
                    None,
                ),
            );
            instance.connections.push(connection);
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
                instance.log(
                    String::from("no connections successfully started"),
                    log::Level::Error,
                );
            }
        }

        if let Some(aprs_is_configuration) = &configuration.packets.aprs_is {
            // TODO
            unimplemented!("APRS IS connection is not implemented");
        }

        instance.log(
            format!(
                "listening for packets every {:} s from {:} source(s)",
                instance.configuration.time.interval.num_seconds(),
                instance.connections.len(),
            ),
            log::Level::Info,
        );

        if let Some(plots_configuration) = &instance.configuration.plots {
            // TODO
            unimplemented!("plotting is not implemented");
        }

        instance
    }

    pub fn log(&mut self, message: String, level: log::Level) {
        self.log_messages
            .push((chrono::Local::now(), message, level));
    }

    pub fn next(&mut self) {
        if self.selected_tab_index < self.tracks.len() {
            self.selected_tab_index += 1;
        } else {
            self.selected_tab_index = 0;
        }
    }

    pub fn previous(&mut self) {
        if self.selected_tab_index > 0 {
            self.selected_tab_index -= 1;
        } else {
            self.selected_tab_index = self.tracks.len();
        }
    }

    pub fn on_key(&mut self, c: char) {
        match c {
            'q' => {
                self.should_quit = true;
            }
            'r' => self.on_tick(),
            _ => {}
        }
    }

    pub fn on_tick(&mut self) {
        let tracks = &mut self.tracks;

        let messages = crate::retrieve::retrieve_locations(
            &mut self.connections,
            tracks,
            self.configuration.time.start,
            self.configuration.time.end,
        );

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

        if let Some(crate::configuration::prediction::PredictionConfiguration::Single(
            prediction_configuration,
        )) = &self.configuration.prediction
        {
            for track in tracks {
                let prediction =
                    track.prediction(&prediction_configuration.to_tawhiri_query().query.profile);

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
        .margin(1)
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
        .block(ratatui::widgets::Block::default())
        .wrap(ratatui::widgets::Wrap { trim: true });
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
                    ratatui::layout::Constraint::Min(30),
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

        let mut last_location_info = vec![
            ratatui::text::Spans::from(vec![
                ratatui::text::Span::styled("time: ", bold_style),
                ratatui::text::Span::raw(format!(
                    "{:}",
                    last_location.time.format("%Y-%m-%d %H:%M:%S")
                )),
            ]),
            ratatui::text::Spans::from(vec![
                ratatui::text::Span::styled("since prev.: ", bold_style),
                ratatui::text::Span::raw(format!(
                    "{:.2} s",
                    intervals.last().unwrap().num_seconds(),
                )),
            ]),
            ratatui::text::Spans::from(vec![
                ratatui::text::Span::styled("coordinates: ", bold_style),
                ratatui::text::Span::raw(format!(
                    "({:.2}, {:.2})",
                    &last_location.location.x(),
                    &last_location.location.y(),
                )),
            ]),
        ];
        if let Some(altitude) = last_location.altitude {
            last_location_info.push(ratatui::text::Spans::from(vec![
                ratatui::text::Span::styled("altitude: ", bold_style),
                ratatui::text::Span::raw(format!("{:.2} m", altitude)),
            ]));
        }
        last_location_info.extend(vec![
            ratatui::text::Spans::from(vec![
                ratatui::text::Span::styled("over ground: ", bold_style),
                ratatui::text::Span::raw(format!("{:.2} m", overground_distances.last().unwrap(),)),
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
        let last_location_info = ratatui::widgets::Paragraph::new(last_location_info).block(
            ratatui::widgets::Block::default()
                .borders(ratatui::widgets::Borders::ALL)
                .title(format!("Location #{:}", track.locations.len())),
        );
        frame.render_widget(last_location_info, track_info_areas[0]);

        let track_info = ratatui::widgets::Paragraph::new(vec![
            ratatui::text::Spans::from(vec![
                ratatui::text::Span::styled(format!("{:<10}", "pos. ascent rate: "), bold_style),
                ratatui::text::Span::raw(format!(
                    "{:.2} m/s",
                    positive_ascent_rates.iter().sum::<f64>() / positive_ascent_rates.len() as f64
                )),
            ]),
            ratatui::text::Spans::from(vec![
                ratatui::text::Span::styled(format!("{:<10}", "neg. ascent rate: "), bold_style),
                ratatui::text::Span::raw(format!(
                    "{:.2} m/s",
                    negative_ascent_rates.iter().sum::<f64>() / negative_ascent_rates.len() as f64
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

        if let Some(time_to_ground) = track.time_to_ground() {
            let landing_time = last_location.time + time_to_ground;
            let time_to_ground_from_now = landing_time - chrono::Local::now();
            let mut altitudes = vec![];

            let mut landing_estimate = vec![];

            if track.descending() {
                for location in &track.locations {
                    if let Some(altitude) = location.altitude {
                        altitudes.push(altitude)
                    }
                }
                landing_estimate.push(ratatui::text::Spans::from(vec![
                    ratatui::text::Span::styled("max altitude: ", bold_style),
                    ratatui::text::Span::raw(format!(
                        "{:.2} m",
                        altitudes.iter().max_by(|a, b| a.total_cmp(b)).unwrap(),
                    )),
                ]));
            }

            landing_estimate.extend([
                ratatui::text::Spans::from(vec![
                    ratatui::text::Span::styled("time to landing: ", bold_style),
                    ratatui::text::Span::raw(format!(
                        "{:} s",
                        time_to_ground_from_now.num_seconds(),
                    )),
                ]),
                ratatui::text::Spans::from(vec![
                    ratatui::text::Span::styled("landing time: ", bold_style),
                    ratatui::text::Span::raw(format!(
                        "{:}",
                        landing_time.format("%Y-%m-%d %H:%M:%S"),
                    )),
                ]),
            ]);

            if let Some(prediction) = &track.prediction {
                let landing_location = prediction.last().unwrap().location.x_y();
                landing_estimate.push(ratatui::text::Spans::from(vec![
                    ratatui::text::Span::styled("landing location: ", bold_style),
                    ratatui::text::Span::raw(format!(
                        "({:.2}, {:.2})",
                        landing_location.0, landing_location.1,
                    )),
                ]));
            }

            let landing_estimate = ratatui::widgets::Paragraph::new(landing_estimate).block(
                ratatui::widgets::Block::default()
                    .borders(ratatui::widgets::Borders::ALL)
                    .title("Descent"),
            );
            frame.render_widget(landing_estimate, track_info_areas[2]);
        }

        frame.render_widget(block, areas[1]);
    }
}

fn reset_terminal() -> Result<(), Box<dyn std::error::Error>> {
    crossterm::terminal::disable_raw_mode()?;
    crossterm::execute!(std::io::stdout(), crossterm::terminal::LeaveAlternateScreen)?;

    Ok(())
}
