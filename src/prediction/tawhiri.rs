pub struct TawhiriQuery {
    pub query: crate::prediction::BalloonPredictionQuery,
    pub dataset_time: Option<chrono::DateTime<chrono::Utc>>,
    pub version: Option<f64>,
}

impl TawhiriQuery {
    pub fn new(
        start: &crate::location::Location,
        profile: &crate::prediction::FlightProfile,
        dataset_time: Option<chrono::DateTime<chrono::Utc>>,
        version: Option<f64>,
        name: Option<String>,
        descent_only: bool,
        float_start: Option<chrono::DateTime<chrono::Local>>,
    ) -> TawhiriQuery {
        TawhiriQuery {
            query: crate::prediction::BalloonPredictionQuery::new(
                String::from("https://api.v2.sondehub.org/tawhiri"),
                start,
                profile,
                name,
                descent_only,
                float_start,
            ),
            dataset_time,
            version,
        }
    }

    fn parameters(&self) -> Result<Vec<(&str, String)>, TawhiriError> {
        // CUSF API requires longitude in 0-360 format
        let mut start_location = self.query.start.coord;
        if start_location.x < 0.0 {
            start_location = geo::coord! { x: start_location.x + 360.0, y: start_location.y }
        }

        let burst_altitude = match self.query.descent_only {
            true => {
                let altitude = match self.query.start.altitude {
                    Some(altitude) => altitude,
                    None => {
                        return Err(TawhiriError::RequestError {
                            message: "no start altitude provided for descent prediction"
                                .to_string(),
                        });
                    }
                };
                altitude + 0.1
            }
            false => self.query.profile.burst_altitude,
        };

        let mut parameters = vec![
            ("launch_longitude", format!("{:.2}", start_location.x)),
            ("launch_latitude", format!("{:.2}", start_location.y)),
            (
                "launch_datetime",
                self.query
                    .start
                    .time
                    .with_timezone(&chrono::Utc)
                    .to_rfc3339(),
            ),
            (
                "ascent_rate",
                format!("{:.2}", self.query.profile.ascent_rate),
            ),
            ("burst_altitude", format!("{burst_altitude:.2}")),
            (
                "descent_rate",
                format!("{:.2}", self.query.profile.sea_level_descent_rate,),
            ),
        ];

        let launch_altitude = self.query.start.altitude;
        if let Some(altitude) = launch_altitude {
            parameters.push(("launch_altitude", format!("{altitude:.2}")));
        }
        if let Some(dataset_time) = self.dataset_time {
            parameters.push(("dataset", dataset_time.to_rfc3339()));
        }
        if let Some(version) = self.version {
            parameters.push(("version", format!("{version}")));
        }

        if let Some(float_duration) = self.query.profile.float_duration {
            if !self.query.descent_only {
                parameters.push(("profile", "float_profile".to_string()));
                let mut float_altitude = self
                    .query
                    .profile
                    .float_altitude
                    .unwrap_or(self.query.profile.burst_altitude);
                if let Some(launch_altitude) = launch_altitude {
                    if float_altitude <= launch_altitude {
                        float_altitude = launch_altitude + 1.0;
                    }
                }

                parameters.push(("float_altitude", format!("{float_altitude:.2}")));

                let float_start_time = self.query.float_start.unwrap_or({
                    self.query.start.time
                        + chrono::Duration::seconds(
                            (float_altitude
                                - self.query.start.altitude.unwrap_or(0.0)
                                    / self.query.profile.ascent_rate)
                                as i64,
                        )
                });
                parameters.push((
                    "stop_datetime",
                    (float_start_time + float_duration).to_rfc3339(),
                ));
            }
        } else {
            parameters.push(("profile", "standard_profile".to_string()));
        }

        Ok(parameters)
    }

    fn get(&self) -> Result<TawhiriResponse, TawhiriError> {
        let client = reqwest::blocking::Client::builder()
            .user_agent(crate::connection::USER_AGENT.to_owned())
            .timeout(Some(std::time::Duration::from_secs(10)))
            .build()
            .unwrap();

        let parameters = self.parameters();
        let response = client
            .get(&self.query.api_url)
            .query(&parameters?)
            .send()
            .expect("error retrieving prediction");
        let url = response.url().to_string();

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
                                        &float_end_location.location,
                                        &crate::prediction::FlightProfile::new_standard(
                                            10.0,
                                            float_end_location.location.altitude.unwrap(),
                                            self.query.profile.sea_level_descent_rate,
                                        ),
                                        self.dataset_time,
                                        self.version,
                                        None,
                                        true,
                                        None,
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
                match response.json::<TawhiriErrorResponse>() {
                    Ok(tawhiri_error) => Err(TawhiriError::HttpError {
                        status: status.as_u16(),
                        description: tawhiri_error.error.description,
                        url,
                    }),
                    Err(error) => Err(TawhiriError::ParsingError {
                        message: error.to_string(),
                    }),
                }
            }
        }
    }

    pub fn retrieve_prediction(
        &self,
    ) -> Result<crate::location::track::LocationTrack, TawhiriError> {
        let response = self.get()?;

        let mut locations = vec![];

        for stage in response.prediction {
            for location in stage.trajectory {
                locations.push(location.to_balloon_location());
            }
        }

        Ok(locations)
    }
}

