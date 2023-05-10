pub struct TawhiriQuery {
    pub query: crate::prediction::BalloonPredictionQuery,
    pub dataset_time: Option<chrono::DateTime<chrono::Utc>>,
    pub version: Option<f64>,
}

impl TawhiriQuery {
    pub fn new(
        start: &crate::location::BalloonLocation,
        profile: &crate::prediction::FlightProfile,
        dataset_time: Option<chrono::DateTime<chrono::Utc>>,
        version: Option<f64>,
        name: Option<String>,
        descent_only: bool,
    ) -> TawhiriQuery {
        TawhiriQuery {
            query: crate::prediction::BalloonPredictionQuery::new(
                String::from("https://api.v2.sondehub.org/tawhiri"),
                start,
                profile,
                name,
                descent_only,
            ),
            dataset_time,
            version,
        }
    }

    fn url(&self) -> String {
        // CUSF API requires longitude in 0-360 format
        let mut start_location = self.query.start.location;
        if start_location.x() < 0.0 {
            start_location = geo::point!(x: start_location.x() + 360.0, y: start_location.y())
        }

        let burst_altitude = match self.query.descent_only {
            true => {
                self.query
                    .start
                    .altitude
                    .expect("no start altitude provided for descent prediction")
                    + 0.1
            }
            false => self.query.profile.burst_altitude,
        };

        let mut parameters = vec![
            format!("launch_longitude={:}", start_location.x()),
            format!("launch_latitude={:}", start_location.y()),
            format!("launch_datetime={:}", self.query.start.time.to_rfc3339()),
            format!("ascent_rate={:}", self.query.profile.ascent_rate),
            format!("burst_altitude={:}", burst_altitude),
            format!(
                "descent_rate={:}",
                self.query.profile.sea_level_descent_rate,
            ),
        ];

        if let Some(altitude) = self.query.start.altitude {
            parameters.push(format!("launch_altitude={:}", altitude));
        }
        parameters.push(format!(
            "profile={:}",
            match self.query.profile.float_duration {
                Some(_) => String::from("float_profile"),
                None => String::from("standard_profile"),
            },
        ));
        if let Some(dataset_time) = self.dataset_time {
            parameters.push(format!("dataset={:}", dataset_time.to_rfc3339()));
        }
        if let Some(version) = self.version {
            parameters.push(format!("version={:}", version));
        }

        if !self.query.descent_only {
            if let Some(float_duration) = self.query.profile.float_duration {
                let float_altitude = self
                    .query
                    .profile
                    .float_altitude
                    .unwrap_or(self.query.profile.burst_altitude);
                parameters.push(format!("float_altitude={:}", float_altitude));
                let start_altitude = self.query.start.altitude.unwrap_or(0.0);
                let float_start_time = self.query.start.time
                    + chrono::Duration::seconds(
                        (float_altitude - start_altitude / self.query.profile.ascent_rate) as i64,
                    );
                parameters.push(format!(
                    "stop_datetime={:}",
                    (float_start_time + float_duration).to_rfc3339()
                ));
            }
        }

        format!("{:}?{:}", self.query.api_url, parameters.join("&"))
    }

