pub mod credentials;
pub mod plots;
pub mod prediction;
pub mod text;

fn default_name() -> String {
    String::from("unnamed_flight")
}

#[derive(serde::Deserialize)]
pub struct RunConfiguration {
    #[serde(default = "default_name")]
    pub name: String,
    pub callsigns: Option<Vec<String>>,
    #[serde(default)]
    pub time: TimeConfiguration,
    pub output: Option<PathConfiguration>,
    pub log: Option<PathConfiguration>,
    #[serde(default)]
    pub packets: PacketSourceConfiguration,
    pub prediction: Option<crate::configuration::prediction::PredictionConfiguration>,
    pub plots: Option<crate::configuration::plots::PlotsConfiguration>,
}

#[derive(serde::Deserialize, PartialEq, Debug)]
pub struct PathConfiguration {
    pub filename: std::path::PathBuf,
}

fn default_interval() -> chrono::Duration {
    *crate::DEFAULT_INTERVAL
}

#[serde_with::serde_as]
#[derive(PartialEq, Debug, serde::Deserialize)]
pub struct TimeConfiguration {
    #[serde(default)]
    #[serde(with = "crate::parse::optional_local_datetime_string")]
    pub start: Option<chrono::DateTime<chrono::Local>>,
    #[serde(default)]
    #[serde(with = "crate::parse::optional_local_datetime_string")]
    pub end: Option<chrono::DateTime<chrono::Local>>,
    #[serde(default = "default_interval")]
    #[serde_as(as = "serde_with::DurationSeconds<i64>")]
    pub interval: chrono::Duration,
    #[serde_as(as = "Option<serde_with::DurationSeconds<i64>>")]
    pub timeout: Option<chrono::Duration>,
}
impl Default for TimeConfiguration {
    fn default() -> Self {
        Self {
            start: None,
            end: None,
            interval: chrono::Duration::seconds(10),
            timeout: None,
        }
    }
}

#[derive(Default, serde::Deserialize, PartialEq, Debug)]
pub struct PacketSourceConfiguration {
    #[cfg(feature = "aprsfi")]
    pub aprs_fi: Option<crate::configuration::credentials::AprsFiCredentials>,
    #[cfg(feature = "sondehub")]
    pub sondehub: Option<bool>,
    pub text: Option<crate::configuration::text::TextStreamConfiguration>,
    #[cfg(feature = "postgres")]
    pub database: Option<crate::connection::postgres::DatabaseCredentials>,
    pub aprs_is: Option<crate::configuration::credentials::AprsIsCredentials>,
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

        assert_eq!(
            configuration.packets,
            PacketSourceConfiguration {
                #[cfg(feature = "aprsfi")]
                aprs_fi: None,
                #[cfg(feature = "sondehub")]
                sondehub: None,
                text: Some(crate::configuration::text::TextStreamConfiguration {
                    locations: vec![std::path::PathBuf::from("http://bpp.umd.edu/archives/Launches/NS-111_2022_07_31/APRS/W3EAX-8%20raw.txt")],
                }),
                #[cfg(feature = "postgres")]
                database: None,
                aprs_is: None,
            }
        );
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

        if let Some(callsigns) = configuration.callsigns {
            assert_eq!(
                callsigns,
                vec![String::from("W3EAX-11"), String::from("W3EAX-12")]
            );
        }

        assert_eq!(
            configuration.packets,
            PacketSourceConfiguration {
                #[cfg(feature = "aprsfi")]
                aprs_fi: Some(crate::configuration::credentials::AprsFiCredentials {
                    api_key: String::from("123456.abcdefhijklmnop")
                }),
                #[cfg(feature = "sondehub")]
                sondehub: Some(true),
                text: None,
                #[cfg(feature = "postgres")]
                database: None,
                aprs_is: None,
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

        assert_eq!(
            configuration.callsigns.to_owned().unwrap(),
            vec![
                String::from("W3EAX-9"),
                String::from("W3EAX-11"),
                String::from("W3EAX-12"),
            ]
        );

        assert_eq!(
            configuration.callsigns.to_owned().unwrap(),
            vec![
                String::from("W3EAX-9"),
                String::from("W3EAX-11"),
                String::from("W3EAX-12"),
            ]
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
                timeout: None,
            }
        );

        assert_eq!(
            configuration.output.unwrap(),
            PathConfiguration {
                filename: std::path::PathBuf::from("example_3.geojson")
            }
        );

        assert_eq!(
            configuration.log.unwrap(),
            PathConfiguration {
                filename: std::path::PathBuf::from("example_3.log")
            }
        );

        assert_eq!(
            configuration.packets,
            PacketSourceConfiguration {
                #[cfg(feature = "aprsfi")]
                aprs_fi: None,
                #[cfg(feature = "sondehub")]
                sondehub: Some(true),
                text: Some(crate::configuration::text::TextStreamConfiguration {
                    locations: vec![
                        std::path::PathBuf::from("/dev/ttyUSB0"),
                        std::path::PathBuf::from("~/packets.txt")
                    ],
                }),
                #[cfg(feature = "postgres")]
                database: Some(crate::connection::postgres::DatabaseCredentials::new(
                    String::from("localhost"),
                    Some(5432),
                    Some(String::from("nearspace")),
                    String::from("example_3"),
                    String::from("user1"),
                    String::from("password1"),
                    Some(crate::connection::postgres::SshCredentials {
                        hostname: String::from("bpp.umd.edu:22"),
                        port: 22,
                        username: String::from("user2"),
                        password: String::from("password2"),
                    })
                )),
                aprs_is: None,
            }
        );

        if let Some(crate::configuration::prediction::PredictionConfiguration::Single(prediction)) =
            configuration.prediction
        {
            assert_eq!(
                prediction,
                crate::configuration::prediction::Prediction {
                    name: String::from("prediction"),
                    start: crate::configuration::prediction::StartLocation {
                        location: vec![-78.4987, 40.0157],
                        time: chrono::Local
                            .datetime_from_str("2022-03-05 10:36:00", &crate::DATETIME_FORMAT)
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
                    output: Some(PathConfiguration {
                        filename: std::path::PathBuf::from("example_3_prediction.geojson"),
                    })
                }
            );
        }
    }
}
