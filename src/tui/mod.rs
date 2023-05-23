mod app;
mod draw;

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

    let app = app::PacketravenApp::new(configuration, log_level);
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
    mut app: app::PacketravenApp,
) -> std::io::Result<()> {
    let tick_rate = app.configuration.time.interval.to_std().unwrap();

    // set the first tick to be in the past to update immediately
    let mut last_tick = std::time::Instant::now() - tick_rate;

    loop {
        terminal.draw(|frame| draw::draw(frame, &app))?;

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

fn reset_terminal() -> Result<(), Box<dyn std::error::Error>> {
    crossterm::terminal::disable_raw_mode()?;
    crossterm::execute!(std::io::stdout(), crossterm::terminal::LeaveAlternateScreen)?;

    Ok(())
}
