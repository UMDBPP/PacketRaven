use serde_with::serde_as;

#[derive(serde::Deserialize, Clone)]
#[serde(untagged)]
pub enum PredictionConfiguration {
    Single(Prediction),
    Cloud {
        default: Prediction,
        perturbations: std::collections::HashMap<String, Prediction>,
    },
}

fn default_name() -> String {
    String::from("prediction")
}

#[derive(serde::Deserialize, PartialEq, Debug, Clone)]
pub struct Prediction {
    pub start: crate::location::Location,
    pub profile: StandardProfile,
    pub float: Option<FloatProfile>,
    pub output_file: Option<std::path::PathBuf>,
    pub api_url: Option<String>,
    #[serde(default = "default_name")]
    pub name: String,
}

impl Prediction {
    pub fn to_tawhiri_query(&self) -> crate::prediction::tawhiri::TawhiriQuery {
        let profile = match &self.float {
            Some(float) => crate::prediction::FlightProfile::new_float(
                self.profile.ascent_rate,
                Some(float.altitude),
                float.duration,
                float.uncertainty,
                self.profile.burst_altitude,
                self.profile.sea_level_descent_rate,
            ),
            None => crate::prediction::FlightProfile::new_standard(
                self.profile.ascent_rate,
                self.profile.burst_altitude,
                self.profile.sea_level_descent_rate,
            ),
        };

        crate::prediction::tawhiri::TawhiriQuery::new(
            &self.start,
            &profile,
            None,
            None,
            None,
            false,
        )
    }
}

fn default_sea_level_descent_rate() -> f64 {
    -crate::model::FreefallEstimate::new(0.0).ascent_rate
}

fn default_descent_only() -> bool {
    false
}

#[derive(serde::Deserialize, PartialEq, Debug, Clone)]
pub struct StandardProfile {
    pub ascent_rate: f64,
    pub burst_altitude: f64,
    #[serde(default = "default_sea_level_descent_rate")]
    pub sea_level_descent_rate: f64,
    #[serde(default = "default_descent_only")]
    pub descent_only: bool,
}

#[serde_as]
#[derive(serde::Deserialize, PartialEq, Debug, Clone)]
pub struct FloatProfile {
    pub altitude: f64,
    pub uncertainty: Option<f64>,
    #[serde_as(as = "serde_with::DurationSeconds<i64>")]
    pub duration: chrono::Duration,
}