    fn get(&self) -> Result<TawhiriResponse, TawhiriError> {
        let response = reqwest::blocking::get(self.url()).expect("error retrieving prediction");

        match &response.status() {
            &reqwest::StatusCode::OK => {
                // deserialize JSON into struct
                let mut tawhiri_response: TawhiriResponse =
                    response.json().expect("error parsing response JSON");

                // since tawhiri does not currently include a descent stage when querying a float profile,
                // we need to query one from the end of the float stage and append it to the prediction
                match tawhiri_response.request {
                    TawhiriRequest::FloatProfile { .. } => {
                        let mut descent_stage_exists: bool = false;
                        for stage in &tawhiri_response.prediction {
                            if stage.stage == "descent" {
                                descent_stage_exists = true;
                                break;
                            }
                        }
                        if !descent_stage_exists {
                            let mut float_stage_exists: bool = false;
                            for stage in &tawhiri_response.prediction {
                                if stage.stage == "float" {
                                    float_stage_exists = true;
                                    let float_end_location =
                                        stage.trajectory.last().unwrap().to_balloon_location();
                                    let descent_query = TawhiriQuery::new(
                                        &float_end_location,
                                        &crate::prediction::FlightProfile::new_standard(
                                            10.0,
                                            float_end_location.altitude.unwrap(),
                                            self.query.profile.sea_level_descent_rate,
                                        ),
                                        self.dataset_time,
                                        self.version,
                                        None,
                                        true,
                                    );
                                    let descent: TawhiriResponse = descent_query.get().unwrap();
                                    for stage in descent.prediction {
                                        if stage.stage == "descent" {
                                            tawhiri_response.prediction.push(stage);
                                            break;
                                        }
                                    }
                                    break;
                                }
                            }
                            if !float_stage_exists {
                                return Err(TawhiriError::NoFloatStage);
                            }
                        }
                    }
                    TawhiriRequest::StandardProfile { .. } => {}
                }

                if self.query.descent_only {
                    let mut descent_stage_found: bool = false;
                    let descent_only_prediction: Vec<TawhiriPrediction>;
                    for stage in &tawhiri_response.prediction {
                        if stage.stage == "descent" {
                            descent_only_prediction = vec![stage.to_owned()];
                            tawhiri_response.prediction = descent_only_prediction;
                            descent_stage_found = true;
                            break;
                        }
                    }
                    if !descent_stage_found {
                        return Err(TawhiriError::NoDescentStage);
                    }
                }
                Ok(tawhiri_response)
            }
            _ => {
                let status = &response.status();
                // https://tawhiri.readthedocs.io/en/latest/api.html#error-fragment
                let tawhiri_error: TawhiriErrorResponse = response.json().unwrap();
                return Err(TawhiriError::HttpErrorStatus {
                    status: status.as_u16(),
                    description: tawhiri_error.description,
                });
            }
        }
    }

    pub fn retrieve_prediction(&self) -> crate::location::track::BalloonTrack {
        let response = self.get().unwrap();

        let mut locations = vec![];

        for stage in response.prediction {
            for location in stage.trajectory {
                locations.push(location.to_balloon_location());
            }
        }

        crate::location::track::BalloonTrack {
            name: match &self.query.name {
                Some(name) => name.to_owned(),
                None => String::from("prediction"),
            },
            locations,
            attributes: crate::location::track::BalloonTrackAttributes {
                callsign: None,
                prediction: true,
            },
        }
    }
}

impl crate::location::track::BalloonTrack {
    pub fn prediction(
        &self,
        profile: &super::FlightProfile,
    ) -> crate::location::track::BalloonTrack {
        let query = crate::prediction::tawhiri::TawhiriQuery::new(
            &self.locations.last().unwrap(),
            profile,
            None,
            None,
            None,
            self.descending() || self.falling().is_some(),
        );

        query.retrieve_prediction()
    }
}

custom_error::custom_error! {pub TawhiriError
    NoFloatStage="API did not return a float stage",
    NoDescentStage = "API did not return a descent stage",
    HttpErrorStatus {status:u16, description:String} = "HTTP error {status} - {description}",
}

