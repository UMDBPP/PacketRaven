#[derive(Clone)]
pub struct FreefallEstimate {
    pub ascent_rate: f64,
    pub ascent_rate_uncertainty: f64,
    pub time_to_ground: chrono::Duration,
}

impl FreefallEstimate {
    // estimation of freefall w/ parachute, based on historical flight data
    pub fn new(altitude: f64) -> FreefallEstimate {
        // `dh/dt` based on historical flight data
        let ascent_rate = -5.8e-08 * altitude.powi(2) - 6.001;

        // TODO: propagate uncertainty
        let ascent_rate_uncertainty = (0.2 * ascent_rate).abs();

        // integration of `(1/(dh/dt)) dh` based on historical flight data
        // TODO make this model better with ML
        let time_to_ground = chrono::Duration::milliseconds(
            (1695.02 * (9.8311e-05 * altitude).atan() * 1000.0) as i64,
        );

        FreefallEstimate {
            ascent_rate,
            ascent_rate_uncertainty,
            time_to_ground,
        }
    }
}

impl crate::location::BalloonLocation {
    pub fn estimate_freefall(&self) -> FreefallEstimate {
        FreefallEstimate::new(
            self.altitude
                .expect("location must have an altitude to estimate freefall"),
        )
    }
}
