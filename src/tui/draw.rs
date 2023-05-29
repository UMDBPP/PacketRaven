lazy_static::lazy_static! {
    pub static ref CHARTS: Vec<String> = vec!["altitude / time".to_string(), "ascent rate / time".to_string(), "altitude / ground speed".to_string(), "coordinates (unprojected)".to_string()];
}

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
        .select(app.tab_index)
        .style(ratatui::style::Style::default().fg(ratatui::style::Color::Cyan))
        .highlight_style(
            ratatui::style::Style::default()
                .add_modifier(ratatui::style::Modifier::BOLD)
                .add_modifier(ratatui::style::Modifier::UNDERLINED),
        );
    frame.render_widget(tabs, areas[0]);

    let bold_style = ratatui::style::Style::default().add_modifier(ratatui::style::Modifier::BOLD);

    if app.tab_index == 0 {
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
        let track = &app.tracks[app.tab_index - 1];
        if !track.locations.is_empty() {
            let block = ratatui::widgets::Block::default();
            let track_areas = ratatui::layout::Layout::default()
                .direction(ratatui::layout::Direction::Vertical)
                .constraints(
                    [
                        ratatui::layout::Constraint::Min(11),
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

            let intervals = crate::location::track::intervals(&track.locations);
            let overground_distances =
                crate::location::track::overground_distances(&track.locations);
            let ground_speeds = crate::location::track::ground_speeds(&track.locations);

            let mut total_interval = chrono::Duration::seconds(0);
            for interval in &intervals {
                total_interval = total_interval + interval.to_owned();
            }

            let start_time = track.locations.first().unwrap().location.time;
            let end_time = track.locations.last().unwrap().location.time;
            let seconds_since_start: Vec<f64> = track
                .locations
                .iter()
                .map(|location| (location.location.time - start_time).num_seconds() as f64)
                .collect();

            let locations_with_altitude: Vec<&crate::location::BalloonLocation> = track
                .locations
                .iter()
                .filter(|location| location.location.altitude.is_some())
                .collect();

            let has_altitude = !locations_with_altitude.is_empty();

            let mut altitudes = Vec::<f64>::new();
            let mut ascents = Vec::<f64>::new();
            let mut ascent_rates = Vec::<f64>::new();
            let mut positive_ascent_rates = Vec::<f64>::new();
            let mut negative_ascent_rates = Vec::<f64>::new();
            let mut altitude_range = [0.0, 1.0];
            if has_altitude {
                ascents = crate::location::track::ascents(&track.locations);
                ascent_rates = crate::location::track::ascent_rates(&track.locations);

                positive_ascent_rates = ascent_rates
                    .iter()
                    .filter_map(|ascent_rate| {
                        if ascent_rate > &0.0 {
                            Some(ascent_rate.to_owned())
                        } else {
                            None
                        }
                    })
                    .collect();
                negative_ascent_rates = ascent_rates
                    .iter()
                    .filter_map(|ascent_rate| {
                        if ascent_rate < &0.0 {
                            Some(ascent_rate.to_owned())
                        } else {
                            None
                        }
                    })
                    .collect();

                altitudes = locations_with_altitude
                    .iter()
                    .filter_map(|location| location.location.altitude)
                    .collect();
                altitude_range = [
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
            }

            let last_location = track.locations.last().unwrap();

            let mut last_location_info = vec![ratatui::text::Spans::from(vec![
                ratatui::text::Span::styled("time: ", bold_style),
                ratatui::text::Span::raw(format!(
                    "{:} ({:})",
                    crate::utilities::duration_string(
                        &(last_location.location.time - chrono::Local::now())
                    ),
                    last_location.location.time.format(&crate::DATETIME_FORMAT),
                )),
            ])];

            if track.locations.len() > 1 {
                last_location_info.push(ratatui::text::Spans::from(vec![
                    ratatui::text::Span::styled("since prev.: ", bold_style),
                    ratatui::text::Span::raw(crate::utilities::duration_string(
                        intervals.last().unwrap(),
                    )),
                ]));
            }

            last_location_info.push(ratatui::text::Spans::from(vec![
                ratatui::text::Span::styled("coordinates: ", bold_style),
                ratatui::text::Span::raw(format!(
                    "({:.2}, {:.2})",
                    &last_location.location.coord.x, &last_location.location.coord.y,
                )),
            ]));

            if let Some(altitude) = last_location.location.altitude {
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
                        ratatui::text::Span::raw(format!(
                            "{:.2} m/s",
                            ground_speeds.last().unwrap(),
                        )),
                    ]),
                ]);

                if has_altitude {
                    last_location_info.extend([
                        ratatui::text::Spans::from(vec![
                            ratatui::text::Span::styled("ascent: ", bold_style),
                            ratatui::text::Span::raw(format!("{:.2} m", ascents.last().unwrap(),)),
                        ]),
                        ratatui::text::Spans::from(vec![
                            ratatui::text::Span::styled("ascent rate: ", bold_style),
                            ratatui::text::Span::raw(format!(
                                "{:.2} m/s",
                                ascent_rates.last().unwrap(),
                            )),
                        ]),
                    ]);
                }
            }

            let last_location_info = ratatui::widgets::Paragraph::new(last_location_info)
                .block(
                    ratatui::widgets::Block::default()
                        .borders(ratatui::widgets::Borders::ALL)
                        .title(format!("Location #{:}", track.locations.len())),
                )
                .wrap(ratatui::widgets::Wrap { trim: true });
            frame.render_widget(last_location_info, track_info_areas[0]);

            if track.locations.len() > 1 {
                let mut track_info = vec![];
                if has_altitude {
                    track_info.extend([
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
                    ]);
                }

                track_info.extend([
                    ratatui::text::Spans::from(vec![
                        ratatui::text::Span::styled("ground speed: ", bold_style),
                        ratatui::text::Span::raw(format!(
                            "{:.2} m/s",
                            ground_speeds.iter().sum::<f64>() / ground_speeds.len() as f64,
                        )),
                    ]),
                    ratatui::text::Spans::from(vec![
                        ratatui::text::Span::styled("time interval: ", bold_style),
                        ratatui::text::Span::raw(crate::utilities::duration_string(
                            &chrono::Duration::seconds(
                                (total_interval.num_seconds() as f64 / intervals.len() as f64)
                                    as i64,
                            ),
                        )),
                    ]),
                ]);

                let track_info = ratatui::widgets::Paragraph::new(track_info)
                    .block(
                        ratatui::widgets::Block::default()
                            .borders(ratatui::widgets::Borders::ALL)
                            .title("Averages"),
                    )
                    .wrap(ratatui::widgets::Wrap { trim: true });
                frame.render_widget(track_info, track_info_areas[1]);
            }

            let mut descent_info = vec![];
            if track.descending() {
                if has_altitude {
                    descent_info.push(ratatui::text::Spans::from(vec![
                        ratatui::text::Span::styled("max altitude: ", bold_style),
                        ratatui::text::Span::raw(format!("{:.2} m", altitude_range[1])),
                    ]));
                }

                if let Some(estimated_time_to_ground) = track.estimated_time_to_ground() {
                    let landing_time = last_location.location.time + estimated_time_to_ground;

                    descent_info.push(ratatui::text::Spans::from(vec![
                        ratatui::text::Span::styled("est. landing: ", bold_style),
                        ratatui::text::Span::raw(format!(
                            "{:} ({:})",
                            crate::utilities::duration_string(
                                &(landing_time - chrono::Local::now())
                            ),
                            landing_time.format(&crate::DATETIME_FORMAT),
                        )),
                    ]));
                }

                if let Some(freefall_estimate) = track.falling() {
                    let landing_time =
                        last_location.location.time + freefall_estimate.time_to_ground;

                    descent_info.push(ratatui::text::Spans::from(vec![
                        ratatui::text::Span::styled("@ term. vel.: ", bold_style),
                        ratatui::text::Span::raw(format!(
                            "{:} ({:})",
                            crate::utilities::duration_string(
                                &(landing_time - chrono::Local::now())
                            ),
                            landing_time.format(&crate::DATETIME_FORMAT),
                        )),
                    ]));
                }
            }

            if let Some(prediction) = &track.prediction {
                let predicted_landing_location = prediction.last().unwrap();
                descent_info.extend([
                    ratatui::text::Spans::from(vec![
                        ratatui::text::Span::styled("pred. landing: ", bold_style),
                        ratatui::text::Span::raw(format!(
                            "{:} ({:})",
                            crate::utilities::duration_string(
                                &(predicted_landing_location.location.time - chrono::Local::now()),
                            ),
                            predicted_landing_location
                                .location
                                .time
                                .format(&crate::DATETIME_FORMAT)
                        )),
                    ]),
                    ratatui::text::Spans::from(vec![
                        ratatui::text::Span::styled("pred. landing loc.: ", bold_style),
                        ratatui::text::Span::raw(format!(
                            "({:.2}, {:.2})",
                            predicted_landing_location.location.coord.x,
                            predicted_landing_location.location.coord.y,
                        )),
                    ]),
                ]);
            }

            if !descent_info.is_empty() {
                let descent_info = ratatui::widgets::Paragraph::new(descent_info)
                    .block(
                        ratatui::widgets::Block::default()
                            .borders(ratatui::widgets::Borders::ALL)
                            .title("Descent"),
                    )
                    .wrap(ratatui::widgets::Wrap { trim: true });
                frame.render_widget(descent_info, track_info_areas[2]);
            } else if track.ascending() {
                if let Some(prediction) = &track.prediction {
                    let locations_with_altitudes =
                        crate::location::track::with_altitude(prediction);
                    let mut predicted_max_altitude_location: &crate::location::Location =
                        &locations_with_altitudes.last().unwrap().location;
                    for location in &locations_with_altitudes {
                        if location.location.altitude.unwrap()
                            > predicted_max_altitude_location.altitude.unwrap()
                        {
                            predicted_max_altitude_location = &location.location;
                        }
                    }

                    if has_altitude {
                        let estimated_time_to_max_altitude = chrono::Duration::seconds(
                            ((positive_ascent_rates.iter().sum::<f64>()
                                / positive_ascent_rates.len() as f64)
                                / predicted_max_altitude_location.altitude.unwrap())
                                as i64,
                        );
                        let ascent_info = ratatui::widgets::Paragraph::new(vec![
                            ratatui::text::Spans::from(vec![
                                ratatui::text::Span::styled("est. max alt. at: ", bold_style),
                                ratatui::text::Span::raw(format!(
                                    "{:} ({:})",
                                    (chrono::Local::now() + estimated_time_to_max_altitude)
                                        .format(&crate::DATETIME_FORMAT),
                                    crate::utilities::duration_string(
                                        &estimated_time_to_max_altitude
                                    )
                                )),
                            ]),
                            ratatui::text::Spans::from(vec![
                                ratatui::text::Span::styled("pred. max alt. at: ", bold_style),
                                ratatui::text::Span::raw(format!(
                                    "{:} ({:})",
                                    predicted_max_altitude_location
                                        .time
                                        .format(&crate::DATETIME_FORMAT),
                                    crate::utilities::duration_string(
                                        &(predicted_max_altitude_location.time
                                            - chrono::Local::now())
                                    )
                                )),
                            ]),
                        ])
                        .block(
                            ratatui::widgets::Block::default()
                                .borders(ratatui::widgets::Borders::ALL)
                                .title("Ascent"),
                        )
                        .wrap(ratatui::widgets::Wrap { trim: true });
                        frame.render_widget(ascent_info, track_info_areas[2]);
                    }
                }
            }

            let mut datasets = vec![];
            let mut x_range = [0.0, 1.0];
            let mut y_range = [0.0, 1.0];
            let mut x_labels = vec![];
            let mut y_labels = vec![];

            let time_format = if end_time - start_time < chrono::Duration::days(1) {
                "%H:%M:%S"
            } else {
                &crate::DATETIME_FORMAT
            };
            let time_labels = [
                start_time,
                start_time + ((end_time - start_time) / 2),
                end_time,
            ]
            .iter()
            .map(|value| ratatui::text::Span::raw(value.format(time_format).to_string()))
            .collect();

            let chart_name = CHARTS.get(app.chart_index).unwrap();
            let telemetry_data: Vec<(f64, f64)>;
            let predicted_data: Vec<(f64, f64)>;

            let mut draw_chart = true;
            if chart_name == "altitude / time" && has_altitude {
                telemetry_data = seconds_since_start
                    .iter()
                    .zip(altitudes.iter())
                    .map(|tuple| (tuple.0.to_owned(), tuple.1.to_owned()))
                    .collect();
                datasets.push(
                    ratatui::widgets::Dataset::default()
                        .marker(ratatui::symbols::Marker::Braille)
                        .style(ratatui::style::Style::default().fg(ratatui::style::Color::Blue))
                        .data(&telemetry_data)
                        .name("telemetry")
                        .graph_type(ratatui::widgets::GraphType::Scatter),
                );

                x_range = [0.0, (end_time - start_time).num_seconds() as f64];
                y_range = altitude_range;

                if let Some(prediction) = &track.prediction {
                    let with_altitude = crate::location::track::with_altitude(prediction);
                    let seconds_since_start: Vec<f64> = with_altitude
                        .iter()
                        .map(|location| (location.location.time - start_time).num_seconds() as f64)
                        .collect();
                    let altitudes = crate::location::track::altitudes(&with_altitude);

                    let min_x = seconds_since_start
                        .iter()
                        .min_by(|a, b| a.total_cmp(b))
                        .unwrap()
                        .to_owned();
                    let max_x = seconds_since_start
                        .iter()
                        .max_by(|a, b| a.total_cmp(b))
                        .unwrap()
                        .to_owned();
                    if min_x < x_range[0] {
                        x_range[0] = min_x;
                    }
                    if max_x > x_range[1] {
                        x_range[1] = max_x;
                    }
                    let min_y = altitudes
                        .iter()
                        .min_by(|a, b| a.total_cmp(b))
                        .unwrap()
                        .to_owned();
                    let max_y = altitudes
                        .iter()
                        .max_by(|a, b| a.total_cmp(b))
                        .unwrap()
                        .to_owned();
                    if min_y < y_range[0] {
                        y_range[0] = min_y;
                    }
                    if max_y > y_range[1] {
                        y_range[1] = max_y;
                    }

                    predicted_data = seconds_since_start
                        .iter()
                        .zip(altitudes.iter())
                        .map(|tuple| (tuple.0.to_owned(), tuple.1.to_owned()))
                        .collect();
                    datasets.push(
                        ratatui::widgets::Dataset::default()
                            .marker(ratatui::symbols::Marker::Braille)
                            .style(ratatui::style::Style::default().fg(ratatui::style::Color::Red))
                            .data(&predicted_data)
                            .name("prediction")
                            .graph_type(ratatui::widgets::GraphType::Scatter),
                    );
                }

                x_labels = time_labels;
                y_labels = [
                    y_range[0],
                    y_range[0] + ((y_range[1] - y_range[0]) / 2.0),
                    y_range[1],
                ]
                .iter()
                .map(|value| ratatui::text::Span::raw(format!("{:.1} m", value)))
                .collect();
            } else if chart_name == "ascent rate / time"
                && has_altitude
                && locations_with_altitude.len() > 1
            {
                telemetry_data = seconds_since_start
                    .iter()
                    .zip(ascent_rates.iter())
                    .map(|tuple| (tuple.0.to_owned(), tuple.1.to_owned()))
                    .collect();
                datasets.push(
                    ratatui::widgets::Dataset::default()
                        .marker(ratatui::symbols::Marker::Braille)
                        .style(ratatui::style::Style::default().fg(ratatui::style::Color::Blue))
                        .data(&telemetry_data)
                        .name("telemetry")
                        .graph_type(ratatui::widgets::GraphType::Scatter),
                );

                x_range = [0.0, (end_time - start_time).num_seconds() as f64];
                y_range = [
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

                if let Some(prediction) = &track.prediction {
                    let locations_with_altitude = crate::location::track::with_altitude(prediction);
                    let seconds_since_start: Vec<f64> = locations_with_altitude
                        .iter()
                        .map(|location| (location.location.time - start_time).num_seconds() as f64)
                        .collect();

                    let ascent_rates =
                        crate::location::track::ascent_rates(locations_with_altitude.as_slice());

                    let min_x = seconds_since_start
                        .iter()
                        .min_by(|a, b| a.total_cmp(b))
                        .unwrap()
                        .to_owned();
                    let max_x = seconds_since_start
                        .iter()
                        .max_by(|a, b| a.total_cmp(b))
                        .unwrap()
                        .to_owned();
                    if min_x < x_range[0] {
                        x_range[0] = min_x;
                    }
                    if max_x > x_range[1] {
                        x_range[1] = max_x;
                    }
                    let min_y = ascent_rates
                        .iter()
                        .min_by(|a, b| a.total_cmp(b))
                        .unwrap()
                        .to_owned();
                    let max_y = ascent_rates
                        .iter()
                        .max_by(|a, b| a.total_cmp(b))
                        .unwrap()
                        .to_owned();
                    if min_y < y_range[0] {
                        y_range[0] = min_y;
                    }
                    if max_y > y_range[1] {
                        y_range[1] = max_y;
                    }

                    predicted_data = seconds_since_start
                        .into_iter()
                        .zip(ascent_rates.into_iter())
                        .collect();
                    datasets.push(
                        ratatui::widgets::Dataset::default()
                            .marker(ratatui::symbols::Marker::Braille)
                            .style(ratatui::style::Style::default().fg(ratatui::style::Color::Red))
                            .data(&predicted_data)
                            .name("prediction")
                            .graph_type(ratatui::widgets::GraphType::Scatter),
                    );
                }

                x_labels = time_labels;
                y_labels = [
                    y_range[0],
                    y_range[0] + ((y_range[1] - y_range[0]) / 2.0),
                    y_range[1],
                ]
                .iter()
                .map(|value| ratatui::text::Span::raw(format!("{:.1} m/s", value)))
                .collect();
            } else if chart_name == "altitude / ground speed"
                && has_altitude
                && locations_with_altitude.len() > 1
            {
                telemetry_data = altitudes
                    .into_iter()
                    .zip(ground_speeds.clone().into_iter())
                    .collect();
                datasets.push(
                    ratatui::widgets::Dataset::default()
                        .marker(ratatui::symbols::Marker::Braille)
                        .style(ratatui::style::Style::default().fg(ratatui::style::Color::Blue))
                        .data(&telemetry_data)
                        .name("telemetry")
                        .graph_type(ratatui::widgets::GraphType::Scatter),
                );

                x_range = altitude_range;
                y_range = [
                    ground_speeds
                        .iter()
                        .min_by(|a, b| a.total_cmp(b))
                        .unwrap()
                        .to_owned(),
                    ground_speeds
                        .iter()
                        .max_by(|a, b| a.total_cmp(b))
                        .unwrap()
                        .to_owned(),
                ];

                if let Some(prediction) = &track.prediction {
                    let with_altitude = crate::location::track::with_altitude(prediction);
                    let altitudes = crate::location::track::altitudes(&with_altitude);
                    let ground_speeds = crate::location::track::ground_speeds(&with_altitude);

                    let min_x = altitudes
                        .iter()
                        .min_by(|a, b| a.total_cmp(b))
                        .unwrap()
                        .to_owned();
                    let max_x = altitudes
                        .iter()
                        .max_by(|a, b| a.total_cmp(b))
                        .unwrap()
                        .to_owned();
                    if min_x < x_range[0] {
                        x_range[0] = min_x;
                    }
                    if max_x > x_range[1] {
                        x_range[1] = max_x;
                    }
                    let min_y = ground_speeds
                        .iter()
                        .min_by(|a, b| a.total_cmp(b))
                        .unwrap()
                        .to_owned();
                    let max_y = ground_speeds
                        .iter()
                        .max_by(|a, b| a.total_cmp(b))
                        .unwrap()
                        .to_owned();
                    if min_y < y_range[0] {
                        y_range[0] = min_y;
                    }
                    if max_y > y_range[1] {
                        y_range[1] = max_y;
                    }

                    predicted_data = altitudes
                        .into_iter()
                        .zip(ground_speeds.into_iter())
                        .collect();
                    datasets.push(
                        ratatui::widgets::Dataset::default()
                            .marker(ratatui::symbols::Marker::Braille)
                            .style(ratatui::style::Style::default().fg(ratatui::style::Color::Red))
                            .data(&predicted_data)
                            .name("prediction")
                            .graph_type(ratatui::widgets::GraphType::Scatter),
                    );
                }

                x_labels = [
                    x_range[0],
                    x_range[0] + ((x_range[1] - x_range[0]) / 2.0),
                    x_range[1],
                ]
                .iter()
                .map(|value| ratatui::text::Span::raw(format!("{:.1} m", value)))
                .collect();
                y_labels = [
                    y_range[0],
                    y_range[0] + ((y_range[1] - y_range[0]) / 2.0),
                    y_range[1],
                ]
                .iter()
                .map(|value| ratatui::text::Span::raw(format!("{:.1} m/s", value)))
                .collect();
            } else if chart_name == "coordinates (unprojected)" {
                telemetry_data = track
                    .locations
                    .iter()
                    .map(|location| location.location.coord.x_y())
                    .collect();
                datasets.push(
                    ratatui::widgets::Dataset::default()
                        .marker(ratatui::symbols::Marker::Braille)
                        .style(ratatui::style::Style::default().fg(ratatui::style::Color::Blue))
                        .data(&telemetry_data)
                        .name("telemetry")
                        .graph_type(ratatui::widgets::GraphType::Scatter),
                );

                x_range = [
                    telemetry_data
                        .iter()
                        .map(|coordinate| coordinate.0)
                        .min_by(|a, b| a.total_cmp(b))
                        .unwrap(),
                    telemetry_data
                        .iter()
                        .map(|coordinate| coordinate.0)
                        .max_by(|a, b| a.total_cmp(b))
                        .unwrap(),
                ];
                y_range = [
                    telemetry_data
                        .iter()
                        .map(|coordinate| coordinate.1)
                        .min_by(|a, b| a.total_cmp(b))
                        .unwrap(),
                    telemetry_data
                        .iter()
                        .map(|coordinate| coordinate.1)
                        .max_by(|a, b| a.total_cmp(b))
                        .unwrap(),
                ];

                if let Some(prediction) = &track.prediction {
                    let predicted_x: Vec<f64> = prediction
                        .iter()
                        .map(|location| location.location.coord.x)
                        .collect();
                    let predicted_y: Vec<f64> = prediction
                        .iter()
                        .map(|location| location.location.coord.y)
                        .collect();

                    let min_x = predicted_x
                        .iter()
                        .min_by(|a, b| a.total_cmp(b))
                        .unwrap()
                        .to_owned();
                    let max_x = predicted_x
                        .iter()
                        .max_by(|a, b| a.total_cmp(b))
                        .unwrap()
                        .to_owned();
                    if min_x < x_range[0] {
                        x_range[0] = min_x;
                    }
                    if max_x > x_range[1] {
                        x_range[1] = max_x;
                    }
                    let min_y = predicted_y
                        .iter()
                        .min_by(|a, b| a.total_cmp(b))
                        .unwrap()
                        .to_owned();
                    let max_y = predicted_y
                        .iter()
                        .max_by(|a, b| a.total_cmp(b))
                        .unwrap()
                        .to_owned();
                    if min_y < y_range[0] {
                        y_range[0] = min_y;
                    }
                    if max_y > y_range[1] {
                        y_range[1] = max_y;
                    }

                    predicted_data = predicted_x
                        .into_iter()
                        .zip(predicted_y.into_iter())
                        .collect();
                    datasets.push(
                        ratatui::widgets::Dataset::default()
                            .marker(ratatui::symbols::Marker::Braille)
                            .style(ratatui::style::Style::default().fg(ratatui::style::Color::Red))
                            .data(&predicted_data)
                            .name("prediction")
                            .graph_type(ratatui::widgets::GraphType::Scatter),
                    );
                }

                x_labels = [
                    x_range[0],
                    x_range[0] + ((x_range[1] - x_range[0]) / 2.0),
                    x_range[1],
                ]
                .iter()
                .map(|value| ratatui::text::Span::raw(format!("{:.1}", value)))
                .collect();
                y_labels = [
                    y_range[0],
                    y_range[0] + ((y_range[1] - y_range[0]) / 2.0),
                    y_range[1],
                ]
                .iter()
                .map(|value| ratatui::text::Span::raw(format!("{:.1}", value)))
                .collect();
            } else {
                draw_chart = false;
            }

            if draw_chart {
                let chart = ratatui::widgets::Chart::new(datasets)
                    .block(
                        ratatui::widgets::Block::default()
                            .title(ratatui::text::Span::styled(
                                chart_name,
                                ratatui::style::Style::default()
                                    .fg(ratatui::style::Color::Cyan)
                                    .add_modifier(ratatui::style::Modifier::BOLD),
                            ))
                            .borders(ratatui::widgets::Borders::ALL),
                    )
                    .x_axis(
                        ratatui::widgets::Axis::default()
                            .style(
                                ratatui::style::Style::default()
                                    .fg(ratatui::style::Color::DarkGray),
                            )
                            .labels(x_labels)
                            .labels_alignment(ratatui::layout::Alignment::Right)
                            .bounds(x_range),
                    )
                    .y_axis(
                        ratatui::widgets::Axis::default()
                            .style(
                                ratatui::style::Style::default()
                                    .fg(ratatui::style::Color::DarkGray),
                            )
                            .labels(y_labels)
                            .labels_alignment(ratatui::layout::Alignment::Right)
                            .bounds(y_range),
                    );
                frame.render_widget(chart, track_areas[1]);
            }

            frame.render_widget(block, areas[1]);
        }
    }
}
