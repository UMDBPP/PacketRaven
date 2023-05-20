pub mod tawhiri;

lazy_static::lazy_static! {
    static ref DEFAULT_FLOAT_UNCERTAINTY: f64 = 500.0;
}

#[derive(Clone)]
pub struct FlightProfile {
    pub ascent_rate: f64,
    pub float_altitude: Option<f64>,
    pub float_duration: Option<chrono::Duration>,
    pub float_uncertainty: f64,
    pub burst_altitude: f64,
    pub sea_level_descent_rate: f64,
}

impl FlightProfile {
    pub fn new(
        ascent_rate: f64,
        float_altitude: Option<f64>,
        float_duration: Option<chrono::Duration>,
        float_uncertainty: Option<f64>,
        burst_altitude: f64,
        sea_level_descent_rate: f64,
    ) -> Self {
        Self {
            ascent_rate,
            float_altitude,
            float_duration,
            float_uncertainty: float_uncertainty.unwrap_or(*DEFAULT_FLOAT_UNCERTAINTY),
            burst_altitude,
            sea_level_descent_rate,
        }
    }

    pub fn new_float(
        ascent_rate: f64,
        float_altitude: Option<f64>,
        float_duration: chrono::Duration,
        float_uncertainty: Option<f64>,
        burst_altitude: f64,
        sea_level_descent_rate: f64,
    ) -> Self {
        Self::new(
            ascent_rate,
            float_altitude,
            Some(float_duration),
            float_uncertainty,
            burst_altitude,
            sea_level_descent_rate,
        )
    }

    pub fn new_standard(
        ascent_rate: f64,
        burst_altitude: f64,
        sea_level_descent_rate: f64,
    ) -> Self {
        Self::new(
            ascent_rate,
            None,
            None,
            None,
            burst_altitude,
            sea_level_descent_rate,
        )
    }
}

pub struct BalloonPredictionQuery {
    pub api_url: String,
    pub start: crate::location::BalloonLocation,
    pub profile: FlightProfile,
    pub name: Option<String>,
    pub descent_only: bool,
}

impl BalloonPredictionQuery {
    pub fn new(
        api_url: String,
        start: &crate::location::BalloonLocation,
        profile: &FlightProfile,
        name: Option<String>,
        descent_only: bool,
    ) -> Self {
        Self {
            api_url,
            start: start.to_owned(),
            profile: profile.to_owned(),
            name,
            descent_only,
        }
    }
}
