pub fn draw<B: ratatui::backend::Backend>(
    frame: &mut ratatui::Frame<B>,
    app: &super::app::PacketravenApp,
) {
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
                .add_modifier(ratatui::style::Modifier::UNDERLINED),
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
                            format!("{:} ", time.format(&crate::DATETIME_FORMAT)),
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

        let track_chart_areas = ratatui::layout::Layout::default()
            .direction(ratatui::layout::Direction::Vertical)
            .constraints(
                [
                    ratatui::layout::Constraint::Min(10),
                    ratatui::layout::Constraint::Min(5),
                ]
                .as_ref(),
            )
            .split(track_areas[1]);

        let track = &app.tracks[app.selected_tab_index - 1];
        let intervals = crate::location::track::intervals(&track.locations);
        let overground_distances = crate::location::track::overground_distances(&track.locations);
        let ground_speeds = crate::location::track::ground_speeds(&track.locations);
        let ascents = crate::location::track::ascents(&track.locations);
        let ascent_rates = crate::location::track::ascent_rates(&track.locations);

        let positive_ascent_rates: Vec<f64> = ascent_rates
            .iter()
            .filter_map(|ascent_rate| {
                if ascent_rate > &0.0 {
                    Some(ascent_rate.to_owned())
                } else {
                    None
                }
            })
            .collect();
        let negative_ascent_rates: Vec<f64> = ascent_rates
            .iter()
            .filter_map(|ascent_rate| {
                if ascent_rate < &0.0 {
                    Some(ascent_rate.to_owned())
                } else {
                    None
                }
            })
            .collect();

        let ascent_rate_range = [
            ascent_rates
                .iter()
                .min_by(|a, b| a.total_cmp(b))
                .unwrap()
                .to_owned(),
            ascent_rates
                .iter()
                .max_by(|a, b| a.total_cmp(b))
                .unwrap()
                .to_owned(),
        ];

        let mut total_interval = chrono::Duration::seconds(0);
        for interval in &intervals {
            total_interval = total_interval + interval.to_owned();
        }

        let locations_with_altitude: Vec<&crate::location::BalloonLocation> = track
            .locations
            .iter()
            .filter(|location| location.altitude.is_some())
            .collect();
        let start_time = locations_with_altitude.first().unwrap().time;
        let end_time = locations_with_altitude.last().unwrap().time;
        let seconds_since_start: Vec<f64> = locations_with_altitude
            .iter()
            .map(|location| (location.time - start_time).num_seconds() as f64)
            .collect();

        let altitudes: Vec<f64> = locations_with_altitude
            .iter()
            .filter_map(|location| location.altitude)
            .collect();
        let altitude_range = [
            altitudes
                .iter()
                .min_by(|a, b| a.total_cmp(b))
                .unwrap()
                .to_owned(),
            altitudes
                .iter()
                .max_by(|a, b| a.total_cmp(b))
                .unwrap()
                .to_owned(),
        ];

        let last_location = track.locations.last().unwrap();

        let mut last_location_info = vec![ratatui::text::Spans::from(vec![
            ratatui::text::Span::styled("time: ", bold_style),
            ratatui::text::Span::raw(format!(
                "{:}",
                last_location.time.format(&crate::DATETIME_FORMAT)
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

        let mut landing_estimate = vec![];
        if let Some(estimated_time_to_ground) = track.estimated_time_to_ground() {
            let landing_time = last_location.time + estimated_time_to_ground;
            let time_to_ground_from_now = landing_time - chrono::Local::now();

            landing_estimate.extend([
                ratatui::text::Spans::from(vec![
                    ratatui::text::Span::styled("max altitude: ", bold_style),
                    ratatui::text::Span::raw(format!("{:.2} m", altitude_range[1])),
                ]),
                ratatui::text::Spans::from(vec![
                    ratatui::text::Span::styled("est. landing: ", bold_style),
                    ratatui::text::Span::raw(crate::parse::duration_string(
                        time_to_ground_from_now,
                    )),
                ]),
                ratatui::text::Spans::from(vec![
                    ratatui::text::Span::styled("est. landing time: ", bold_style),
                    ratatui::text::Span::raw(format!(
                        "{:}",
                        landing_time.format(&crate::DATETIME_FORMAT),
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
                        predicted_landing_location
                            .time
                            .format(&crate::DATETIME_FORMAT),
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

        let data: Vec<(f64, f64)> = seconds_since_start
            .iter()
            .zip(altitudes.iter())
            .map(|tuple| (tuple.0.to_owned(), tuple.1.to_owned()))
            .collect();
        datasets.push(
            ratatui::widgets::Dataset::default()
                .marker(ratatui::symbols::Marker::Braille)
                .style(ratatui::style::Style::default().fg(ratatui::style::Color::Blue))
                .data(&data)
                .name("telemetry")
                .graph_type(ratatui::widgets::GraphType::Scatter),
        );

        let data: Vec<(f64, f64)>;
        if let Some(prediction) = &track.prediction {
            let with_altitude = crate::location::track::with_altitude(prediction);
            let start_time = with_altitude.first().unwrap().time;
            let seconds_since_start: Vec<f64> = with_altitude
                .iter()
                .map(|location| (location.time - start_time).num_seconds() as f64)
                .collect();
            let altitudes = crate::location::track::altitudes(&with_altitude);

            data = seconds_since_start
                .iter()
                .zip(altitudes.iter())
                .map(|tuple| (tuple.0.to_owned(), tuple.1.to_owned()))
                .collect();
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
            &crate::DATETIME_FORMAT
        };
        let time_labels = vec![
            ratatui::text::Span::raw(start_time.format(time_format).to_string()),
            ratatui::text::Span::raw(
                (start_time + ((end_time - start_time) / 2))
                    .format(time_format)
                    .to_string(),
            ),
            ratatui::text::Span::raw(end_time.format(time_format).to_string()),
        ];

        let chart = ratatui::widgets::Chart::new(datasets)
            .block(
                ratatui::widgets::Block::default()
                    .title(ratatui::text::Span::styled(
                        "altitude",
                        ratatui::style::Style::default()
                            .fg(ratatui::style::Color::Cyan)
                            .add_modifier(ratatui::style::Modifier::BOLD),
                    ))
                    .borders(ratatui::widgets::Borders::ALL),
            )
            .x_axis(
                ratatui::widgets::Axis::default()
                    .style(ratatui::style::Style::default().fg(ratatui::style::Color::DarkGray))
                    .labels(time_labels.to_owned())
                    .labels_alignment(ratatui::layout::Alignment::Right)
                    .bounds(x_range),
            )
            .y_axis(
                ratatui::widgets::Axis::default()
                    .style(ratatui::style::Style::default().fg(ratatui::style::Color::DarkGray))
                    .labels(vec![
                        ratatui::text::Span::raw(format!(
                            "{:>9}",
                            format!("{:.0} m", altitude_range[0])
                        )),
                        ratatui::text::Span::raw(format!(
                            "{:>9}",
                            format!("{:.0} m", altitude_range[1])
                        )),
                    ])
                    .labels_alignment(ratatui::layout::Alignment::Right)
                    .bounds(altitude_range),
            );
        frame.render_widget(chart, track_chart_areas[0]);

        let mut datasets = vec![];
        let data: Vec<(f64, f64)> = seconds_since_start
            .iter()
            .zip(ascent_rates.iter())
            .map(|tuple| (tuple.0.to_owned(), tuple.1.to_owned()))
            .collect();
        datasets.push(
            ratatui::widgets::Dataset::default()
                .marker(ratatui::symbols::Marker::Braille)
                .style(ratatui::style::Style::default().fg(ratatui::style::Color::Blue))
                .data(&data)
                .name("telemetry")
                .graph_type(ratatui::widgets::GraphType::Scatter),
        );
        let data: Vec<(f64, f64)>;
        if let Some(prediction) = &track.prediction {
            let locations_with_altitude: Vec<&crate::location::BalloonLocation> = prediction
                .iter()
                .filter(|location| location.altitude.is_some())
                .collect();
            let start_time = locations_with_altitude.first().unwrap().time;
            let seconds_since_start: Vec<f64> = locations_with_altitude
                .iter()
                .map(|location| (location.time - start_time).num_seconds() as f64)
                .collect();

            let ascent_rates = crate::location::track::ascent_rates(prediction);

            data = seconds_since_start
                .iter()
                .zip(ascent_rates.iter())
                .map(|tuple| (tuple.0.to_owned(), tuple.1.to_owned()))
                .collect();
            datasets.push(
                ratatui::widgets::Dataset::default()
                    .marker(ratatui::symbols::Marker::Braille)
                    .style(ratatui::style::Style::default().fg(ratatui::style::Color::Red))
                    .data(&data)
                    .name("prediction")
                    .graph_type(ratatui::widgets::GraphType::Scatter),
            );
        }

        let chart = ratatui::widgets::Chart::new(datasets)
            .block(
                ratatui::widgets::Block::default()
                    .title(ratatui::text::Span::styled(
                        "ascent rate",
                        ratatui::style::Style::default()
                            .fg(ratatui::style::Color::Cyan)
                            .add_modifier(ratatui::style::Modifier::BOLD),
                    ))
                    .borders(ratatui::widgets::Borders::ALL),
            )
            .x_axis(
                ratatui::widgets::Axis::default()
                    .style(ratatui::style::Style::default().fg(ratatui::style::Color::DarkGray))
                    .labels(time_labels)
                    .labels_alignment(ratatui::layout::Alignment::Right)
                    .bounds(x_range),
            )
            .y_axis(
                ratatui::widgets::Axis::default()
                    .style(ratatui::style::Style::default().fg(ratatui::style::Color::DarkGray))
                    .labels(vec![
                        ratatui::text::Span::raw(format!(
                            "{:>9}",
                            format!("{:.1} m/s", ascent_rate_range[0])
                        )),
                        ratatui::text::Span::raw(format!(
                            "{:>9}",
                            format!("{:.1} m/s", ascent_rate_range[1])
                        )),
                    ])
                    .labels_alignment(ratatui::layout::Alignment::Right)
                    .bounds(ascent_rate_range),
            );
        frame.render_widget(chart, track_chart_areas[1]);

        frame.render_widget(block, areas[1]);
    }
}