impl crate::location::track::BalloonTrack {
    pub fn prediction(
        &self,
        profile: &super::FlightProfile,
    ) -> Result<crate::location::track::LocationTrack, TawhiriError> {
        let mut descending = self.descending() || self.falling().is_some();

        let float_start = if let Some(float_altitude) = profile.float_altitude {
            let locations_at_float_altitude: Vec<&crate::location::BalloonLocation> = self
                .locations
                .iter()
                .filter(|location| match location.location.altitude {
                    Some(altitude) => {
                        (float_altitude - altitude).abs() <= profile.float_uncertainty
                    }
                    None => false,
                })
                .collect();

            if !locations_at_float_altitude.is_empty() {
                // mark as "not descending" if altitude is within float uncertainty
                if descending
                    && self.falling().is_none()
                    && (locations_at_float_altitude
                        .last()
                        .unwrap()
                        .location
                        .altitude
                        .unwrap()
                        - float_altitude)
                        .abs()
                        <= profile.float_uncertainty
                {
                    descending = false;
                }

                Some(locations_at_float_altitude.first().unwrap().location.time)
            } else {
                None
            }
        } else {
            None
        };

        let query = crate::prediction::tawhiri::TawhiriQuery::new(
            &self.locations.last().unwrap().location,
            profile,
            None,
            None,
            None,
            descending,
            float_start,
        );

        query.retrieve_prediction()
    }
}

custom_error::custom_error! {pub TawhiriError
    NoFloatStage ="server did not return a float stage",
    NoDescentStage = "server did not return a descent stage",
    HttpError { status: u16, description: String, url: String } = "HTTP error {status} - {description} - {url}",
    ParsingError { message: String } = "{message}",
    RequestError { message: String } = "{message}",
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
    error: TawhiriErrorMessage,
    metadata: TawhiriMetadata,
}

#[derive(serde::Deserialize)]
struct TawhiriErrorMessage {
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
    datetime: chrono::DateTime<chrono::Utc>,
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
            location: crate::location::Location {
                time: self.datetime.with_timezone(&chrono::Local),
                coord: geo::coord! { x: longitude, y: self.latitude },
                altitude: Some(self.altitude),
            },
            data: crate::location::BalloonData::new(
                None,
                None,
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
    #[ignore]
    fn test_ground_prediction() {
        let start = crate::location::Location {
            time: chrono::Local::now(),
            coord: geo::coord! { x: -77.547824, y: 39.359031 },
            altitude: None,
        };
        let profile = crate::prediction::FlightProfile::new_standard(5.5, 28000.0, 9.0);

        let query = TawhiriQuery::new(&start, &profile, None, None, None, false, None);

        let response = query.get().unwrap();
        let prediction = query.retrieve_prediction();

        let mut stages = vec![];
        for stage in response.prediction {
            stages.push(stage.stage);
        }

        for stage in [String::from("ascent"), String::from("descent")] {
            assert!(stages.contains(&stage));
        }
        assert!(prediction.is_ok());
        assert!(!prediction.unwrap().is_empty());
    }

    #[test]
    #[ignore]
    fn test_ascending_prediction() {
        let start = crate::location::Location {
            time: chrono::Local::now(),
            coord: geo::coord! { x: -77.547824, y: 39.359031 },
            altitude: Some(2000.0),
        };
        let profile = crate::prediction::FlightProfile::new_standard(5.5, 28000.0, 9.0);

        let query = TawhiriQuery::new(&start, &profile, None, None, None, false, None);

        let response = query.get().unwrap();
        let prediction = query.retrieve_prediction();

        let mut stages = vec![];
        for stage in response.prediction {
            stages.push(stage.stage);
        }

        for stage in [String::from("ascent"), String::from("descent")] {
            assert!(stages.contains(&stage));
        }
        assert!(prediction.is_ok());
        assert!(!prediction.unwrap().is_empty());
    }

    #[test]
    #[ignore]
    fn test_descending_prediction() {
        let start = crate::location::Location {
            time: chrono::Local::now(),
            coord: geo::coord! { x: -77.547824, y: 39.359031 },
            altitude: Some(26888.0),
        };
        let profile =
            crate::prediction::FlightProfile::new_standard(5.5, start.altitude.unwrap(), 9.0);

        let query = TawhiriQuery::new(&start, &profile, None, None, None, true, None);

        let response = query.get().unwrap();
        let prediction = query.retrieve_prediction();

        let mut stages = vec![];
        for stage in response.prediction {
            stages.push(stage.stage);
        }

        assert!(stages.contains(&"descent".to_string()));
        assert!(prediction.is_ok());
        assert!(!prediction.unwrap().is_empty());
    }

    #[test]
    #[ignore]
    fn test_float_prediction() {
        let start = crate::location::Location {
            time: chrono::Local::now(),
            coord: geo::coord! { x: -77.547824, y: 39.359031 },
            altitude: None,
        };
        let profile = crate::prediction::FlightProfile::new(
            5.5,
            None,
            Some(chrono::Duration::hours(1)),
            None,
            28000.0,
            9.0,
        );

        let query = TawhiriQuery::new(&start, &profile, None, None, None, false, None);

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
        assert!(prediction.is_ok());
        assert!(!prediction.unwrap().is_empty());
    }
}
