pub mod prediction;

fn default_name() -> String {
    String::from("unnamed_flight")
}

#[derive(serde::Deserialize, Clone, Default, serde::Serialize)]
pub struct RunConfiguration {
    #[serde(default = "default_name")]
    pub name: String,
    pub callsigns: Option<Vec<String>>,
    #[serde(default)]
    pub time: TimeConfiguration,
    pub output_file: Option<std::path::PathBuf>,
    pub log_file: Option<std::path::PathBuf>,
    #[serde(default)]
    pub connections: ConnectionConfiguration,
    pub prediction: Option<crate::configuration::prediction::PredictionConfiguration>,
}

fn default_interval() -> chrono::Duration {
    *crate::DEFAULT_INTERVAL
}

#[serde_with::serde_as]
#[derive(PartialEq, Debug, serde::Deserialize, Clone, serde::Serialize)]
pub struct TimeConfiguration {
    #[serde(default)]
    #[serde(with = "crate::utilities::optional_local_datetime_string")]
    pub start: Option<chrono::DateTime<chrono::Local>>,
    #[serde(default)]
    #[serde(with = "crate::utilities::optional_local_datetime_string")]
    pub end: Option<chrono::DateTime<chrono::Local>>,
    #[serde(default = "default_interval")]
    #[serde_as(as = "serde_with::DurationSeconds<i64>")]
    pub interval: chrono::Duration,
}

impl Default for TimeConfiguration {
    fn default() -> Self {
        Self {
            start: None,
            end: None,
            interval: chrono::Duration::seconds(10),
        }
    }
}

#[derive(Default, serde::Deserialize, PartialEq, Debug, Clone, serde::Serialize)]
pub struct ConnectionConfiguration {
    pub text: Option<Vec<crate::connection::text::TextStream>>,
    #[cfg(feature = "sondehub")]
    #[serde(default)]
    pub sondehub: Option<crate::connection::sondehub::SondeHubQuery>,
    #[cfg(feature = "aprsfi")]
    pub aprs_fi: Option<crate::connection::aprs_fi::AprsFiQuery>,
    #[cfg(feature = "postgres")]
    pub database: Option<crate::connection::postgres::DatabaseCredentials>,
}

#[cfg(test)]
mod tests {
    use super::*;
    use chrono::offset::TimeZone;

    #[test]
    fn test_example_1() {
        let path = format!(
            "{:}/{:}",
            env!("CARGO_MANIFEST_DIR"),
            "examples/example_1.yaml"
        );

        let file = std::fs::File::open(path).unwrap();
        let configuration: RunConfiguration = serde_yaml::from_reader(file).unwrap();

        assert!(!configuration.connections.text.unwrap().is_empty());
    }

    #[test]
    fn test_example_2() {
        let path = format!(
            "{:}/{:}",
            env!("CARGO_MANIFEST_DIR"),
            "examples/example_2.yaml"
        );

        let file = std::fs::File::open(path).unwrap();
        let configuration: RunConfiguration = serde_yaml::from_reader(file).unwrap();

        let expected_callsigns = vec!["KC3SKW-8".to_string(), "KC3SKW-9".to_string()];

        if let Some(callsigns) = configuration.callsigns {
            assert_eq!(callsigns, expected_callsigns);
        }

        assert_eq!(
            configuration.connections,
            ConnectionConfiguration {
                #[cfg(feature = "aprsfi")]
                aprs_fi: Some(crate::connection::aprs_fi::AprsFiQuery::new(
                    String::from("123456.abcdefhijklmnop"),
                    None,
                )),
                #[cfg(feature = "sondehub")]
                sondehub: Some(crate::connection::sondehub::SondeHubQuery::default()),
                text: Some(vec![crate::connection::text::TextStream::AprsSerial(
                    crate::connection::text::serial::AprsSerial {
                        port: "COM3".to_string(),
                        baud_rate: 9600,
                        callsigns: None
                    }
                )]),
                #[cfg(feature = "postgres")]
                database: None,
            }
        );
    }

    #[test]
    fn test_example_3() {
        let path = format!(
            "{:}/{:}",
            env!("CARGO_MANIFEST_DIR"),
            "examples/example_3.yaml"
        );

        let file = std::fs::File::open(path).unwrap();
        let configuration: RunConfiguration = serde_yaml::from_reader(file).unwrap();

        let expected_callsigns = vec![
            "W3EAX-9".to_string(),
            "W3EAX-11".to_string(),
            "W3EAX-12".to_string(),
        ];

        assert_eq!(
            configuration.callsigns.to_owned().unwrap(),
            expected_callsigns
        );

        assert_eq!(
            configuration.time,
            TimeConfiguration {
                start: Some(
                    chrono::Local
                        .from_local_datetime(
                            &chrono::NaiveDate::from_ymd_opt(2022, 3, 5)
                                .unwrap()
                                .and_hms_opt(0, 0, 0)
                                .unwrap()
                        )
                        .unwrap()
                ),
                end: Some(
                    chrono::Local
                        .from_local_datetime(
                            &chrono::NaiveDate::from_ymd_opt(2022, 3, 6)
                                .unwrap()
                                .and_hms_opt(0, 0, 0)
                                .unwrap()
                        )
                        .unwrap()
                ),
                interval: chrono::Duration::seconds(120),
            }
        );

        assert_eq!(
            configuration.output_file.unwrap(),
            std::path::PathBuf::from("example_3.geojson".to_string())
        );

        assert!(configuration.connections.text.is_some());

        if let Some(crate::configuration::prediction::PredictionConfiguration::Single(prediction)) =
            configuration.prediction
        {
            assert_eq!(
                prediction,
                crate::configuration::prediction::Prediction {
                    name: String::from("prediction"),
                    start: crate::location::Location {
                        coord: geo::coord! { x: -78.4987, y: 40.0157 },
                        altitude: None,
                        time: chrono::NaiveDateTime::parse_from_str(
                            "2022-03-05 10:36:00",
                            &crate::DATETIME_FORMAT
                        )
                        .unwrap()
                        .and_local_timezone(chrono::Local)
                        .unwrap()
                    },
                    profile: crate::configuration::prediction::StandardProfile {
                        ascent_rate: 6.5,
                        burst_altitude: 25000.0,
                        sea_level_descent_rate: 9.0,
                        descent_only: false,
                    },
                    float: None,
                    api_url: None,
                    output_file: Some(std::path::PathBuf::from(
                        "example_3_prediction.geojson".to_string()
                    ))
                }
            );
        }
    }
}
