use serde_with::serde_as;

#[derive(serde::Deserialize)]
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

#[derive(serde::Deserialize, PartialEq, Debug)]
pub struct Prediction {
    pub start: StartLocation,
    pub profile: StandardProfile,
    pub float: Option<FloatProfile>,
    pub output: Option<crate::configuration::PathConfiguration>,
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
            &self.start.to_balloon_location(),
            &profile,
            None,
            None,
            None,
            false,
        )
    }
}

#[derive(serde::Deserialize, PartialEq, Debug)]
pub struct StartLocation {
    pub location: Vec<f64>,
    #[serde(with = "crate::parse::deserialize_local_datetime_string")]
    pub time: chrono::DateTime<chrono::Local>,
}

impl StartLocation {
    pub fn to_balloon_location(&self) -> crate::location::BalloonLocation {
        crate::location::BalloonLocation {
            time: self.time.with_timezone(&chrono::Local),
            location: geo::point!(x: self.location[0], y: self.location[1]),
            altitude: if self.location.len() > 2 {
                Some(self.location[2])
            } else {
                None
            },
            data: crate::location::BalloonData::default(),
        }
    }
}

fn default_sea_level_descent_rate() -> f64 {
    -crate::model::FreefallEstimate::new(0.0).ascent_rate
}

fn default_descent_only() -> bool {
    false
}

#[derive(serde::Deserialize, PartialEq, Debug)]
pub struct StandardProfile {
    pub ascent_rate: f64,
    pub burst_altitude: f64,
    #[serde(default = "default_sea_level_descent_rate")]
    pub sea_level_descent_rate: f64,
    #[serde(default = "default_descent_only")]
    pub descent_only: bool,
}

#[serde_as]
#[derive(serde::Deserialize, PartialEq, Debug)]
pub struct FloatProfile {
    pub altitude: f64,
    pub uncertainty: Option<f64>,
    #[serde_as(as = "serde_with::DurationSeconds<i64>")]
    pub duration: chrono::Duration,
}