// https://tawhiri.readthedocs.io/en/latest/api.html#responses
#[derive(serde::Deserialize)]
struct TawhiriResponse {
    metadata: TawhiriMetadata,
    request: TawhiriRequest,
    prediction: Vec<TawhiriPrediction>,
    warnings: std::collections::HashMap<String, String>,
}
#[derive(serde::Deserialize)]
struct TawhiriErrorResponse {
    description: String,
    #[serde(rename = "type")]
    _type: String,
}
#[derive(serde::Deserialize)]
struct TawhiriMetadata {
    start_datetime: String,
    complete_datetime: String,
}
#[derive(serde::Deserialize)]
#[serde(tag = "profile")]
#[serde(rename_all = "snake_case")]
enum TawhiriRequest {
    StandardProfile {
        ascent_rate: f64,
        burst_altitude: f64,
        dataset: String,
        descent_rate: f64,
        launch_altitude: f64,
        launch_datetime: String,
        launch_latitude: f64,
        launch_longitude: f64,
        version: f64,
    },
    FloatProfile {
        ascent_rate: f64,
        dataset: String,
        float_altitude: f64,
        launch_altitude: f64,
        launch_datetime: String,
        launch_latitude: f64,
        launch_longitude: f64,
        stop_datetime: String,
        version: f64,
    },
}
#[derive(serde::Deserialize, Clone)]
struct TawhiriPrediction {
    stage: String,
    trajectory: Vec<TawhiriLocation>,
}
#[derive(serde::Deserialize, Clone)]
struct TawhiriLocation {
    altitude: f64,
    datetime: String,
    latitude: f64,
    longitude: f64,
}
impl TawhiriLocation {
    pub fn to_balloon_location(&self) -> crate::location::BalloonLocation {
        // CUSF API requires longitude in 0-360 format
        let mut longitude: f64 = self.longitude;
        if longitude > 180.0 {
            longitude -= 360.0;
        }

        crate::location::BalloonLocation {
            time: chrono::DateTime::parse_from_rfc3339(&self.datetime)
                .unwrap()
                .with_timezone(&chrono::Local),
            location: geo::point!(x: longitude, y: self.latitude),
            altitude: Some(self.altitude),
            data: crate::location::BalloonData::new(
                None,
                None,
                crate::location::LocationSource::Prediction,
            ),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_ground_prediction() {
        let start = crate::location::BalloonLocation {
            time: chrono::Local::now(),
            location: geo::point!(x: -77.547824, y: 39.359031),
            altitude: None,
            data: crate::location::BalloonData::default(),
        };
        let profile = crate::prediction::FlightProfile::new_standard(5.5, 28000.0, 9.0);

        let query = TawhiriQuery::new(&start, &profile, None, None, None, false);
        println!("{:}", query.url());

        let response = query.get().unwrap();
        let prediction = query.retrieve_prediction();

        let mut stages = vec![];
        for stage in response.prediction {
            stages.push(stage.stage);
        }

        for stage in [String::from("ascent"), String::from("descent")] {
            assert!(stages.contains(&stage));
        }
        assert!(!prediction.locations.is_empty());
    }

    #[test]
    fn test_ascending_prediction() {
        let start = crate::location::BalloonLocation {
            time: chrono::Local::now(),
            location: geo::point!(x: -77.547824, y: 39.359031),
            altitude: Some(2000.0),
            data: crate::location::BalloonData::default(),
        };
        let profile = crate::prediction::FlightProfile::new_standard(5.5, 28000.0, 9.0);

        let query = TawhiriQuery::new(&start, &profile, None, None, None, false);
        println!("{:}", query.url());

        let response = query.get().unwrap();
        let prediction = query.retrieve_prediction();

        let mut stages = vec![];
        for stage in response.prediction {
            stages.push(stage.stage);
        }

        for stage in [String::from("ascent"), String::from("descent")] {
            assert!(stages.contains(&stage));
        }
        assert!(!prediction.locations.is_empty());
    }

    #[test]
    fn test_descending_prediction() {
        let start = crate::location::BalloonLocation {
            time: chrono::Local::now(),
            location: geo::point!(x: -77.547824, y: 39.359031),
            altitude: Some(26888.0),
            data: crate::location::BalloonData::default(),
        };
        let profile =
            crate::prediction::FlightProfile::new_standard(5.5, start.altitude.unwrap(), 9.0);

        let query = TawhiriQuery::new(&start, &profile, None, None, None, true);
        println!("{:}", query.url());

        let response = query.get().unwrap();
        let prediction = query.retrieve_prediction();

        let mut stages = vec![];
        for stage in response.prediction {
            stages.push(stage.stage);
        }

        for stage in [String::from("descent")] {
            assert!(stages.contains(&stage));
        }
        assert!(!prediction.locations.is_empty());
    }

    #[test]
    fn test_float_prediction() {
        let start = crate::location::BalloonLocation {
            time: chrono::Local::now(),
            location: geo::point!(x: -77.547824, y: 39.359031),
            altitude: None,
            data: crate::location::BalloonData::default(),
        };
        let profile = crate::prediction::FlightProfile::new(
            5.5,
            None,
            Some(chrono::Duration::hours(1)),
            None,
            28000.0,
            9.0,
        );

        let query = TawhiriQuery::new(&start, &profile, None, None, None, false);
        println!("{:}", query.url());

        let response = query.get().unwrap();
        let prediction = query.retrieve_prediction();

        let mut stages = vec![];
        for stage in response.prediction {
            stages.push(stage.stage);
        }

        for stage in [
            String::from("ascent"),
            String::from("float"),
            String::from("descent"),
        ] {
            assert!(stages.contains(&stage));
        }
        assert!(!prediction.locations.is_empty());
    }
}
